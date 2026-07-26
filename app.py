from flask import Flask, request, jsonify, render_template_string
import openai
import os
import requests

app = Flask(__name__)

# 🔑 المفتاح
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ المفتاح غير موجود")
client = openai.OpenAI(api_key=API_KEY)

# 📚 ملف المعرفة
KNOWLEDGE_FILE = "Knowledge.md"
knowledge_content = ""
if os.path.exists(KNOWLEDGE_FILE):
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge_content = f.read()
    except:
        pass

# 🔍 البحث
def search_web(query):
    try:
        res = requests.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "kl": "ar-sa"}, timeout=8).json()
        return res.get("AbstractText") or ""
    except:
        return ""

# 🧠 التعليمات
SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد أهل السعودية والخليج.
تحدث باللهجة السعودية العامية الواضحة، جمل قصيرة وطبيعية كإنسان حقيقي.
لا تقل أبداً "لا أقدر أبحث". إذا كان السؤال عن سعر، موعد، أخبار، نتيجة، أو شيء حديث، سيتم جلب المعلومات لك تلقائياً، فأجب بها مباشرة.
تفاعل بود ورحب، ولا تطيل الكلام.

معلوماتك الخاصة:
{knowledge_content}
"""

# 📱 الواجهة بالشكل الذي تريده بالضبط
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
    <style>
        *{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}
        html,body{height:100%;background:#fff;color:#111;overflow:hidden}
        .app{display:flex;flex-direction:column;height:100vh}
        .top-bar{position:relative;padding:12px 16px;text-align:right}
        .menu-btn{border:none;background:none;font-size:20px;color:#333;cursor:pointer;padding:6px}
        .dropdown{position:absolute;top:45px;right:12px;background:#fff;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.15);display:none;flex-direction:column;min-width:160px;z-index:999}
        .dropdown.show{display:flex}
        .dropdown button{padding:12px 16px;border:none;background:none;text-align:right;font-size:14px;cursor:pointer;border-bottom:1px solid #f5f5f5}
        .dropdown button:last-child{border-bottom:none}
        #chat{flex:1;overflow-y:auto;padding:12px}
        .msg{max-width:80%;padding:10px 14px;border-radius:18px;margin-bottom:8px;position:relative;white-space:pre-wrap}
        .user{background:#f0f0f0;margin-left:auto}
        .bot{background:#f8f8f8;margin-right:auto}
        .time{font-size:10px;color:#999;margin-top:4px;display:block}
        .speak{position:absolute;left:8px;bottom:4px;border:none;background:none;color:#888;cursor:pointer}
        .input-area{display:flex;align-items:center;gap:8px;padding:10px 14px;margin:8px;background:#f9f9f9;border-radius:25px;border:1px solid #eee}
        .input-area input{flex:1;border:none;background:transparent;outline:none}
        .icon{border:none;background:none;color:#555;font-size:18px;cursor:pointer;padding:4px}
        .send{background:#222;color:#fff;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center}
    </style>
</head>
<body>
<div class="app">
    <div class="top-bar">
        <button class="menu-btn" id="menu"><i class="fas fa-ellipsis-v"></i></button>
        <div class="dropdown" id="list">
            <button id="new"><i class="fas fa-plus"></i> محادثة جديدة</button>
            <button id="history"><i class="fas fa-clock"></i> المحادثات السابقة</button>
        </div>
    </div>
    <div id="chat"></div>
    <div class="input-area">
        <button class="icon" id="pic"><i class="fas fa-image"></i></button>
        <button class="icon" id="mic"><i class="fas fa-microphone"></i></button>
        <input type="text" id="txt" placeholder="اكتب رسالتك..." />
        <button class="icon send" id="go"><i class="fas fa-paper-plane"></i></button>
    </div>
</div>

<script>
function spk(t){if(window.speechSynthesis){let u=new SpeechSynthesisUtterance(t);u.lang='ar-SA';speechSynthesis.speak(u);}}
async function typeText(el,txt){el.textContent='';for(let c of txt){el.textContent+=c;chat.scrollTop=chat.scrollHeight;await new Promise(r=>setTimeout(r,20));}}
function add(who,txt){let d=document.createElement('div');d.className='msg '+(who==='user'?'user':'bot');let t=new Date().toLocaleTimeString('ar-SA',{hour:'2-digit',minute:'2-digit'});
if(who==='bot'){let b=document.createElement('button');b.className='speak';b.innerHTML='🔊';b.onclick=()=>spk(txt);d.appendChild(b);typeText(d,txt+`\n<span class="time">${t}</span>`);}
else{d.textContent=txt;d.innerHTML+=`<span class="time">${t}</span>`;}
chat.appendChild(d);chat.scrollTop=chat.scrollHeight;}

// التحكم في القائمة
document.getElementById('menu').onclick=()=>document.getElementById('list').classList.toggle('show');
document.addEventListener('click',e=>{if(!e.target.closest('.top-bar'))document.getElementById('list').classList.remove('show');});
document.getElementById('new').onclick=()=>{chat.innerHTML='';document.getElementById('list').classList.remove('show');};
document.getElementById('history').onclick=()=>{alert('سيتم تفعيلها قريباً، حالياً محادثة جديدة');document.getElementById('list').classList.remove('show');};

// الإرسال
document.getElementById('go').onclick=snd;document.getElementById('txt').onkeydown=e=>e.key==='Enter'&&snd();
async function snd(){let v=txt.value.trim();if(!v)return;add('user',v);txt.value='';try{let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({m:v})});let j=await r.json();add('bot',j.reply||'تم')}catch{add('bot','خطأ')}}
</script>
</body>
</html>
    ''')

# 📨 المعالجة
@app.route('/chat', methods=['POST'])
def chat():
    msg = request.json.get("m", "").strip()
    if not msg:
        return jsonify({"reply": "اكتب شيء"})

    search_words = ["متى", "سعر", "اسعار", "اخبار", "نتيجة", "موسم", "موعد", "احدث"]
    need_search = any(k in msg.lower() for k in search_words)
    info = search_web(msg) if need_search else ""
    full = f"{SYSTEM_PROMPT}\n\nالسؤال: {msg}\n\nمعلومات حديثة: {info or 'لا يحتاج بحث'}"

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":full},{"role":"user","content":msg}],
        temperature=0.7
    )
    return jsonify({"reply": res.choices[0].message.content.strip()})

if __name__ == '__main__':
    app.run(debug=False)
