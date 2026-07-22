from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI
import os
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

# ─── المفتاح من متغيرات البيئة ───
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ OPENAI_API_KEY غير موجود")

client = OpenAI(api_key=API_KEY)

# ─── شخصية نبراس ───
NBRAS_KNOWLEDGE = """
تحدث باللهجة السعودية العامية.
جمل قصيرة ومباشرة.
لا تتفلسف، ولا تطيل (حد أقصى 4 جمل).
إذا سألك عن المبرمج: قل "أنا من تطوير أبو مشعل المطيري".
لا تظهر روابط، ولا تذكر أنك تبحث.
"""

# ─── البحث في الويب ───
def search_web(query):
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1}
        r = requests.get(url, params=params, timeout=5)
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

# ─── التاريخ ───
def get_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

# ─── ذاكرة المحادثة ───
chat_sessions = {}

# ─── الواجهة النهائية الثابتة تماماً ───
HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>نبراس</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
        html, body {
            /* شلنا 100vh و overflow:hidden المسببة للمشكلة */
            min-height: 100%;
            background-color: #f8f9fa;
            color: #212529;
        }
        body {
            display: flex;
            flex-direction: column;
            height: 100dvh; /* نستخدم dvh الجديدة التي تتعامل مع الجوال بشكل صحيح */
            position: fixed;
            width: 100%;
        }

        .header {
            background: #ffffff;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #e9ecef;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            flex-shrink: 0;
            z-index: 10;
        }

        .dropdown {
            position: relative;
            display: inline-block;
        }
        .dropbtn {
            background: #e7f1ff;
            color: #0d6efd;
            border: none;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
            transition: 0.2s;
        }
        .dropbtn:hover { background: #0d6efd; color: white; }
        .dropdown-content {
            display: none;
            position: absolute;
            right: 0;
            background-color: white;
            min-width: 160px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            margin-top: 8px;
            overflow: hidden;
            border: 1px solid #e9ecef;
            z-index: 999;
        }
        .dropdown-content button {
            color: #212529;
            padding: 10px 16px;
            text-decoration: none;
            display: block;
            width: 100%;
            text-align: right;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 14px;
        }
        .dropdown-content button:hover { background-color: #f8f9fa; color: #0d6efd; }
        .show { display: block; }

        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 12px 10px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .msg {
            padding: 10px 14px;
            border-radius: 16px;
            max-width: 80%;
            font-size: 14px;
            line-height: 1.6;
            word-wrap: break-word;
            flex-shrink: 0;
        }
        .msg.user {
            background: #0d6efd;
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .msg.bot {
            background: #ffffff;
            color: #212529;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
            border: 1px solid #e9ecef;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .time {
            font-size: 10px;
            margin-top: 4px;
            display: block;
            opacity: 0.6;
        }

        .typing {
            align-self: flex-start;
            background: white;
            padding: 10px 14px;
            border-radius: 16px;
            border-bottom-left-radius: 4px;
            border: 1px solid #e9ecef;
            display: flex;
            gap: 4px;
            flex-shrink: 0;
        }
        .typing span {
            width: 7px; height: 7px;
            background: #adb5bd;
            border-radius: 50%;
            animation: bounce 1.2s infinite;
        }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-4px); }
        }

        .input-area {
            background: white;
            padding: 10px 12px 14px;
            border-top: 1px solid #e9ecef;
            flex-shrink: 0;
            z-index: 10;
        }
        .input-wrap {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #f8f9fa;
            border-radius: 24px;
            padding: 8px 12px;
            border: 1px solid #dee2e6;
        }
        .input-wrap input {
            flex: 1;
            border: none;
            background: transparent;
            padding: 6px;
            font-size: 14px;
            outline: none;
            color: #212529;
        }
        .input-wrap input::placeholder { color: #adb5bd; }

        .icon-btn {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: #6c757d;
            font-size: 15px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
            flex-shrink: 0;
        }
        .icon-btn:hover { background: #e9ecef; color: #0d6efd; }

        .send-btn {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background: #0d6efd;
            color: white;
            font-size: 15px;
            cursor: pointer;
            transition: 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .send-btn:hover { transform: scale(1.05); }
        .send-btn:disabled { background: #adb5bd; cursor: not-allowed; }

        @media (max-width: 480px) {
            .msg { max-width: 88%; font-size: 13px; }
            .header { padding: 10px 12px; }
            .input-area { padding: 8px 10px 12px; }
        }
    </style>
</head>
<body>

<div class="header">
    <button class="dropbtn" id="newChatBtn">محادثة جديدة</button>
    <div class="dropdown">
        <button class="dropbtn" id="menuBtn"><i class="fa-solid fa-bars"></i> خيارات</button>
        <div class="dropdown-content" id="myDropdown">
            <button onclick="resetChat()">🔄 محادثة جديدة</button>
            <button onclick="alert('⚙️ الإعدادات قيد التطوير')">⚙️ الإعدادات</button>
        </div>
    </div>
</div>

<div class="chat-container" id="chatBox">
    <div class="msg bot">هلا وسهلا بك! أنا نبراس، جاهز لأخدمك. وش أخبارك اليوم؟ 😊 <span class="time">الآن</span></div>
</div>

<div class="input-area">
    <div class="input-wrap">
        <button class="icon-btn" id="imgBtn"><i class="fa-solid fa-image"></i></button>
        <button class="icon-btn" id="micBtn"><i class="fa-solid fa-microphone"></i></button>
        <input type="text" id="userInput" placeholder="اكتب سؤالك هنا...">
        <button class="send-btn" id="sendBtn"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
</div>

<script>
    const chatBox = document.getElementById('chatBox');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const micBtn = document.getElementById('micBtn');
    const imgBtn = document.getElementById('imgBtn');
    const menuBtn = document.getElementById('menuBtn');
    const dropdown = document.getElementById('myDropdown');
    let sessionId = 'user_' + Date.now();

    window.onclick = function(event) {
        if (!event.target.matches('#menuBtn')) {
            if (dropdown.classList.contains('show')) {
                dropdown.classList.remove('show');
            }
        }
    }
    menuBtn.onclick = (e) => { e.stopPropagation(); dropdown.classList.toggle('show'); };

    function resetChat() {
        dropdown.classList.remove('show');
        chatBox.innerHTML = '';
        sessionId = 'user_' + Date.now();
        appendMessage('bot', 'هلا وسهلا! وش أخبارك اليوم؟');
    }

    function getTime() {
        return new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
    }

    const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    rec.lang = 'ar-SA';
    rec.continuous = false;
    micBtn.onclick = () => { rec.start(); micBtn.style.color='#0d6efd'; };
    rec.onresult = e => { userInput.value = e.results[0][0].transcript; micBtn.style.color='#6c757d'; sendBtn.click(); };
    rec.onend = () => micBtn.style.color='#6c757d';

    function appendMessage(role, text) {
        const div = document.createElement('div');
        div.className = `msg ${role}`;
        div.innerHTML = `${text} <span class="time">${getTime()}</span>`;
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function showTyping() {
        const div = document.createElement('div');
        div.className = 'typing';
        div.id = 'typingIndicator';
        div.innerHTML = '<span></span><span></span><span></span>';
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function hideTyping() {
        const el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }

    async function sendMessage(text) {
        if (!text || !text.trim()) return;
        const msg = text.trim();
        appendMessage('user', msg);
        userInput.value = '';
        sendBtn.disabled = true;
        showTyping();

        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg, session_id: sessionId })
            });
            const data = await res.json();
            hideTyping();
            appendMessage('bot', data.reply || '⚠️ عذراً، لم أفهم');
        } catch (e) {
            hideTyping();
            appendMessage('bot', '⚠️ تعذر الاتصال، جرب مرة أخرى');
        }
        sendBtn.disabled = false;
        // ✅ شلنا userInput.focus() المسبب للارتجاع تماماً
    }

    sendBtn.addEventListener('click', () => sendMessage(userInput.value));
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendMessage(userInput.value);
    });
    document.getElementById('newChatBtn').addEventListener('click', resetChat);

    imgBtn.addEventListener('click', () => {
        alert('📸 خاصية رفع الصور قيد التطوير قريباً بإذن الله');
    });

    // ✅ شلنا التركيز التلقائي عند فتح الصفحة
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not user_msg:
        return jsonify({"reply": "اكتب سؤالك"}), 400

    if session_id not in chat_sessions:
        chat_sessions[session_id] = []
    chat_sessions[session_id].append({"role": "user", "content": user_msg})

    search_keywords = ["أخبار", "حدث", "اليوم", "سعر", "طقس", "مباراة", "نتيجة", "جديد", "آخر"]
    search_context = search_web(user_msg) if any(kw in user_msg.lower() for kw in search_keywords) else ""

    system_prompt = f"""أنت نبراس، صديق ومساعد سعودي.
{NBRAS_KNOWLEDGE}
التاريخ اليوم: {get_date()}.
{f"معلومات حديثة: {search_context}" if search_context else ""}
تكلم بلهجة سعودية واضحة، ردود قصيرة وودودة، كأنك تتكلم مع صديق.
"""

    try:
        messages = [{"role": "system", "content": system_prompt}] + chat_sessions[session_id]
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=600,
            temperature=0.7
        )
        reply = res.choices[0].message.content.strip()
        chat_sessions[session_id].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"⚠️ خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
