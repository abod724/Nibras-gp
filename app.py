from flask import Flask, request, jsonify, render_template_string
import openai
import os

app = Flask(__name__)

# ========== مفتاح API ==========
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("المفتاح غير موجود")
client = openai.OpenAI(api_key=API_KEY)

# ========== ملف المعرفة ==========
KNOWLEDGE_FILE = "Knowledge.md"
knowledge_content = ""
if os.path.exists(KNOWLEDGE_FILE):
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge_content = f.read()
    except:
        pass

# ========== تعليمات النظام (معدلة للهجة السعودية ومنع الروابط) ==========
SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد ودود ومتعاون لأهل السعودية والخليج.

**اللهجة:**  
تحدث باللهجة السعودية العامية البيضاء الطبيعية تماماً، مثل:  
"كيف الحال؟"، "وش أخبارك؟"، "تمام يا عزيزي"، "طيب بس كذا"، "إيوه"، "لا حول ولا قوة إلا بالله".  
لا تستخدم الفصحى أبداً، ولا تستخدم كلمات رسمية أو إخبارية جافة. كن عفويًا وكأنك تتحدث مع صديق في مجلس.

**الأسلوب:**  
- جاوب بإجابات متوسطه ومختصره ، واشرح الأمور بطريقة مفهومة.  
- إذا كان الرد يحتوي على معلومات من البحث، ادمجها بطريقة طبيعية في كلامك، ولا تذكر المصادر أو الروابط أبداً.  
- لا تضع أي روابط أو أسماء مواقع في ردك.  
- لا تذكر "وفقاً لـ" أو "حسب موقع كذا". فقط قدم المعلومة وكأنها من معرفتك.

**معلوماتك الخاصة:**  
{knowledge_content}

