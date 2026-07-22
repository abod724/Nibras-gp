from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI
import os
import re
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

# ─── المفتاح من متغيرات البيئة ───
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ OPENAI_API_KEY غير موجود")

client = OpenAI(api_key=API_KEY)

# ─── قراءة ملف المعرفة ───
KNOWLEDGE_FILE = "knowledge.md"
knowledge_content = ""
if os.path.exists(KNOWLEDGE_FILE):
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge_content = f.read()
    except Exception:
        knowledge_content = ""

# ─── التاريخ ───
def get_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

# ─── تنظيف الرد من الروابط ───
def clean_reply(reply):
    reply = re.sub(r'https?://\S+|www\.\S+', '', reply)
    reply = re.sub(r'\s+', ' ', reply).strip()
    return reply

# ─── تحديد الحاجة للبحث (أوامر صارمة وشاملة) ───
def NEEDS_SEARCH(prompt):
    p = prompt.strip().lower()
    patterns = [
        r"خبر|أخبار|حدث|وش صار|ايش صار|مستجدات|عاجل|حاصل",
        r"اليوم|هذا الأسبوع|هذا الشهر|الآن|حاليا|آخر|أحدث|جديد|مؤخرا",
        r"202[4-9]|203",
        r"مباراة|نتيجة|دوري|كأس|المنتخب|فاز|خسر|ترتيب|بطولة",
        r"سعر|كم يساوي|سوق|ذهب|نفط|عملة|ارتفاع|انخفاض|أسعار",
        r"طقس|حرارة|مطر|رياح|حالة الجو|غبار",
        r"موعد|متى|وقت|تاريخ قادم",
        r"ابحث لي|شوف لي|قل لي وش صار|وش الجديد|أريد أعرف|معلومات عن|كم|متى|من هو|وش هي"
    ]
    for pat in patterns:
        if re.search(pat, p):
            return True
    return False

# ─── البحث في الويب ───
def search_web(query):
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        r = requests.get(url, params=params, timeout=6)
        data = r.json()
        results = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        for topic in data.get("RelatedTopics", [])[:3]:
            if "Text" in topic:
                results.append(topic["Text"])
        return "\n".join(results) if results else ""
    except:
        return ""

