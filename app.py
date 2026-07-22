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

# ─── ملف المعرفة (مضمن داخل الكود) ───
NBRAS_KNOWLEDGE = """
# شخصية نبراس

## اللهجة
اللهجة السعودية العامية (البدوية الخفيفة).
كلمات دارجة: وش، شلون، هاه، عاد، يبه، زين، تمام، وش وضعك، وش عندك، تبي، ودّك.

## طريقة الكلام
- جمل قصيرة ومباشرة.
- سوالف بسيطة وواضحة.
- بدون فصحى أو تعقيد.
- نبرة ودودة وخفيفة.

## الروح العامة
- صديق قريب وطبيعي.
- يحب المزح الخفيف والسوالف.
- إذا المستخدم جاد، يكون جاداً.
- إذا المستخدم يطقطق، يطقطق معه.

## القواعد
- لا تتفلسف.
- لا تطيل في الردود (حد أقصى 4 جمل).
- إذا سأل عن المبرمج: قل "أنا من صنع أبو مشعل المطيري".
- إذا سأل عن شيء يحتاج بحث، ابحث في الويب واختصر الإجابة.
"""

# ─── البحث في الويب (DuckDuckGo) ───
def search_web(query, max_results=3):
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        results = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        
        if "RelatedTopics" in data:
            for topic in data["RelatedTopics"][:max_results]:
                if "Text" in topic:
                    results.append(topic["Text"])
        
        return "\n".join(results) if results else ""
    except Exception as e:
        return ""

# ─── التاريخ ───
def get_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

# ─── ذاكرة المحادثة ───
chat_sessions = {}

# ─── واجهة HTML (مضمنة) ───
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نبراس</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #f7f7f8;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #ffffff;
            padding: 12px 24px;
            border-bottom: 1px solid #e5e5e5;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
        }
        .header .brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header .brand i {
            font-size: 24px;
            color: #1a1a1a;
        }
        .header .brand h1 {
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
        }
        .header .actions button {
            background: transparent;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: #555;
            padding: 4px 8px;
            border-radius: 8px;
            transition: 0.2s;
        }
        .header .actions button:hover {
            background: #f0f0f0;
        }
        .chat-box {
            flex: 1;
            overflow-y: auto;
            padding: 20px 24px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: #f7f7f8;
        }
        .msg {
            max-width: 75%;
            padding: 10px 16px;
            border-radius: 18px;
            font-size: 15px;
            line-height: 1.6;
            animation: fadeIn 0.25s ease;
            word-wrap: break-word;
        }
        .msg.user {
            background: #1a1a1a;
            color: #ffffff;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .msg.bot {
            background: #ffffff;
            color: #1a1a1a;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        .msg .time {
            font-size: 10px;
            color: #999;
            display: block;
            margin-top: 4px;
        }
        .msg.user .time { color: #aaa; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .typing {
            align-self: flex-start;
            background: #ffffff;
            padding: 12px 18px;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            display: flex;
            gap: 5px;
        }
        .typing span {
            width: 8px;
            height: 8px;
            background: #b0b8c8;
            border-radius: 50%;
            animation: bounce 1.2s infinite;
        }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-6px); }
        }
        .input-bar {
            background: #ffffff;
            padding: 12px 20px 20px;
            border-top: 1px solid #e5e5e5;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-shrink: 0;
        }
        .input-bar .wrap {
            flex: 1;
            display: flex;
            align-items: center;
            background: #f0f0f0;
            border-radius: 24px;
            padding: 2px 14px;
            border: 1px solid transparent;
            transition: 0.2s;
        }
        .input-bar .wrap:focus-within {
            border-color: #1a1a1a;
            background: #ffffff;
        }
        .input-bar .wrap input {
            flex: 1;
            border: none;
            background: transparent;
            padding: 10px 8px;
            font-size: 15px;
            outline: none;
            color: #1a1a1a;
        }
        .input-bar .wrap input::placeholder {
            color: #999;
        }
        .input-bar .send-btn {
            background: #1a1a1a;
            color: white;
            border: none;
            border-radius: 50%;
            width: 42px;
            height: 42px;
            font-size: 18px;
            cursor: pointer;
            transition: 0.15s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .input-bar .send-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .input-bar .send-btn:hover:not(:disabled) {
            background: #333;
            transform: scale(1.02);
        }
        @media (max-width: 600px) {
            .msg { font-size: 14px; max-width: 85%; }
            .input-bar { padding: 10px 12px 16px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">
            <i class="fa-regular fa-comment-dots"></i>
            <h1>نبراس</h1>
        </div>
        <div class="actions">
            <button id="newChatBtn" title="محادثة جديدة"><i class="fa-regular fa-plus"></i></button>
        </div>
    </div>
    <div class="chat-box" id="chatBox">
        <div class="msg bot">مرحباً! أنا نبراس، كيف أساعدك؟ <span class="time">الآن</span></div>
    </div>
    <div class="input-bar">
        <div class="wrap">
            <input type="text" id="userInput" placeholder="اكتب سؤالك...">
        </div>
        <button class="send-btn" id="sendBtn"><i class="fa-regular fa-paper-plane"></i></button>
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
        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;
            appendMessage('user', text);
            userInput.value = '';
            sendBtn.disabled = true;
            showTyping();
            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, session_id: sessionId })
                });
                const data = await res.json();
                hideTyping();
                appendMessage('bot', data.reply || '⚠️ عذراً');
            } catch (e) {
                hideTyping();
                appendMessage('bot', '⚠️ حدث خطأ في الاتصال');
            }
            sendBtn.disabled = false;
            userInput.focus();
        }
        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        newChatBtn.addEventListener('click', () => {
            chatBox.innerHTML = '';
            sessionId = 'user_' + Date.now();
            appendMessage('bot', 'مرحباً! أنا نبراس، كيف أساعدك؟');
        });
        userInput.focus();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

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
    search_keywords = ["بحث", "أخبار", "حدث", "اليوم", "سعر", "طقس", "مباراة", "نتيجة"]
    needs_search = any(kw in user_msg for kw in search_keywords)

    search_context = ""
    if needs_search:
        search_context = search_web(user_msg)

    # ─── نظام التعليمات ───
    system_prompt = f"""أنت نبراس، صديق سعودي طبيعي، تتحدث باللهجة السعودية العامية.

🎯 شخصيتك:
{NBRAS_KNOWLEDGE}

📌 تعليمات إضافية:
- تحدث كإنسان طبيعي، بجمل قصيرة ومباشرة.
- لا تتفلسف، ولا تطيل (حد أقصى 4 جمل).
- استخدم اللهجة السعودية العامية فقط.
- إذا سألك عن المبرمج: قل "أنا من صنع أبو مشعل المطيري".
- التاريخ اليوم: {get_date()}.
{f"📌 معلومات من البحث:\n{search_context}" if search_context else ""}
- إذا كان السؤال يحتاج بحث، استخدم المعلومات أعلاه.
- إذا لم تكن متأكداً، قل "ما عندي علم والله".
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
