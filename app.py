from flask import Flask, request, session, Response
from openai import OpenAI
import os
import re
import time
from datetime import datetime
import pytz
from duckduckgo_search import DDGS

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nibras_gt_secure_key_2026")
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ OPENAI_API_KEY غير موجود")
client = OpenAI(api_key=API_KEY)

def get_real_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

def is_pure_date_question(prompt):
    p = prompt.strip().lower()
    patterns = [r"^وش اليوم\??$", r"^ايش اليوم\??$", r"^كم التاريخ\??$", r"^شو التاريخ\??$", r"^تاريخ اليوم\??$"]
    return any(re.fullmatch(pat, p) for pat in patterns)

def user_asks_for_sources(prompt):
    p = prompt.strip().lower()
    return any(word in p for word in ["المصدر", "المصادر", "الروابط", "عطني المصدر", "من وين جبتها"])

def MUST_SEARCH(prompt):
    p = prompt.strip().lower()
    force = [
        r"خبر|أخبار|حدث|وش صار|ايش صار|عاجل|مستجدات",
        r"202[4-9]|203", r"مباراة|نتيجة|دوري|ترتيب|كأس|المنتخب",
        r"سعر|ذهب|نفط|عملة|سوق", r"طقس|حرارة|مطر|رياح",
        r"ابحث لي|شوف لي|تحقق لي"
    ]
    return any(re.search(pat, p) for pat in force)