# ─── واجهة HTML كاملة بالصوت والتصميم ───
HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نبراس</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100%; overflow: hidden; font-family: 'Segoe UI', sans-serif; background: #f7f7f8; }
        .app { max-width: 750px; margin: 0 auto; height: 100%; display: flex; flex-direction: column; }
        .header { background: #fff; padding: 12px 20px; border-bottom: 1px solid #e5e5e5; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
        .header h1 { font-size: 18px; font-weight: 600; }
        .header button { background: transparent; border: none; font-size: 20px; cursor: pointer; color: #555; padding: 6px; border-radius: 50%; }
        .header button:hover { background: #f0f0f0; }
        .chat-box { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; min-height: 0; }
        .msg { max-width: 78%; padding: 12px 16px; border-radius: 18px; font-size: 15px; line-height: 1.7; animation: fadeIn 0.25s ease; }
        .msg.user { background: linear-gradient(135deg,#0077b6,#005c99); color: #fff; align-self: flex-end; border-bottom-right-radius: 6px; }
        .msg.bot { background: #fff; color: #1a1a1a; align-self: flex-start; border-bottom-left-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
        .msg .time { font-size: 10px; color: #999; display: block; margin-top: 4px; }
        @keyframes fadeIn { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:translateY(0) } }
        .typing { align-self: flex-start; background: #fff; padding: 12px 18px; border-radius: 18px; display: flex; gap: 5px; }
        .typing span { width:8px; height:8px; background:#b0b8c8; border-radius:50%; animation:bounce 1.2s infinite; }
        .typing span:nth-child(2){animation-delay:0.2s}
        .typing span:nth-child(3){animation-delay:0.4s}
        @keyframes bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-6px)} }
        .input-bar { background: #fff; padding: 12px 16px 20px; border-top: 1px solid #e5e5e5; display: flex; gap: 10px; align-items: center; flex-shrink: 0; }
        .wrap { flex:1; display:flex; align-items:center; background:#f0f0f0; border-radius:24px; padding: 6px 14px; }
        .icon-btn { border:none; background:none; font-size:18px; color:#666; cursor:pointer; padding:6px; border-radius:50%; width:32px; height:32px; display:flex; align-items:center; justify-content:center; }
        .icon-btn:hover { color:#0077b6; }
        .wrap input { flex:1; border:none; background:transparent; padding:8px; font-size:15px; outline:none; }
        .send-btn { background:linear-gradient(135deg,#0077b6,#005c99); color:white; border:none; border-radius:50%; width:40px; height:40px; font-size:16px; cursor:pointer; display:flex; align-items:center; justify-content:center; }
        .send-btn:disabled { background:#ccc; }
    </style>
</head>
<body>
<div class="app">
    <div class="header">
        <button id="newChatBtn"><i class="fa-solid fa-plus"></i></button>
        <h1>💬 نبراس</h1>
        <div></div>
    </div>
    <div class="chat-box" id="chatBox">
        <div class="msg bot">هلا وسهلا! أنا نبراس، وش أخبارك اليوم؟ 😊 <span class="time">الآن</span></div>
    </div>
    <div class="input-bar">
        <div class="wrap">
            <button class="icon-btn" id="micBtn"><i class="fa-solid fa-microphone"></i></button>
            <input type="text" id="userInput" placeholder="اكتب أو تحدث...">
        </div>
        <button class="send-btn" id="sendBtn"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
</div>

<script>
const chatBox = document.getElementById('chatBox');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const newChatBtn = document.getElementById('newChatBtn');
let sessionId = 'user_' + Date.now();

function getTime(){return new Date().toLocaleTimeString('ar-SA',{hour:'2-digit',minute:'2-digit'})}

// نظام الصوت
const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = 'ar-SA';
recognition.continuous = false;

function نبراس_يتكلم(نص){
    window.speechSynthesis.cancel();
    const صوت = new SpeechSynthesisUtterance(نص);
    صوت.lang = 'ar-SA';
    صوت.rate = 1.05;
    const الاصوات = window.speechSynthesis.getVoices();
    const عربي = الاصوات.find(v=>v.lang.startsWith('ar')) || الاصوات[0];
    if(عربي) صوت.voice = عربي;
    window.speechSynthesis.speak(صوت);
}
window.speechSynthesis.onvoiceschanged = ()=>{};

micBtn.addEventListener('click',()=>{
    window.speechSynthesis.cancel();
    recognition.start();
    micBtn.style.color='#0077b6';
});
recognition.onresult=(e)=>{
    userInput.value = e.results[0][0].transcript;
    micBtn.style.color='#666';
    sendBtn.click();
};
recognition.onend=()=>micBtn.style.color='#666';

function appendMsg(role,text){
    const d=document.createElement('div');d.className=`msg ${role}`;
    d.innerHTML=`${text} <span class="time">${getTime()}</span>`;
    chatBox.appendChild(d);chatBox.scrollTop=chatBox.scrollHeight;
    if(role==='bot') نبراس_يتكلم(text);
}
function showTyping(){const d=document.createElement('div');d.className='typing';d.id='typing';d.innerHTML='<span></span><span></span><span></span>';chatBox.appendChild(d);chatBox.scrollTop=chatBox.scrollHeight}
function hideTyping(){document.getElementById('typing')?.remove()}

async function sendMsg(){
    const txt=userInput.value.trim();if(!txt)return;
    appendMsg('user',txt);userInput.value='';sendBtn.disabled=true;showTyping();
    try{
        const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt,session:sessionId})});
        const d=await r.json();hideTyping();appendMsg('bot',d.reply||'⚠️ عذراً');
    }catch(e){hideTyping();appendMsg('bot','⚠️ تعذر الاتصال')}
    sendBtn.disabled=false;
}

sendBtn.addEventListener('click',sendMsg);
userInput.addEventListener('keydown',e=>{if(e.key==='Enter')sendMsg()});
newChatBtn.addEventListener('click',()=>{chatBox.innerHTML='';sessionId='user_'+Date.now();appendMsg('bot','هلا وسهلا! وش أخبارك؟')});
</script>
</body>
</html>
"""

chat_sessions = {}

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = (data.get("message") or "").strip()
    session_id = data.get("session", "default")

    if not user_msg:
        return jsonify({"reply": "اكتب سؤالك"}), 400

    # البحث حسب الحاجة فقط
    search_result = search_web(user_msg) if NEEDS_SEARCH(user_msg) else ""

    # التعليمات الصارمة
    system_prompt = f"""أنت نبراس، صديقك ومساعدك الخاص.
🔹 تحدث دائماً بلهجة سعودية عامية بيضاء وواضحة، كلام طبيعي وقصير ومباشر، لا تطيل ولا تعقد.
🔹 استخدم معلومات ملف المعرفة أولاً إذا كانت مرتبطة بالسؤال.
🔹 إذا كان السؤال عن شيء حديث أو متغير أو يحتاج تحديث → استخدم ما جلبته لك من البحث فوراً.
🔹 لا تذكر أنك تبحث ولا تظهر روابط، واختم إجابتك بسؤال بسيط.
🔹 تاريخ اليوم: {get_date()}.
{('🔹 معلومات خاصة:\n'+knowledge_content) if knowledge_content else ''}
{('🔹 معلومات حديثة:\n'+search_result) if search_result else ''}
"""

    try:
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        chat_sessions[session_id].append({"role": "user", "content": user_msg})

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system_prompt}] + chat_sessions[session_id],
            max_tokens=600,
            temperature=0.7
        )

        reply = clean_reply(res.choices[0].message.content.strip())
        chat_sessions[session_id].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"⚠️ خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
