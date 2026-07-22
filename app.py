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
إذا سألك عن المبرمج: قل "أنا من صنع أبو مشعل المطيري".
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

# ─── الواجهة الجديدة (مدمجة مع وظائف المحادثة) ───
HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>نبراس</title>
    <style>
        body {
            margin: 0;
            font-family: system-ui, sans-serif;
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
            justify-content: flex-start;
            gap: 16px;
            overflow-y: auto;
        }

        .top-bar {
            display: flex;
            justify-content: flex-end;
        }

        .plus-btn {
            background: #0d6efd;
            color: #fff;
            border: none;
            padding: 8px 14px;
            border-radius: 999px;
            font-size: 13px;
            cursor: pointer;
        }

        .cards {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .card {
            background: #111827;
            border-radius: 14px;
            padding: 14px;
            border: 1px solid #1f2937;
            cursor: pointer;
            transition: 0.2s;
        }

        .card:hover {
            border-color: #0d6efd;
            transform: translateY(-1px);
        }

        .card-title {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .card-sub {
            font-size: 12px;
            color: #9ca3af;
        }

        .chat-box {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 8px;
        }

        .msg {
            padding: 10px 14px;
            border-radius: 14px;
            max-width: 85%;
            font-size: 14px;
            line-height: 1.6;
            word-wrap: break-word;
        }
        .msg.user {
            background: #0d6efd;
            color: #fff;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .msg.bot {
            background: #1f2937;
            color: #e5e7eb;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .msg .time {
            font-size: 10px;
            color: #9ca3af;
            display: block;
            margin-top: 4px;
        }
        .msg.user .time { color: #9ca3af; }

        .typing {
            align-self: flex-start;
            background: #1f2937;
            padding: 10px 16px;
            border-radius: 14px;
            border-bottom-left-radius: 4px;
            display: flex;
            gap: 4px;
        }
        .typing span {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #9ca3af;
            border-radius: 50%;
            animation: pulse 1.2s infinite;
        }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes pulse {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
            30% { transform: translateY(-6px); opacity: 1; }
        }

        .input-bar {
            padding: 10px 16px;
            border-top: 1px solid #1f2937;
            background: #050816;
        }

        .input-wrapper {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #111827;
            border-radius: 999px;
            padding: 8px 12px;
            border: 1px solid #1f2937;
        }

        .input-wrapper input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: #fff;
            font-size: 13px;
        }

        .input-wrapper input::placeholder {
            color: #6b7280;
        }

        .send-btn {
            background: #0d6efd;
            border: none;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            color: #fff;
            font-size: 14px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    </style>
</head>
<body>

<div class="container" id="container">
    <div class="top-bar">
        <button class="plus-btn" id="plusBtn">اشترك في Plus</button>
    </div>

    <div class="chat-box" id="chatBox">
        <div class="msg bot">مرحباً! أنا نبراس، كيف أساعدك؟ <span class="time">الآن</span></div>
    </div>

    <div class="cards" id="suggestions">
        <div class="card" data-prompt="أنشئ صورة لي">
            <div class="card-title">🖼️ أنشئ صورة</div>
            <div class="card-sub">اكتب وصفًا وسننشئ لك صورة</div>
        </div>
        <div class="card" data-prompt="ساعدني في كتابة نص">
            <div class="card-title">✍️ الكتابة أو التحرير</div>
            <div class="card-sub">اكتب نصًا وسنساعدك في صياغته</div>
        </div>
    </div>
</div>

<div class="input-bar">
    <div class="input-wrapper">
        <input type="text" id="userInput" placeholder="اطرح سؤالك على نبراس">
        <button class="send-btn" id="sendBtn">➤</button>
    </div>
</div>

<script>
    const chatBox = document.getElementById('chatBox');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const plusBtn = document.getElementById('plusBtn');
    const suggestions = document.getElementById('suggestions');
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
        // إخفاء الاقتراحات بعد أول رسالة
        suggestions.style.display = 'none';
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

    function resetSuggestions() {
        suggestions.style.display = 'flex';
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
            appendMessage('bot', data.reply || '⚠️ عذراً');
        } catch (e) {
            hideTyping();
            appendMessage('bot', '⚠️ حدث خطأ');
        }
        sendBtn.disabled = false;
        userInput.focus();
    }

    // ─── الأحداث ───
    sendBtn.addEventListener('click', () => sendMessage(userInput.value));
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendMessage(userInput.value);
    });

    // ─── الاقتراحات ───
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('click', () => {
            const prompt = card.dataset.prompt;
            if (prompt) {
                userInput.value = prompt;
                sendMessage(prompt);
            }
        });
    });

    // ─── زر Plus ───
    plusBtn.addEventListener('click', () => {
        alert('🚀 سيتم فتح صفحة الترقية قريباً');
    });

    // ─── محادثة جديدة ───
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            chatBox.innerHTML = '';
            sessionId = 'user_' + Date.now();
            appendMessage('bot', 'مرحباً! أنا نبراس، كيف أساعدك؟');
            resetSuggestions();
        }
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
        return jsonify({"reply": "اكتب رسالة"}), 400

    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    chat_sessions[session_id].append({"role": "user", "content": user_msg})

    # ─── البحث ───
    keywords = ["بحث", "أخبار", "حدث", "اليوم", "سعر", "طقس", "مباراة", "نتيجة"]
    search_context = search_web(user_msg) if any(kw in user_msg for kw in keywords) else ""

    # ─── التعليمات ───
    system_prompt = f"""أنت نبراس، صديق سعودي.
{NBRAS_KNOWLEDGE}
التاريخ: {get_date()}.
{f"معلومات من البحث: {search_context}" if search_context else ""}
"""

    try:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(chat_sessions[session_id])

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=700,
            temperature=0.7
        )

        reply = response.choices[0].message.content
        chat_sessions[session_id].append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"⚠️ خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
