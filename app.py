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

# ========== تعليمات النظام ==========
SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد ودود ومتعاون لأهل السعودية والخليج.
تحدث باللهجة السعودية العامية الواضحة والطبيعية تماماً كإنسان حقيقي.
تفاعل مع المستخدم بكل رحابة صدر، جاوب على أسئلته، واطلب منه التفاصيل إن احتجت، واقترح عليه أمور مفيدة، واطرح عليه أسئلة لتبادل الحديث والفائدة.

معلوماتك الخاصة (من ملف المعرفة):
{knowledge_content}

ملاحظة مهمة: أنت تمتلك معرفة عامة محدثة حتى أكتوبر 2023، وتعرف الأخبار العامة والأحداث التاريخية. إذا سألك المستخدم عن شيء لا تعرفه، أخبره بصراحة أنك لا تملك المعلومة واقترح عليه مصدراً آخر.
"""

# ========== الواجهة ==========
HTML_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نبراس</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family: Arial, sans-serif; }
        body { background:#f5f7fa; display:flex; justify-content:center; align-items:center; height:100vh; }
        .chat-container { width:100%; max-width:450px; height:90vh; background:white; border-radius:30px; box-shadow:0 10px 30px rgba(0,0,0,0.05); display:flex; flex-direction:column; overflow:hidden; }
        .header { padding:20px; border-bottom:1px solid #eee; display:flex; justify-content:space-between; }
        .header .title { font-weight:bold; font-size:18px; }
        #messages { flex:1; padding:20px; overflow-y:auto; display:flex; flex-direction:column; gap:10px; }
        .msg { padding:10px 16px; border-radius:18px; max-width:80%; font-size:15px; line-height:1.6; }
        .msg.user { background:#eef2f7; align-self:flex-end; border-bottom-left-radius:4px; }
        .msg.bot { background:#f0f0f0; align-self:flex-start; border-bottom-right-radius:4px; }
        .input-area { display:flex; gap:10px; padding:15px; border-top:1px solid #eee; background:white; }
        .input-area input { flex:1; padding:12px 16px; border:1px solid #ddd; border-radius:30px; outline:none; font-size:15px; }
        .input-area button { background:#2c3e50; color:white; border:none; padding:12px 20px; border-radius:30px; font-size:15px; cursor:pointer; }
        .input-area button:hover { background:#1a252f; }
        .loading { color:#888; font-size:13px; padding:5px 16px; }
    </style>
</head>
<body>
<div class="chat-container">
    <div class="header">
        <span class="title">نبراس</span>
        <span>⚙️</span>
    </div>
    <div id="messages"></div>
    <div class="input-area">
        <input type="text" id="userInput" placeholder="اكتب رسالتك...">
        <button onclick="sendMessage()">إرسال</button>
    </div>
</div>
<script>
    const messagesDiv = document.getElementById('messages');
    const userInput = document.getElementById('userInput');

    function addMessage(text, sender) {
        const msg = document.createElement('div');
        msg.className = 'msg ' + sender;
        msg.textContent = text;
        messagesDiv.appendChild(msg);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;
        addMessage(text, 'user');
        userInput.value = '';
        userInput.disabled = true;

        const loading = document.createElement('div');
        loading.className = 'loading';
        loading.textContent = '...';
        messagesDiv.appendChild(loading);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({m: text})
            });
            const data = await res.json();
            loading.remove();
            if (res.ok) {
                addMessage(data.reply, 'bot');
            } else {
                addMessage('خطأ: ' + (data.error || 'مشكلة في السيرفر'), 'bot');
            }
        } catch (e) {
            loading.remove();
            addMessage('تعذر الاتصال بالسيرفر.', 'bot');
        }
        userInput.disabled = false;
        userInput.focus();
    }

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get("m", "").strip()
        if not user_message:
            return jsonify({"reply": "اكتب شيء أساعدك فيه"})

        # استدعاء ChatGPT مباشرة (بدون بحث خارجي)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # أو gpt-4 إذا كان حسابك يدعم
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.8,
            max_tokens=600
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