**ملاحظة:** عندما يسألك المستخدم عن أخبار حديثة، استخدم أداة البحث، ولكن أعد صياغة المعلومة بلهجتك الخاصة دون ذكر المصادر.
"""

# ========== الواجهة (بدون تغيير) ==========
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes" />
    <title>نبراس</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
        body { background: #ffffff; height: 100dvh; display: flex; justify-content: center; align-items: center; margin: 0; padding: 0; }
        .app { width: 100%; max-width: 450px; height: 100dvh; background: #ffffff; display: flex; flex-direction: column; position: relative; }

        .header { display: flex; justify-content: flex-end; align-items: center; padding: 14px 18px; border-bottom: 1px solid #eaeef2; flex-shrink: 0; background: #ffffff; }
        .header .menu-btn { background: none; border: none; font-size: 22px; color: #5a6b7c; cursor: pointer; padding: 4px 8px; }

        .dropdown { position: absolute; top: 64px; left: 14px; right: 14px; background: white; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); display: none; flex-direction: column; z-index: 100; border: 1px solid #eaedf2; }
        .dropdown.show { display: flex; }
        .dropdown .item { display: flex; align-items: center; gap: 12px; padding: 14px 18px; font-size: 15px; color: #1a2b3c; background: none; border: none; width: 100%; text-align: right; cursor: pointer; border-bottom: 1px solid #f0f2f5; }
        .dropdown .item:last-child { border-bottom: none; }
        .dropdown .item i { width: 22px; font-size: 18px; color: #5a6b7c; }
        .dropdown .item:hover { background: #f5f7fa; }

        #chat { flex: 1; overflow-y: auto; padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; background: #ffffff; }
        .msg { max-width: 80%; padding: 10px 16px; border-radius: 20px; font-size: 15px; line-height: 1.6; word-wrap: break-word; }
        .msg.user { align-self: flex-end; background: #eef2f7; color: #1a2b3c; border-bottom-left-radius: 6px; }
        .msg.bot { align-self: flex-start; background: #f5f7fa; color: #1a2b3c; border-bottom-right-radius: 6px; }
        .msg .time { font-size: 9px; opacity: 0.35; display: block; margin-top: 4px; }
        .msg.error { background: #fde8e8; color: #a33; align-self: center; max-width: 90%; }

        .input-area { display: flex; align-items: center; gap: 6px; padding: 6px 12px; margin: 8px 14px 16px 14px; background: #f5f7fa; border-radius: 40px; border: 1px solid #dce1e8; flex-shrink: 0; }
        .input-area input { flex: 1; border: none; background: transparent; padding: 12px 4px; font-size: 15px; outline: none; color: #1a2b3c; direction: rtl; }
        .input-area input::placeholder { color: #9aabbc; }
        .input-area .btn-icon { background: none; border: none; color: #6a7b8c; font-size: 20px; cursor: pointer; padding: 4px; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; }
        .input-area .btn-icon:hover { background: #e8ecf0; }
        .input-area .mic-btn { color: #4a6a8a; }
        .input-area .mic-btn.listening { color: #c33; background: #fde8e8; }
        .input-area .send { background: #4a6a8a; color: white; border: none; width: 44px; height: 44px; border-radius: 50%; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 2px 8px rgba(74,106,138,0.2); }
        .input-area .send:hover { background: #3a5a7a; }

        @media (max-width: 420px) {
            .header { padding: 12px 14px; }
            .dropdown { top: 58px; left: 10px; right: 10px; }
            .dropdown .item { padding: 12px 14px; font-size: 14px; }
            #chat { padding: 12px 14px; }
            .msg { font-size: 14px; padding: 8px 12px; }
            .input-area { margin: 6px 10px 12px 10px; padding: 4px 10px; }
            .input-area input { font-size: 14px; padding: 10px 2px; }
            .input-area .send { width: 40px; height: 40px; font-size: 16px; }
            .input-area .btn-icon { width: 34px; height: 34px; font-size: 18px; }
        }
    </style>
</head>
<body>
<div class="app">

    <div class="header">
        <button class="menu-btn" id="menuToggle"><i class="fas fa-ellipsis-v"></i></button>
    </div>

    <div class="dropdown" id="dropdown">
        <button class="item" data-action="new"><i class="fas fa-plus-circle"></i> محادثة جديدة</button>
        <button class="item" data-action="library"><i class="fas fa-layer-group"></i> المكتبة</button>
        <button class="item" data-action="history"><i class="fas fa-history"></i> المحادثات السابقة</button>
    </div>

    <div id="chat"></div>

    <div class="input-area">
        <button class="btn-icon mic-btn" id="micBtn" title="تسجيل صوت"><i class="fas fa-microphone"></i></button>
        <button class="btn-icon" id="fileBtn" title="رفع صورة"><i class="fas fa-image"></i></button>
        <input type="file" id="fileInput" accept="image/*" style="display: none;" />
        <input type="text" id="userInput" placeholder="اكتب رسالة..." autofocus />
        <button class="send" id="sendBtn"><i class="fas fa-arrow-left"></i></button>
    </div>
</div>

<script>
    (function() {
        const chatBox = document.getElementById('chat');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const micBtn = document.getElementById('micBtn');
        const fileBtn = document.getElementById('fileBtn');
        const fileInput = document.getElementById('fileInput');
        const menuToggle = document.getElementById('menuToggle');
        const dropdown = document.getElementById('dropdown');

        function addMessage(text, sender = 'bot', isSystem = false) {
            const el = document.createElement('div');
            el.className = `msg ${sender}`;
            if (sender === 'error') el.classList.add('error');
            const now = new Date();
            const time = now.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
            el.innerHTML = `<span class="typing-text"></span><span class="time"> ${time}</span>`;
            chatBox.appendChild(el);
            chatBox.scrollTop = chatBox.scrollHeight;

            const textSpan = el.querySelector('.typing-text');
            let index = 0;
            function typeChar() {
                if (index < text.length) {
                    textSpan.textContent += text.charAt(index);
                    index++;
                    chatBox.scrollTop = chatBox.scrollHeight;
                    setTimeout(typeChar, 15);
                }
            }
            typeChar();

            if (!isSystem && sender !== 'error') {
                saveHistory(sender, text);
            }
        }

        function saveHistory(sender, text) {
            let hist = JSON.parse(localStorage.getItem('niras_history') || '[]');
            hist.push({ sender, text, time: new Date().toISOString() });
            if (hist.length > 100) hist = hist.slice(-100);
            localStorage.setItem('niras_history', JSON.stringify(hist));
        }
        function getHistory() {
            return JSON.parse(localStorage.getItem('niras_history') || '[]');
        }

        function getImages() {
            return JSON.parse(localStorage.getItem('niras_images') || '[]');
        }
        function saveImages(imgs) {
            localStorage.setItem('niras_images', JSON.stringify(imgs));
        }
        function deleteImage(index) {
            let imgs = getImages();
            if (index >= 0 && index < imgs.length) {
                imgs.splice(index, 1);
                saveImages(imgs);
                addMessage('تم حذف الصورة.', 'bot', true);
                showLibrary();
            }
        }

        function showLibrary() {
            const imgs = getImages();
            if (imgs.length === 0) {
                addMessage('لا توجد صور.', 'bot', true);
                return;
            }
            let html = '<div class="gallery">';
            imgs.forEach((src, idx) => {
                html += `<div class="img-wrap">
                    <img src="${src}" />
                    <button class="del" data-idx="${idx}">×</button>
                </div>`;
            });
            html += '</div>';
            const container = document.createElement('div');
            container.className = 'msg bot';
            container.innerHTML = html + `<span class="time">${new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}</span>`;
            chatBox.appendChild(container);
            chatBox.scrollTop = chatBox.scrollHeight;
            container.querySelectorAll('.del').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const idx = parseInt(this.dataset.idx);
                    deleteImage(idx);
                });
            });
        }

        function showHistory() {
            const hist = getHistory();
            if (hist.length === 0) {
                addMessage('لا توجد محادثات.', 'bot', true);
                return;
            }
            let msg = '';
            hist.slice(-12).forEach((entry) => {
                const t = new Date(entry.time).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
                const txt = entry.text.length > 40 ? entry.text.substring(0, 40) + '...' : entry.text;
                msg += `- ${txt} (${t})\n`;
            });
            addMessage(msg, 'bot', true);
            hist.slice(-5).forEach(entry => {
                const btn = document.createElement('button');
                btn.textContent = entry.text.length > 22 ? entry.text.substring(0, 22) + '…' : entry.text;
                btn.style.cssText = 'background:#f0f2f5;border:none;border-radius:30px;padding:4px 12px;margin:4px;cursor:pointer;font-size:13px;color:#1a2b3c;';
                btn.onclick = function() { userInput.value = entry.text; userInput.focus(); };
                chatBox.appendChild(btn);
            });
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function newChat() {
            chatBox.innerHTML = '';
        }

        function handleAction(action) {
            dropdown.classList.remove('show');
            switch(action) {
                case 'new': newChat(); break;
                case 'library': showLibrary(); break;
                case 'history': showHistory(); break;
                default: break;
            }
        }

        document.querySelectorAll('.dropdown .item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                handleAction(item.dataset.action);
            });
        });

        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });
        document.addEventListener('click', () => {
            dropdown.classList.remove('show');
        });

        let recognition = null;
        micBtn.addEventListener('click', function() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                addMessage('المتصفح لا يدعم التعرف على الصوت.', 'bot', true);
                return;
            }
            if (this.classList.contains('listening')) {
                this.classList.remove('listening');
                if (recognition) recognition.stop();
                return;
            }
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SR();
            recognition.lang = 'ar-SA';
            recognition.continuous = false;
            recognition.interimResults = false;

            this.classList.add('listening');
            addMessage('جاري الاستماع...', 'bot', true);

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                userInput.value = transcript;
                micBtn.classList.remove('listening');
                setTimeout(() => {
                    sendMessage();
                }, 300);
            };
            recognition.onerror = (event) => {
                micBtn.classList.remove('listening');
                if (event.error !== 'aborted') {
                    addMessage('لم يتعرف على الصوت، حاول مرة أخرى.', 'bot', true);
                }
            };
            recognition.onend = () => {
                micBtn.classList.remove('listening');
            };
            recognition.start();
        });

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;
            addMessage(text, 'user');
            userInput.value = '';
            userInput.focus();
            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ m: text })
                });
                const data = await res.json();
                if (res.ok) {
                    addMessage(data.reply, 'bot');
                } else {
                    addMessage('خطأ: ' + (data.error || 'مشكلة في السيرفر'), 'error');
                }
            } catch (e) {
                addMessage('تعذر الاتصال بالسيرفر.', 'error');
            }
        }

        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

        fileBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                const reader = new FileReader();
                reader.onload = function(ev) {
                    let imgs = getImages();
                    imgs.push(ev.target.result);
                    saveImages(imgs);
                    addMessage(`تم رفع ${file.name}`, 'user');
                    addMessage('حُفظت الصورة في مكتبتك.', 'bot', true);
                    fileInput.value = '';
                };
                reader.readAsDataURL(file);
            }
        });
    })();
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ========== نقطة الدردشة مع البحث ==========
@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get("m", "").strip()
        if not user_message:
            return jsonify({"reply": "اكتب شيء أساعدك فيه"})

        response = client.responses.create(
            model="gpt-4o-mini",
            instructions=SYSTEM_PROMPT,
            input=user_message,
            tools=[{"type": "web_search"}],
            temperature=0.9,
            max_output_tokens=4000
        )

        reply = response.output_text.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
