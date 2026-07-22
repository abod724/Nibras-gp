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

# ─── الواجهة الجديدة المحدثة ───
HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نبراس</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: system-ui, sans-serif; }
        body {
            background: #050816;
            color: #ffffff;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        .container {
            padding: 16px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 16px;
            overflow-y: auto;
        }

        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .new-chat-btn {
            background: #0d6efd;
            color: #fff;
            border: none;
            padding: 8px 16px;
            border-radius: 999px;
            font-size: 13px;
            cursor: pointer;
            transition: 0.2s;
        }
        .new-chat-btn:hover { background: #0b5ed7; }

        .chat-box {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 8px;
        }

        .msg {
            padding: 12px 16px;
            border-radius: 16px;
            max-width: 82%;
            font-size: 14px;
            line-height: 1.7;
            word-wrap: break-word;
        }
        .msg.user {
            background: #0d6efd;
            color: #fff;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .msg.bot {
            background: #111827;
            color: #e5e7eb;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
            border: 1px solid #1f2937;
        }
        .msg .time {
            font-size: 10px;
            color: #9ca3af;
            display: block;
            margin-top: 4px;
        }

        .typing {
            align-self: flex-start;
            background: #111827;
            padding: 12px 16px;
            border-radius: 16px;
            border-bottom-left-radius: 4px;
            display: flex;
            gap: 5px;
            border: 1px solid #1f2937;
        }
        .typing span {
            width: 8px; height: 8px;
            background: #9ca3af;
            border-radius: 50%;
            animation: pulse 1.2s infinite;
        }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes pulse {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
            30% { transform: translateY(-5px); opacity: 1; }
        }

        .input-bar {
            padding: 12px 16px;
            border-top: 1px solid #1f2937;
            background: #050816;
        }

        .input-wrapper {
            display: flex;
            align-items: center;
            gap: 10px;
            background: #111827;
            border-radius: 999px;
            padding: 10px 16px;
            border: 1px solid #1f2937;
        }

        .input-wrapper input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: #fff;
            font-size: 14px;
        }
        .input-wrapper input::placeholder { color: #6b7280; }

        .send-btn {
            background: #0d6efd;
            border: none;
            border-radius: 50%;
            width: 34px;
            height: 34px;
            color: #fff;
            font-size: 15px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
        }
        .send-btn:hover { transform: scale(1.05); }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        @media (max-width: 480px) {
            .msg { max-width: 88%; font-size: 13px; }
        }
    </style>
</head>
<body>

<div class="container" id="container">
    <div class="top-bar">
        <div></div>
        <button class="new-chat-btn" id="newChatBtn">محادثة جديدة +</button>
    </div>

    <div class="chat-box" id="chatBox">
        <div class="msg bot">هلا وسهلا بك! أنا نبراس، جاهز لأخدمك. وش أخبارك اليوم؟ 😊 <span class="time">الآن</span></div>
    </div>
</div>

<div class="input-bar">
    <div class="input-wrapper">
        <input type="text" id="userInput" placeholder="اكتب سؤالك هنا...">
        <button class="send-btn" id="sendBtn">➤</button>
    </div>
</div>

<script>
    const chatBox = document.getElementById('chatBox');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const newChatBtn = document.getElementById('newChatBtn');
    let sessionId = 'user_' + Date.now();

    function getTime() {
        return new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
    }

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
        userInput.focus();
    }

    // الأحداث
    sendBtn.addEventListener('click', () => sendMessage(userInput.value));
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendMessage(userInput.value);
    });

    newChatBtn.addEventListener('click', () => {
        chatBox.innerHTML = '';
        sessionId = 'user_' + Date.now();
        appendMessage('bot', 'هلا وسهلا! وش أخبارك اليوم؟');
    });

    userInput.focus();
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

    # البحث الذكي
    search_keywords = ["أخبار", "حدث", "اليوم", "سعر", "طقس", "مباراة", "نتيجة", "جديد", "آخر"]
    search_context = search_web(user_msg) if any(kw in user_msg.lower() for kw in search_keywords) else ""

    # التعليمات النهائية
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
