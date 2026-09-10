from flask import Flask,request,jsonify,render_template_string,session,redirect,url_for,send_from_directory
import openai,os,secrets,json,hashlib,asyncio,base64,re,sqlite3,requests,edge_tts
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app=Flask(__name__,static_folder='static')
app.secret_key=os.environ.get("SECRET_KEY",secrets.token_hex(16))

OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:raise Exception("OPENAI_API_KEY غير موجود!")
OPENAI_MODEL=os.environ.get("OPENAI_MODEL")
if not OPENAI_MODEL:raise Exception("OPENAI_MODEL غير موجود! أضفه في متغيرات البيئة.")

client=openai.OpenAI(api_key=OPENAI_API_KEY)
limiter=Limiter(key_func=get_remote_address,default_limits=["500 per day","20 per hour"])
limiter.init_app(app)

@app.route('/robots.txt')
def serve_robots():return send_from_directory('static','robots.txt')

@app.route('/sitemap.xml')
def serve_sitemap():return send_from_directory('static','sitemap.xml')

@app.route('/.well-known/<path:filename>')
def serve_well_known(filename):return send_from_directory('.well-known',filename)

DB_FILE="conversations.db"

def get_db():conn=sqlite3.connect(DB_FILE,check_same_thread=False,timeout=15);conn.row_factory=sqlite3.Row;return conn

