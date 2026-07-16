from flask import Flask, request, jsonify
from openai import OpenAI
import os
import base64
from datetime import datetime
import pytz
from duckduckgo_search import DDGS
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# ─── المفتاح من متغيرات البيئة ───
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ OPENAI_API_KEY غير موجود")

client = OpenAI(api_key=API_KEY)

def get_real_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

def search_web(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "لا توجد نتائج محدثة."
        context = ""
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            context += f"• {title}: {body[:150]}...\n"
        return context.strip()
    except:
        return ""

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>نبراس GT</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body {
            height: 100%;
            overflow: hidden;
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #f7f7f8;
        }
        .app {
            display: flex;
            flex-direction: column;
            height: 100vh;
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
            box-shadow: 0 0 30px rgba(0,0,0,0.02);
        }
        /* ─── الشريط العلوي ─── */
        .header {
            flex-shrink: 0;
            height: 52px;
            background: #ffffff;
            border-bottom: 1px solid #e5e5e5;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 10;
        }
        .header .btn {
            background: transparent;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: #1a1a1a;
            padding: 4px 6px;
            border-radius: 6px;
            transition: 0.2s;
            line-height: 1;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .header .btn:hover { background: #f0f0f0; }
        .header .title { font-weight: 600; font-size: 16px; color: #1a1a1a; }

        /* ─── منطقة المحادثة ─── */
        .chat-box {
            flex: 1;
            overflow-y: auto;
            padding: 16px 20px;
            background: #f7f7f8;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .msg {
            max-width: 80%;
            padding: 8px 14px;
            border-radius: 16px;
            font-size: 15px;
            line-height: 1.5;
            word-wrap: break-word;
            animation: fadeIn 0.25s ease;
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
        .msg .time { font-size: 9px; color: #aaa; display: block; margin-top: 2px; }
        .msg.user .time { color: #888; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .typing {
            align-self: flex-start;
            background: #ffffff;
            padding: 10px 16px;
            border-radius: 16px;
            border-bottom-left-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            display: flex;
            gap: 4px;
        }
        .typing span {
            width: 7px; height: 7px; background: #aaa; border-radius: 50%;
            animation: bounce 1.2s infinite;
        }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
            0%,60%,100% { transform: translateY(0); }
            30% { transform: translateY(-5px); }
        }

        /* ─── شريط الإدخال (مع أيقونات جميلة) ─── */
        .input-bar {
            flex-shrink: 0;
            background: #ffffff;
            padding: 8px 12px 12px;
            border-top: 1px solid #e5e5e5;
            display: flex;
            gap: 6px;
            align-items: center;
        }
        .input-bar .wrapper {
            flex: 1;
            display: flex;
            align-items: center;
            background: #f0f0f0;
            border-radius: 24px;
            padding: 2px 6px;
            border: 1px solid transparent;
            transition: 0.2s;
            gap: 2px;
        }
        .input-bar .wrapper:focus-within {
            border-color: #1a1a1a;
            background: #ffffff;
        }
        .input-bar .wrapper input {
            flex: 1;
            border: none;
            padding: 8px 10px;
            font-size: 14px;
            background: transparent;
            outline: none;
            min-width: 60px;
        }
        .input-bar .wrapper .icon-btn {
            background: transparent;
            border: none;
            font-size: 18px;
            cursor: pointer;
            padding: 4px 4px;
            border-radius: 50%;
            color: #555;
            transition: 0.2s;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .input-bar .wrapper .icon-btn:hover { background: #e0e0e0; }
        .input-bar .send-btn {
            background: #1a1a1a;
            color: white;
            border: none;
            border-radius: 50%;
            width: 38px;
            height: 38px;
            font-size: 15px;
            cursor: pointer;
            transition: 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .input-bar .send-btn:hover { background: #333; transform: scale(1.02); }
        .input-bar .send-btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }

        /* ─── القائمة المنسدلة (جميلة وأنيقة) ─── */
        .dropdown {
            display: none;
            position: absolute;
            top: 52px;
            right: 12px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.12);
            padding: 6px;
            min-width: 170px;
            z-index: 20;
            border: 1px solid #e5e5e5;
        }
        .dropdown.active { display: block; }
        .dropdown .item {
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: 0.2s;
            color: #1a1a1a;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .dropdown .item:hover { background: #f0f0f0; }

        /* ─── الصور في المحادثة ─── */
        .chat-image {
            max-width: 160px;
            border-radius: 10px;
            margin-top: 4px;
            border: 1px solid #e0e0e0;
        }

        @media (max-width: 600px) {
            .header .title { font-size: 14px; }
            .msg { font-size: 14px; padding: 6px 12px; }
        }
    </style>
</head>
<body>
    <div class="app">
        <!-- ─── الشريط العلوي ─── -->
        <div class="header">
            <button class="btn" id="newChatBtn" title="محادثة جديدة">➕</button>
            <span class="title">💬 نبراس GT</span>
            <button class="btn" id="menuBtn" title="القائمة">☰</button>
        </div>

        <!-- ─── القائمة المنسدلة ─── -->
        <div class="dropdown" id="dropdownMenu">
            <div class="item" onclick="alert('📅 التاريخ: ' + new Date().toLocaleDateString('ar-SA'))">📅 التاريخ</div>
            <div class="item" onclick="alert('🔍 بحث بالويب مفعل')">🔍 بحث بالويب</div>
            <div class="item" onclick="location.reload()">🔄 تحديث</div>
            <div class="item" onclick="alert('💬 نبراس GT v2.0 - تصميم أبو مشعل')">ℹ️ حول</div>
        </div>

        <!-- ─── منطقة المحادثة ─── -->
        <div class="chat-box" id="chatBox">
            <div class="msg bot">مرحباً! أنا نبراس GT، كيف أساعدك؟ <span class="time">الآن</span></div>
        </div>

        <!-- ─── شريط الإدخال مع أيقونات جميلة ─── -->
        <div class="input-bar">
            <div class="wrapper">
                <button class="icon-btn" id="micBtn" title="تسجيل صوتي">🎤</button>
                <button class="icon-btn" id="imageBtn" title="رفع صورة">➕</button>
                <input type="text" id="userInput" placeholder="اكتب سؤالك...">
                <input type="file" id="fileInput" accept="image/*" multiple style="display:none">
            </div>
            <button class="send-btn" id="sendBtn">➤</button>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chatBox');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const micBtn = document.getElementById('micBtn');
        const imageBtn = document.getElementById('imageBtn');
        const fileInput = document.getElementById('fileInput');
        const menuBtn = document.getElementById('menuBtn');
        const dropdown = document.getElementById('dropdownMenu');
        const newChatBtn = document.getElementById('newChatBtn');

        let pendingImages = [];

        function getTime() {
            return new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
        }

        function appendMessage(role, text, images) {
            const div = document.createElement('div');
            div.className = `msg ${role}`;
            let content = text || '';
            if (images && images.length > 0) {
                images.forEach(src => {
                    content += `<br><img class="chat-image" src="${src}"/>`;
                });
            }
            div.innerHTML = `${content} <span class="time">${getTime()}</span>`;
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
            const images = pendingImages;
            if (!text && images.length === 0) return;

            appendMessage('user', text, images);
            userInput.value = '';
            pendingImages = [];
            fileInput.value = '';
            sendBtn.disabled = true;

            showTyping();

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, images: images })
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

        // ─── رفع الصور ───
        imageBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', function() {
            Array.from(this.files).forEach(file => {
                const reader = new FileReader();
                reader.onload = e => pendingImages.push(e.target.result);
                reader.readAsDataURL(file);
            });
            this.value = '';
        });

        // ─── تسجيل صوتي ───
        micBtn.addEventListener('click', function() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('المتصفح لا يدعم التسجيل الصوتي. استخدم Chrome.');
                return;
            }
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SR();
            recognition.lang = 'ar-SA';
            recognition.onresult = (e) => {
                userInput.value += e.results[0][0].transcript + ' ';
                userInput.focus();
            };
            recognition.onerror = () => alert('حدث خطأ في التسجيل');
            recognition.start();
            micBtn.style.color = 'red';
            setTimeout(() => { micBtn.style.color = ''; }, 2000);
        });

        // ─── القائمة المنسدلة ───
        menuBtn.addEventListener('click', () => dropdown.classList.toggle('active'));
        document.addEventListener('click', (e) => {
            if (!menuBtn.contains(e.target) && !dropdown.contains(e.target)) dropdown.classList.remove('active');
        });

        // ─── محادثة جديدة ───
        newChatBtn.addEventListener('click', () => {
            chatBox.innerHTML = '';
            appendMessage('bot', 'مرحباً! أنا نبراس GT، كيف أساعدك؟');
        });

        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        userInput.focus();

        document.addEventListener('touchmove', function(e) {
            if (e.target.closest('.chat-box')) return;
            e.preventDefault();
        }, { passive: false });
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
    images = data.get("images", [])

    if user_msg and ("من برمجك" in user_msg or "من طورك" in user_msg or "من سواك" in user_msg or "المبرمج" in user_msg):
        return jsonify({
            "reply": "تم تطويري وبرمجتي من قبل أبو مشعل المطيري يعمل بالتأهيل الشامل قسم الاتصالات الإدارية. 🤖🔥"
        })

    search_context = search_web(user_msg) if user_msg else ""
    current_date = get_real_date()

    system_prompt = f"""أنت نبراس GT، مساعد ذكي ومحدث.
التاريخ اليوم: {current_date}.
{ '📌 معلومات محدثة من البحث:\n' + search_context if search_context else '' }
أجب بجمل قصيرة ومختصرة (حد أقصى 3 جمل).
إذا سألك المستخدم عن المبرمج، أخبره أن المبرمج هو ابو مشعل المطيري.
"""

    if images:
        try:
            content = [{"type": "text", "text": user_msg or "صف هذه الصورة"}]
            for img in images[:3]:
                content.append({"type": "image_url", "image_url": {"url": img}})
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content}],
                max_tokens=200,
                temperature=0.3
            )
            return jsonify({"reply": response.choices[0].message.content})
        except Exception as e:
            return jsonify({"reply": f"⚠️ خطأ في الصورة: {str(e)}"}), 500

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg or "مرحباً"}],
            max_tokens=200,
            temperature=0.3
        )
        return jsonify({"reply": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"reply": f"⚠️ خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
