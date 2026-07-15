from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ OPENAI_API_KEY غير موجود")

client = OpenAI(api_key=API_KEY)

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نبراس</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #f7f7f8;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* ─── الشريط العلوي ─── */
        header {
            background: #ffffff;
            padding: 16px 24px;
            border-bottom: 1px solid #e5e5e5;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        header .avatar {
            width: 36px;
            height: 36px;
            background: #1a1a1a;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        header h1 {
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
        }

        /* ─── منطقة المحادثة ─── */
        .chat-box {
            flex: 1;
            overflow-y: auto;
            padding: 20px 24px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            background: #f7f7f8;
        }

        /* ─── فقاعات الرسائل ─── */
        .msg {
            max-width: 75%;
            padding: 10px 16px;
            border-radius: 18px;
            font-size: 15px;
            line-height: 1.6;
            word-wrap: break-word;
            animation: fadeIn 0.3s ease;
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
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .msg .time {
            font-size: 10px;
            color: #aaa;
            display: block;
            margin-top: 4px;
        }
        .msg.bot .time { color: #aaa; }
        .msg.user .time { color: #888; }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ─── مؤشر الكتابة ─── */
        .typing {
            align-self: flex-start;
            background: #ffffff;
            padding: 12px 18px;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            display: flex;
            gap: 4px;
        }
        .typing span {
            width: 8px;
            height: 8px;
            background: #aaa;
            border-radius: 50%;
            animation: bounce 1.2s infinite;
        }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-6px); }
        }

        /* ─── منطقة الإدخال ─── */
        .input-area {
            background: #ffffff;
            padding: 12px 24px 20px;
            border-top: 1px solid #e5e5e5;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .input-area input {
            flex: 1;
            padding: 12px 18px;
            border: 1px solid #e5e5e5;
            border-radius: 30px;
            font-size: 15px;
            outline: none;
            background: #ffffff;
            transition: 0.2s;
        }
        .input-area input:focus {
            border-color: #1a1a1a;
            box-shadow: 0 0 0 3px rgba(0,0,0,0.05);
        }
        .input-area button {
            background: #1a1a1a;
            color: white;
            border: none;
            border-radius: 30px;
            padding: 12px 24px;
            font-size: 15px;
            font-weight: 500;
            cursor: pointer;
            transition: 0.2s;
        }
        .input-area button:hover {
            background: #333;
            transform: scale(1.02);
        }
        .input-area button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
    </style>
</head>
<body>

<header>
    <div class="avatar">🤖</div>
    <h1>نبراس</h1>
</header>

<div class="chat-box" id="chatBox">
    <div class="msg bot">مرحباً! أنا نبراس، كيف أساعدك؟ <span class="time">الآن</span></div>
</div>

<div class="input-area">
    <input type="text" id="userInput" placeholder="اكتب سؤالك...">
    <button id="sendBtn">إرسال</button>
</div>

<script>
    const chatBox = document.getElementById('chatBox');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');

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
        const msg = userInput.value.trim();
        if (!msg) return;

        userInput.value = '';
        sendBtn.disabled = true;

        // عرض رسالة المستخدم
        appendMessage('user', msg);

        // مؤشر الكتابة
        showTyping();

        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            hideTyping();
            appendMessage('bot', data.reply || '⚠️ لم أستطع الرد');
        } catch (e) {
            hideTyping();
            appendMessage('bot', '⚠️ حدث خطأ في الاتصال');
        }

        sendBtn.disabled = false;
        userInput.focus();
    }

    // ─── الأحداث ───
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    userInput.focus();
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
    if not user_msg:
        return jsonify({"reply": "الرجاء كتابة رسالة"})
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "أنت نبراس، مساعد ذكي مختصر. أجب بجمل قصيرة."},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=200,
            temperature=0.3
        )
        return jsonify({"reply": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"reply": f"⚠️ خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