def search_web(query):
    sources = []
    text = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if results:
            sources = [{"title": r.get('title',''), "url": r.get('href','')} for r in results]
            text = "\n".join(f"• {r.get('title','')}: {r.get('body','')[:150]}" for r in results)
    except: pass
    return text, sources

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>نبراس GT</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;font-family:'Segoe UI',sans-serif}
.app{max-width:750px;margin:0 auto;height:100dvh;display:flex;flex-direction:column}
.header{height:52px;padding:0 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #eee}
.icon-btn{width:28px;height:28px;border:none;background:transparent;font-size:18px;cursor:pointer;border-radius:50%}
.dropdown{display:none;position:absolute;top:60px;right:20px;background:#fff;box-shadow:0 4px 12px rgba(0,0,0,0.1);border-radius:10px;padding:8px 0;z-index:99}
.dropdown.active{display:block}
.dropdown .item{padding:8px 16px;cursor:pointer;font-size:14px}
.dropdown .item:hover{background:#f5f5f5}
.chat-box{flex:1;padding:16px;background:#f9fafb;overflow-y:auto;display:flex;flex-direction:column;gap:12px}
.msg{max-width:78%;padding:12px 16px;border-radius:18px;line-height:1.6}
.msg.user{background:linear-gradient(135deg,#0077b6,#005c99);color:#fff;align-self:flex-end;border-bottom-right-radius:6px}
.msg.bot{background:#fff;align-self:flex-start;border-bottom-left-radius:6px}
.time{font-size:10px;color:#999;display:block;margin-top:4px}
.typing{display:flex;gap:5px;padding:12px 16px;background:#fff;border-radius:18px;align-self:flex-start;border-bottom-left-radius:6px}
.typing span{width:8px;height:8px;background:#ccc;border-radius:50%;animation:bounce 1.2s infinite}
.typing span:nth-child(2){animation-delay:0.2s}
.typing span:nth-child(3){animation-delay:0.4s}
@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px);background:#0077b6}}
.input-bar{padding:12px 16px;background:#fff;border-top:1px solid #eee;display:flex;gap:10px;align-items:center}
.input-wrap{flex:1;display:flex;align-items:center;background:#f5f7fa;border-radius:25px;padding:0 15px}
.input-wrap input{flex:1;border:none;background:transparent;padding:10px;outline:none;font-size:15px}
.send-btn{width:40px;height:40px;border-radius:50%;border:none;background:linear-gradient(135deg,#0077b6,#005c99);color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center}
</style>
</head>
<body>
<div class="app">
    <div class="header">
        <button class="icon-btn" id="newBtn"><i class="fa-solid fa-plus"></i></button>
        <button class="icon-btn" id="menuBtn"><i class="fa-solid fa-bars"></i></button>
        <div class="dropdown" id="menu">
            <div class="item" onclick="alert('📅 '+new Date().toLocaleDateString('ar-SA'))">التاريخ</div>
            <div class="item" onclick="alert('💬 تم تطويري وبرمجتي على يد مطورين ومبرمجين بالتقنية الحديثة، وأنا هنا لمساعدتك')">عن نبراس</div>
            <div class="item" onclick="location.reload()">تحديث</div>
        </div>
    </div>
    <div class="chat-box" id="chat">
        <div class="msg bot">هلا وسهلا بك! أنا نبراس، وش أخبارك اليوم؟ 😊<span class="time">الآن</span></div>
    </div>
    <div class="input-bar">
        <div class="input-wrap">
            <input type="text" id="txt" placeholder="اكتب ما تريد...">
        </div>
        <button class="send-btn" id="send"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
</div>
<script>
const chat = document.getElementById('chat');
const txt = document.getElementById('txt');
const send = document.getElementById('send');
const menuBtn = document.getElementById('menuBtn');
const menu = document.getElementById('menu');

function getTime(){return new Date().toLocaleTimeString('ar-SA',{hour:'2-digit',minute:'2-digit'})}
function showTyping(){const d=document.createElement('div');d.className='typing';d.innerHTML='<span></span><span></span><span></span>';chat.appendChild(d);chat.scrollTop=chat.scrollHeight}
function hideTyping(){document.querySelector('.typing')?.remove()}
function addUser(msg){const d=document.createElement('div');d.className='msg user';d.textContent=msg;d.innerHTML+=`<span class="time">${getTime()}</span>`;chat.appendChild(d);chat.scrollTop=chat.scrollHeight}

// ✅ دالة الكتابة المتقطعة الحقيقية حرفاً بحرف
async function addBotStream(text){
    const d=document.createElement('div');d.className='msg bot';chat.appendChild(d);chat.scrollTop=chat.scrollHeight;
    for(let ch of text){
        d.textContent+=ch;
        chat.scrollTop=chat.scrollHeight;
        // سرعة طبيعية جداً ومريحة
        await new Promise(r=>setTimeout(r,35));
    }
    d.innerHTML+=`<span class="time">${getTime()}</span>`;
}

menuBtn.onclick=e=>{e.stopPropagation();menu.classList.toggle('active')};
document.onclick=()=>menu.classList.remove('active');
document.getElementById('newBtn').onclick=()=>{chat.innerHTML='';addBotStream('هلا وسهلا! أنا نبراس، وش أخبارك اليوم؟ 😊')};

send.onclick=async()=>{
    const m=txt.value.trim();
    if(!m)return;
    txt.value='';
    addUser(m);
    showTyping();
    try{
        const res=await fetch('/chat',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({msg:m})
        });
        hideTyping();
        // نقرأ الرد كاملاً أولاً ثم نكتبه متقطع قدامك (أضمن طريقة ولا تخطئ أبداً)
        const fullText=await res.text();
        await addBotStream(fullText);
    }catch(e){hideTyping();addBotStream('⚠️ تعذر الاتصال، جرب مرة أخرى')}
};
txt.onkeydown=e=>{if(e.key==='Enter')send.click()};
</script>
</body>
</html>
"""

@app.route("/")
def index():
    session.clear()
    return HTML

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("msg","").strip()

    # ردود ثابتة
    if user_msg and any(w in user_msg for w in ["برمج", "مطور", "من صنعك", "من طورك"]):
        return Response("تم تطويري وبرمجتي على يد مطورين ومبرمجين بالتقنية الحديثة، وأنا هنا لمساعدتك في كل ما تحتاج 😊", mimetype="text/plain")
    if user_msg and is_pure_date_question(user_msg):
        return Response(f"اليوم هو {get_real_date()}", mimetype="text/plain")

    # إعداد البيانات
    need_sources = user_asks_for_sources(user_msg)
    FORCE_SEARCH = MUST_SEARCH(user_msg)
    search_text, sources = search_web(user_msg) if (user_msg and FORCE_SEARCH) else ("", [])
    session["last_sources"] = sources
    session["had_search"] = FORCE_SEARCH or bool(sources)

    if need_sources:
        out = "✅ تفضل المصادر:\n\n" if session.get("had_search") else "المعلومة من بياناتي، ما احتجت بحث 😊\n\n"
        for i,s in enumerate(session.get("last_sources",[]),1): out += f"{i}. {s['title']}\n{s['url']}\n\n"
        return Response(out.strip(), mimetype="text/plain")

    # بناء الرد
    sys_prompt = f"""أنت نبراس، المساعد الذكي.
- تحدث بلهجة سعودية عامية واضحة، طبيعية جداً.
- لا تذكر أنك ذكاء اصطناعي ولا تظهر روابط.
- تاريخ اليوم: {get_real_date()}
{('معلومات حديثة:\n'+search_text) if search_text else ''}
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_msg}],
        max_tokens=900,
        temperature=0.7
    ).choices[0].message.content.strip()

    if FORCE_SEARCH or sources:
        resp += "\n💡 لو تريد المصادر قل لي وأجيبك بها."

    return Response(resp, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