def init_db():
    conn=get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS conversations (user_id TEXT, conv_id TEXT PRIMARY KEY, messages TEXT, timestamp TEXT, title TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS cache (question TEXT PRIMARY KEY, answer TEXT, created TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS guest_usage (guest_id TEXT PRIMARY KEY, count INT DEFAULT 0, date TEXT)''')
    conn.commit();conn.close()

def check_guest_limit_safe(gid):
    try:
        today=datetime.now().strftime("%Y-%m-%d");conn=get_db();row=conn.execute("SELECT count, date FROM guest_usage WHERE guest_id=?",(gid,)).fetchone()
        if not row:conn.execute("INSERT INTO guest_usage VALUES (?,?,?)",(gid,1,today));conn.commit();conn.close();return True
        if row[1]!=today:conn.execute("UPDATE guest_usage SET count=1, date=? WHERE guest_id=?",(today,gid));conn.commit();conn.close();return True
        if row[0]>=15:conn.close();return False
        conn.execute("UPDATE guest_usage SET count=count+1 WHERE guest_id=?",(gid,));conn.commit();conn.close();return True
    except:return True

def get_cached(q):
    try:conn=get_db();r=conn.execute("SELECT answer FROM cache WHERE question=?",(q.strip(),)).fetchone();conn.close();return r[0] if r else None
    except:return None

def save_cache(q,a):
    try:
        if len(q)<10 or len(q)>200:return
        if len(a)>2000:return
        conn=get_db();conn.execute("INSERT OR REPLACE INTO cache (question, answer, created) VALUES (?,?,?)",(q.strip(),a,datetime.now().isoformat()));conn.commit();conn.close()
    except:pass

def get_user_conversations(uid):
    conn=get_db();rows=conn.execute("SELECT conv_id,messages,timestamp,title FROM conversations WHERE user_id=? ORDER BY timestamp DESC",(uid,)).fetchall();conn.close();res=[]
    for r in rows:res.append({"id":r[0],"messages":json.loads(r[1]),"timestamp":r[2],"title":r[3]})
    return res

def save_user_conversation(uid,conv,cid=None):
    conn=get_db()
    if cid is None:
        title=conv[0]["content"][:30]+"..." if len(conv[0]["content"])>30 else conv[0]["content"]
        nid=hashlib.md5(f"{uid}{datetime.now().isoformat()}{secrets.token_hex(2)}".encode()).hexdigest()[:10]
        conn.execute("INSERT INTO conversations (user_id,conv_id,messages,timestamp,title) VALUES (?,?,?,?,?)",(uid,nid,json.dumps(conv,ensure_ascii=False),datetime.now().isoformat(),title))
        conn.commit();conn.close();return nid
    else:
        conn.execute("UPDATE conversations SET messages=?,timestamp=? WHERE user_id=? AND conv_id=?",(json.dumps(conv,ensure_ascii=False),datetime.now().isoformat(),uid,cid))
        conn.commit();conn.close();return cid

def load_conversation_by_id(uid,cid):
    conn=get_db();r=conn.execute("SELECT messages FROM conversations WHERE user_id=? AND conv_id=?",(uid,cid)).fetchone();conn.close()
    return json.loads(r[0]) if r else None

init_db()

sm={}
kc=""
for fn in ["Knowledge.md","knowledge.md","معرفة.md","README.md","ملف_المعرفة.md"]:
    if os.path.exists(fn):
        try:
            with open(fn,"r",encoding="utf-8") as f:kc=f.read();break
        except:pass
if not kc:kc="أنت نبراس، مساعد ذكي."

SP=f"""أنت "نبراس"، مساعد شخصي ذكي تتحدث باللهجة العامية البيضاء.\n\n**مصادر معرفتك:**\n\n1. **ملف المعرفة** (أدناه) هو مرجعك الأساسي.\n\n2. **معرفتك العامة**.\n\n3. **البحث بالويب** تستخدمه فقط عندما تكون أدمن ويسألك عن أي شيء حديث أو غير موجود في ملف المعرفة.\n\n**ملف المعرفة الخاص بك:**\n\n{kc}\n\n**⚠️ قاعدة التنسيق الذهبية (الأهم):**\n\n- اكتب ردودك في **فقرات نصية متصلة**. كل فقرة تحتوي على **2 إلى 4 جمل** فقط.\n\n- **ممنوع** وضع كل جملة في سطر منفصل. استخدم النقاط والفواصل وعلامات الترقيم داخل الفقرة نفسها.\n\n- **ممنوع** وضع فواصل أسطر (`Enter`) بين الجمل. الفاصل الوحيد المسموح به هو سطر فارغ بين الفقرة والأخرى.\n\n- اجعل الجملة الواحدة بطول معتدل (حوالي 10-20 كلمة)، بحيث تكون واضحة ومختصرة لكنها تحمل فكرة كاملة."""

def remove_emoji(t):
    return re.compile("["+u"\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002500-\U00002BEF\U00002702-\U000027B0\U000024C2-\U0001F251\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642\u2600-\u2B55\u200d\u23cf\u23e9\u231a\ufe0f\u3030"+"]+",flags=re.UNICODE).sub('',t)

def generate_image(prompt):
    try:
        api_key=os.environ.get("PEXELS_API_KEY")
        if not api_key:return "ERROR: PEXELS_API_KEY غير موجود في البيئة"
        query=requests.utils.quote(prompt);url=f"https://api.pexels.com/v1/search?query={query}&per_page=1&orientation=landscape";headers={"Authorization":api_key};response=requests.get(url,headers=headers,timeout=10);data=response.json()
        if response.status_code==200 and data.get("photos") and len(data["photos"])>0:return data["photos"][0]["src"]["large"]
        else:return f"ERROR: {data.get('error','لم أجد صورة مناسبة')}"
    except Exception as e:return f"ERROR: {str(e)}"

def search_video(prompt):
    try:
        api_key=os.environ.get("PEXELS_API_KEY")
        if not api_key:return "ERROR: PEXELS_API_KEY غير موجود في البيئة"
        query=requests.utils.quote(prompt);url=f"https://api.pexels.com/videos/search?query={query}&per_page=1";headers={"Authorization":api_key};response=requests.get(url,headers=headers,timeout=10);data=response.json()
        if response.status_code==200 and data.get("videos") and len(data["videos"])>0:
            video_files=data["videos"][0]["video_files"]
            for vf in video_files:
                if vf.get("quality")=="hd" and vf.get("link"):return vf["link"]
            if video_files and video_files[0].get("link"):return video_files[0]["link"]
            return "ERROR: ما لقيت رابط فيديو"
        else:return f"ERROR: {data.get('error','لم أجد فيديو مناسباً')}"
    except Exception as e:return f"ERROR: {str(e)}"

async def _generate_speech_async(text, voice):
    communicate=edge_tts.Communicate(text, voice);audio_data=b""
    async for chunk in communicate.stream():
        if chunk["type"]=="audio":audio_data+=chunk["data"]
    return audio_data

def generate_speech(text, gender):
    try:
        voice="ar-SA-HamedNeural" if gender=="male" else "ar-SA-ZariyahNeural"
        audio=asyncio.run(_generate_speech_async(text, voice))
        return base64.b64encode(audio).decode('utf-8')
    except Exception as e:print(f"❌ فشل الصوت (edge-tts): {e}");return None

# (باقي الأكواد الطويلة للـ HTML والقوالب تم حذفها هنا لاختصار المسافة فقط، لكن لا تحذفها من كودك الأصلي)
# ضع كود الـ SPH, TOOLS_HTML, HT, LH كما هو في مكانه الأصلي دون أي تغيير.

@app.route('/')
def index():return render_template_string(HT)

@app.route('/tools')
def tools_page():return render_template_string(TOOLS_HTML)

@app.route('/share/<cid>')
def shared_conversation(cid):
    conn=get_db();r=conn.execute("SELECT messages,title FROM conversations WHERE conv_id=?",(cid,)).fetchone();conn.close()
    if r:m=json.loads(r[0]);t=r[1] or "محادثة نبراس";return render_template_string(SPH,messages=m,title=t)
    return "⚠️ المحادثة غير موجودة أو تم حذفها.",404

@app.route('/login',methods=['GET','POST'])
@limiter.limit("3 per minute")
def login():
    if request.method=='POST':
        e=request.form.get('email');p=request.form.get('password');ae="abdullaha0569361@gmail.com";ap=os.environ.get("ADMIN_PASSWORD")
        if e==ae:
            if not ap:return render_template_string(LH,error="خطأ: لم يتم إعداد كلمة مرور الأدمن في الخادم.")
            if secrets.compare_digest(p,ap):session.clear();session['admin_email']=ae;return redirect(url_for('index'))
            else:return render_template_string(LH,error="كلمة مرور الأدمن غير صحيحة.")
        elif e and "@" in e:session.clear();session['user_email']=e;return redirect(url_for('index'))
        else:return render_template_string(LH,error="يرجى إدخال بريد إلكتروني صحيح.")
    return render_template_string(LH)

@app.route('/logout')
def logout():session.clear();return redirect(url_for('index'))

@app.route('/history')
def history():uid=get_user_id();cs=get_user_conversations(uid);return jsonify({"conversations":[{"id":c["id"],"title":c["title"]} for c in cs]})

@app.route('/load_conversation/<cid>')
def load_conversation(cid):uid=get_user_id();ms=load_conversation_by_id(uid,cid);return jsonify({"messages":ms}) if ms else (jsonify({"messages":None}),404)

@app.route('/delete_message',methods=['POST'])
def delete_message():
    try:
        d=request.get_json();cid=d.get('conv_id');idx=d.get('index');uid=get_user_id()
        if not cid or idx is None:return jsonify({"status":"error","message":"بيانات ناقصة"}),400
        msgs=load_conversation_by_id(uid,cid)
        if not msgs:return jsonify({"status":"error","message":"المحادثة غير موجودة"}),404
        if idx<0 or idx>=len(msgs):return jsonify({"status":"error","message":"الرسالة غير موجودة"}),404
        del msgs[idx];save_user_conversation(uid,msgs,cid);return jsonify({"status":"ok"})
    except Exception as e:return jsonify({"status":"error","message":str(e)}),500

@app.route('/delete_my_data',methods=['POST'])
def delete_my_data():uid=get_user_id();conn=get_db();conn.execute("DELETE FROM conversations WHERE user_id=?",(uid,));conn.commit();conn.close();session.clear();return jsonify({"status":"success","message":"تم حذف جميع بياناتك ومحادثاتك بنجاح."})

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_email')=="abdullaha0569361@gmail.com":return "🚫 هذه الصفحة خاصة بالأدمن فقط.",403
    conn=get_db();users_count=conn.execute("SELECT COUNT(DISTINCT user_id) FROM conversations").fetchone()[0];total_convs=conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0];today=datetime.now().strftime("%Y-%m-%d");today_convs=conn.execute("SELECT COUNT(*) FROM conversations WHERE timestamp LIKE ?",(today+'%',)).fetchone()[0];recent=conn.execute("SELECT user_id, title, timestamp FROM conversations ORDER BY timestamp DESC LIMIT 10").fetchall();conn.close()
    recent_html=""
    for row in recent:
        user=row[0][:15]+"..." if len(row[0])>15 else row[0];title=row[1] or "محادثة بدون عنوان";time=row[2][:16] if row[2] else "وقت غير معروف";recent_html+=f'<div class="conv-item"><b>{title}</b><small>👤 {user} | 🕒 {time}</small></div>'
    if not recent_html:recent_html="<p style='color:#8b949e;text-align:center;'>لا توجد محادثات بعد</p>"
    return f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>لوحة تحكم نبراس</title><style>body{{font-family:'Segoe UI',Tahoma;background:#0d1117;color:#c9d1d9;padding:20px;margin:0}}.container{{max-width:600px;margin:auto}}h1{{color:#58a6ff;text-align:center}}.card{{background:#161b22;border-radius:15px;padding:15px;margin:15px 0;border:1px solid #30363d}}.stat{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #21262d}}.stat:last-child{{border:none}}.num{{color:#58a6ff;font-weight:bold;font-size:18px}}.conv-item{{padding:10px 0;border-bottom:1px solid #21262d}}.conv-item small{{color:#8b949e;display:block;font-size:12px}}.back{{display:block;text-align:center;color:#58a6ff;text-decoration:none;margin-top:20px}}</style></head><body><div class="container"><h1>📊 لوحة تحكم نبراس</h1><div class="card"><div class="stat"><span>👥 إجمالي المستخدمين</span><span class="num">{users_count}</span></div><div class="stat"><span>💬 إجمالي المحادثات</span><span class="num">{total_convs}</span></div><div class="stat"><span>📅 محادثات اليوم</span><span class="num">{today_convs}</span></div></div><div class="card"><h3>🕒 آخر 10 محادثات</h3>{recent_html}</div><a href="/" class="back">⬅ العودة للرئيسية</a></div></body></html>"""

def get_user_id():
    if 'admin_email' in session:return "admin_"+session['admin_email']
    elif 'user_email' in session:return "user_"+session['user_email']
    else:
        if 'guest_id' not in session:session['guest_id']="guest_"+secrets.token_hex(8)
        return session['guest_id']

@app.route('/set_gender',methods=['POST'])
def set_gender():d=request.get_json();session['voice_gender']=d.get('gender','male');return jsonify({"status":"ok"})

@app.route('/chat',methods=['POST'])
@limiter.limit("20 per minute")
def chat():
    try:
        d=request.get_json();um=d.get("message","").strip();hist=d.get("history",[]);cid=d.get("conv_id",None)
        if not um:return jsonify({"reply":"اكتب شيء أساعدك فيه"})
        is_admin='admin_email' in session and session['admin_email']=="abdullaha0569361@gmail.com";uid=get_user_id()
        if not is_admin:
            if not check_guest_limit_safe(uid):
                reply_limit="وصلت للحد المجاني اليوم (15 سؤال) 😊\n\n💡 عندك حلين بدون ما تدفع:\n\n1- جرب أدواتنا المجانية 100% (ما تستهلك رصيد):\nhttps://nibras-al.onrender.com/tools\n\n2- ارجع بكرة وتاخذ 15 سؤال جديدة مجاناً\n\nنظامنا مجاني للجميع لأنه بدون بوابة دفع."
                if cid is None:sm[uid]=[]
                sm[uid].append({"role":"user","content":um});sm[uid].append({"role":"assistant","content":reply_limit});nid=save_user_conversation(uid,sm[uid],cid)
                return jsonify({"reply":reply_limit,"conv_id":nid,"audio":None})
            cached=get_cached(um)
            if cached:
                if cid is None:sm[uid]=[]
                sm[uid].append({"role":"user","content":um});sm[uid].append({"role":"assistant","content":cached});nid=save_user_conversation(uid,sm[uid],cid)
                return jsonify({"reply":cached+"\n\n⚡ جواب سريع من الذاكرة","conv_id":nid,"audio":None})
        draw_phrases=["ارسم لي","ابي صورة","ابي صوره","ابي صورت","صوره لي","ارسم","أنشئ","انشئ","انشى","صمم","ولّد","generate","draw","فيديو","ابي فيديو","عرض فيديو"]
        def is_image_request(text):
            text_lower=text.lower().strip()
            if len(text_lower.split())<=1:return False
            for phrase in draw_phrases:
                if phrase in text_lower:return True
            return False
        has_image=d.get("image") is not None
        if is_image_request(um) and not has_image:
            print(f"🎨 طلب رسم/فيديو مجاني من {uid}")
            video_keywords=["فيديو","ابي فيديو","عرض فيديو"]
            is_video=any(kw in um for kw in video_keywords)
            if is_video:
                video_result=search_video(um)
                if video_result and video_result.startswith("ERROR:"):
                    error_clear=video_result.replace("ERROR:","");reply=f"⚠️ عذراً، ما قدرت أجيب الفيديو. السبب: {error_clear}"
                    sm[uid].append({"role":"user","content":um});sm[uid].append({"role":"assistant","content":reply});nid=save_user_conversation(uid,sm[uid],cid)
                    return jsonify({"reply":reply,"conv_id":nid})
                elif video_result:
                    reply=f"🎬 إليك الفيديو الذي طلبتـه:";reply_with_url=reply+"\n"+video_result
                    sm[uid].append({"role":"user","content":um});sm[uid].append({"role":"assistant","content":reply_with_url});nid=save_user_conversation(uid,sm[uid],cid)
                    return jsonify({"reply":reply_with_url,"image_url":video_result,"conv_id":nid})
                else:
                    reply="⚠️ عذراً، تعذر جلب الفيديو بسبب خطأ غير معروف."
                    sm[uid].append({"role":"user","content":um});sm[uid].append({"role":"assistant","content":reply});nid=save_user_conversation(uid,sm[uid],cid)
                    return jsonify({"reply":reply,"conv_id":nid})
            img_result=generate_image(um)
            if img_result and img_result.startswith("ERROR:"):
                error_clear=img_result.replace("ERROR:","");reply=f"⚠️ عذراً، ما قدرت أولد الصورة. السبب: {error_clear}"
                sm[uid].append({"role":"user","content":um});sm[uid].append({"role":"assistant","content":reply});nid=save_user_conversation(uid,sm[uid],cid)
                return jsonify({"reply":reply,"conv_id":nid})
            elif img_result:
                reply=f"🖼️ إليك الصورة التي طلبتها:";reply_with_url=reply+"\n"+img_result
                sm[uid].append({"role":"user","content":um});sm[uid].append({"role":"assistant","content":reply_with_url});nid=save_user_conversation(uid,sm[uid],cid)
                return jsonify({"reply":reply_with_url,"image_url":img_result,"conv_id":nid})
            else:
                reply="⚠️ عذراً، تعذر توليد الصورة بسبب خطأ غير معروف."
                sm[uid].append({"role":"user","content":um});sm[uid].append({"role":"assistant","content":reply});nid=save_user_conversation(uid,sm[uid],cid)
                return jsonify({"reply":reply,"conv_id":nid})
        if has_image and not is_admin:
            reply="عذراً، ميزة تحليل الصور المرفوعة والبحث المباشر متاحة لحساب الأدمن فقط حالياً للحفاظ على رصيد OpenAI.\n\n💡 لكن تقدر تطلب صور وفيديوهات مجانية بكلمة (ارسم لي) أو (ابي فيديو)."
            if cid is None:sm[uid]=[]
            sm[uid].append({"role":"user","content":um});sm[uid].append({"role":"assistant","content":reply});nid=save_user_conversation(uid,sm[uid],cid)
            return jsonify({"reply":reply,"conv_id":nid})
        if cid is None:sm[uid]=[]
        model=OPENAI_MODEL;use_web=True if is_admin else False;allow_img=True if is_admin else False
        server_hist=load_conversation_by_id(uid,cid) if cid else []
        if not server_hist:server_hist=sm.get(uid,[])
        server_hist.append({"role":"user","content":um});sm[uid]=server_hist
        ch=server_hist[-30:]
        msgs=[{"role":"system","content":SP}]
        for e in ch:msgs.append({"role":e["role"],"content":e["content"]})
        img_data=d.get("image",None)
        if img_data and is_admin:msgs.append({"role":"user","content":[{"type":"text","text":um or "حلل هذه الصورة"},{"type":"image_url","image_url":{"url":img_data}}]})
        if use_web:
            try:
                fc=""
                for m in msgs:
                    if m["role"]=="user":fc+=m["content"]+"\n"
                    elif m["role"]=="assistant":fc+="نبراس: "+m["content"]+"\n"
                sr=client.responses.create(model=model,instructions=f"{SP}\n\nسياق المحادثة السابقة:\n{fc}",input=f"ابحث في الويب عن أحدث المعلومات حول: {um}، وقدم لي ملخصاً مفيداً.",tools=[{"type":"web_search"}])
                res=sr.output_text.strip()
                if res:msgs.append({"role":"user","content":f"نتيجة البحث:\n{res}\n\nاستخدم هذه المعلومات."})
            except Exception as e:print(f"⚠️ فشل البحث: {e}")
        try:
            reasoning_level="low" if not is_admin else "high"
            r=client.chat.completions.create(model=model,messages=msgs,max_completion_tokens=8000,reasoning_effort=reasoning_level)
            reply=r.choices[0].message.content.strip()
            if not reply:reply="ما قدرت أجيب لك رد، حاول مرة أخرى."
        except Exception as e:print(f"❌ خطأ عام: {e}");return jsonify({"error":str(e)}),500
        lines=reply.split('\n');merged_paragraphs=[];current_paragraph=[]
        for line in lines:
            line=line.strip()
            if not line:
                if current_paragraph:merged_paragraphs.append(' '.join(current_paragraph));current_paragraph=[]
            else:current_paragraph.append(line)
        if current_paragraph:merged_paragraphs.append(' '.join(current_paragraph))
        reply='\n\n'.join(merged_paragraphs)
        sm[uid].append({"role":"assistant","content":reply});nid=save_user_conversation(uid,sm[uid],cid)
        if not is_admin:save_cache(um,reply)
        try:gender=session.get('voice_gender','male');audio=generate_speech(reply,gender)
        except Exception as e:print(f"⚠️ فشل الصوت: {e}");audio=None
        return jsonify({"reply":reply,"audio":audio,"conv_id":nid})
    except Exception as e:print(f"❌ خطأ عام: {e}");return jsonify({"error":str(e)}),500

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
