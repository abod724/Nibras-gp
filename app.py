import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# قراءة مفاتيح من صندوق الأسرار
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BING_KEY = os.getenv("BING_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def search_web(query: str) -> str:
    if not query or not BING_KEY:
        return ""
    try:
        url = f"https://api.bing.microsoft.com/v7.0/search?q={query}"
        headers = {"Ocp-Apim-Subscription-Key": BING_KEY}
        r = requests.get(url, headers=headers).json()
        items = r.get("webPages", {}).get("value", [])
        context = ""
        for item in items[:3]:
            name = item.get("name", "")
            snippet = item.get("snippet", "")
            context += f"- {name}: {snippet}\n"
        return context.strip()
    except Exception:
        return ""

def get_real_date() -> str:
    try:
        r = requests.get("https://worldtimeapi.org/api/timezone/Asia/Riyadh").json()
        return r.get("datetime", "").split("T")[0]
    except Exception:
        return "غير متوفر"

HTML = """
<!DOCTYPE html>
<html lang='ar' dir='rtl'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>نبراس GT</title>

<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
    background:#f7f7f8;
    font-family:'Segoe UI', Tahoma;
    overflow:hidden;
}
.app {
    height:100vh;
    max-width:800px;
    margin:auto;
    background:white;
    display:flex;
    flex-direction:column;
    box-shadow:0 0 30px rgba(0,0,0,0.05);
}

/* الهيدر */
.header {
    height:52px;
    border-bottom:1px solid #e5e5e5;
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:0 16px;
}
.header .btn {
    width:36px;
    height:36px;
    border:none;
    background:transparent;
    cursor:pointer;
    border-radius:6px;
    display:flex;
    align-items:center;
    justify-content:center;
}
.header .btn:hover { background:#f0f0f0; }
.header .title { font-size:16px; font-weight:600; }

/* القائمة المنسدلة */
.dropdown {
    display:none;
    position:absolute;
    right:12px;
    top:52px;
    background:white;
    border-radius:10px;
    box-shadow:0 4px 20px rgba(0,0,0,0.12);
    border:1px solid #e5e5e5;
    padding:6px;
    min-width:160px;
}
.dropdown.active { display:block; }
.dropdown .item {
    padding:8px 14px;
    border-radius:6px;
    cursor:pointer;
    font-size:14px;
}
.dropdown .item:hover { background:#f0f0f0; }

/* الرسائل */
.chat-box {
    flex:1;
    overflow-y:auto;
    padding:16px 20px;
    display:flex;
    flex-direction:column;
    gap:6px;
}
.msg {
    max-width:80%;
    padding:10px 14px;
    border-radius:16px;
    font-size:15px;
    line-height:1.5;
}
.msg.user {
    background:#1a1a1a;
    color:white;
    align-self:flex-end;
    border-bottom-right-radius:4px;
}
.msg.bot {
    background:white;
    color:#1a1a1a;
    align-self:flex-start;
    border-bottom-left-radius:4px;
    box-shadow:0 1px 4px rgba(0,0,0,0.05);
}
.time {
    font-size:9px;
    color:#aaa;
    margin-top:4px;
    display:block;
}

/* شريط الإدخال */
.input-bar {
    padding:10px;
    border-top:1px solid #e5e5e5;
    display:flex;
    gap:6px;
}
.wrapper {
    flex:1;
    background:#f0f0f0;
    border-radius:24px;
    padding:4px 6px;
    display:flex;
    align-items:center;
    gap:6px;
}
.wrapper input {
    flex:1;
    border:none;
    background:transparent;
    padding:8px;
    font-size:14px;
    outline:none;
}
.icon-btn {
    width:28px;
    height:28px;
    border:none;
    background:transparent;
    cursor:pointer;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
}
.icon-btn:hover { background:#e0e0e0; }

.send-btn {
    width:38px;
    height:38px;
    border:none;
    border-radius:50%;
    background:#1a1a1a;
    color:white;
    cursor:pointer;
}
.send-btn:hover { background:#333; }
</style>
</head>

<body>
<div class='app'>

    <div class='header'>
        <button class='btn' id='newChatBtn'>+</button>
        <span class='title'>نبراس GT</span>
        <button class='btn' id='menuBtn'>≡</button>
    </div>

    <div class='dropdown' id='dropdownMenu'>
        <div class='item' onclick="setMode('new')">محادثة جديدة</div>
        <div class='item' onclick="setMode('web')">البحث بالويب</div>
        <div class='item' onclick="setMode('openai')">البحث عبر OpenAI</div>
        <div class='item' onclick="toggleDark()">الوضع الليلي</div>
        <div class='item' onclick="alert('نبراس GT — تصميم أبو مشعل')">حول</div>
    </div>

    <div class='chat-box' id='chatBox'>
        <div class='msg bot'>مرحباً! أنا نبراس GT، كيف أساعدك؟ <span class='time'>الآن</span></div>
    </div>

    <div class='input-bar'>
        <div class='wrapper'>
            <button class='icon-btn' id='micBtn'>🎙️</button>
            <button class='icon-btn' id='imageBtn'>📸</button>
            <input type='text' id='userInput' placeholder='اكتب سؤالك...'>
            <input type='file' id='fileInput' accept='image/*' multiple style='display:none'>
        </div>
        <button class='send-btn' id='sendBtn'>➤</button>
    </div>

</div>

<script>
let searchMode = "web";

function setMode(mode) {
    searchMode = mode;

    if (mode === "new") {
        chatBox.innerHTML = "";
        appendMessage('bot', 'مرحباً! أنا نبراس GT، كيف أساعدك؟');
    }

    dropdown.classList.remove("active");
}

function toggleDark() {
    document.body.classList.toggle("dark");
}

const chatBox = document.getElementById('chatBox');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const menuBtn = document.getElementById('menuBtn');
const dropdown = document.getElementById('dropdownMenu');
const newChatBtn = document.getElementById('newChatBtn');

menuBtn.onclick = ()=> dropdown.classList.toggle('active');

function getTime() {
    return new Date().toLocaleTimeString('ar-SA', {hour:'2-digit', minute:'2-digit'});
}

function appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.innerHTML = text + "<span class='time'>" + getTime() + "</span>";
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

sendBtn.onclick = sendMessage;
userInput.onkeydown = (e)=>{ if(e.key==='Enter') sendMessage(); };

function sendMessage() {
    const msg = userInput.value.trim();
    if(!msg) return;

    appendMessage('user', msg);
    userInput.value = '';

    fetch('/chat', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:msg, mode:searchMode})
    })
    .then(r=>r.json())
    .then(d=>appendMessage('bot', d.reply));
}
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return HTML

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "").strip()
    mode = data.get("mode", "web")

    search_context = search_web(user_msg) if mode == "web" else ""
    current_date = get_real_date()

    system_prompt = f"""
أنت نبراس GT.
التاريخ: {current_date}
{search_context}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":user_msg}
        ],
        max_tokens=200
    )

    return jsonify({"reply": response.choices[0].message.content})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
