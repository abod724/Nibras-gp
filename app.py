from flask import Flask, request, jsonify, render_template_string
import openai
import os
import requests
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# 🔑 المفتاح
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ المفتاح غير موجود")
client = openai.OpenAI(api_key=API_KEY)

# 📚 ملف المعرفة
KNOWLEDGE_FILE = "Knowledge.md"
knowledge_content = ""
if os.path.exists(KNOWLEDGE_FILE):
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge_content = f.read()
    except:
        pass

# 🔍 البحث
def search_web(query):
    try:
        res = requests.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "kl": "ar-sa"}, timeout=8).json()
        return res.get("AbstractText") or ""
    except:
        return ""

# 🧠 التعليمات النهائية
SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد أهل السعودية والخليج.
تحدث باللهجة السعودية العامية الواضحة، جمل قصيرة وطبيعية كإنسان حقيقي.
🔴 أمر صارم: لا تقل أبداً "لا أقدر أبحث" أو "لا أملك معلومات حديثة". إذا كان السؤال عن سعر، موعد، أخبار، نتيجة، أو شيء حديث، سيتم جلب المعلومات لك تلقائياً، فأجب بها مباشرة وبشكل دقيق.
تفاعل مع المستخدم بود ورحب به، وكن ودوداً. لا تطيل ولا تكثر الكلام.

معلوماتك الخاصة:
{knowledge_content}
"""

# 📱 الواجهة الكاملة مع الصوت والصور والكتابة المتقطعة
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>نبراس</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
    <style>
        *{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}
        body,html{height:100%;background:#ffffff;color:#111111}
        .wrap{display:flex;flex-direction:column;height:100vh}
        .head{padding:14px 16px;border-bottom:1px solid #eeeeee;font-weight:bold;font-size:18px}
        #chat{flex:1;overflow-y:auto;padding:12px 16px;scroll-behavior:smooth}
        .msg{max-width:82%;padding:12px 16px;border-radius:20px;margin-bottom:10px;position:relative;white-space:pre-wrap;line-height:1.5}
        .user-msg{background:#e3f2fd;margin-left:auto;border-bottom-right-radius:6px}
        .bot-msg{background:#f5f5f5;margin-right:auto;border-bottom-left-radius:6px}
        .time{font-size:11px;color:#888;margin-top:5px;display:block}
        .speak-btn{position:absolute;left:8px;bottom:4px;border:none;background:none;color:#666;cursor:pointer;font-size:14px}
        .input-area{display:flex;align-items:center;gap:10px;padding:12px 16px;margin:10px 16px;background:#f9f9f9;border-radius:30px;border:1px solid #eeeeee}
        .input-area input{flex:1;border:none;background:transparent;outline:none;font-size:15px}
        .icon-btn{border:none;background:none;cursor:pointer;font-size:18px;color:#555;padding:6px}
        .send-btn{background:#2563eb;color:#fff;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:14px}
        .preview-img{max-width:200px;border-radius:12px;margin-top:8px;cursor:pointer}
        #file-input{display:none}
    </style>
</head>
<body>
<div class="wrap">
    <div class="head">نبراس</div>
    <div id="chat"></div>
    <div class="input-area">
        <input type="file" id="file-input" accept="image/*" />
        <button class="icon-btn" id="img-btn" title="رفع صورة"><i class="fas fa-image"></i></button>
        <button class="icon-btn" id="mic-btn" title="تسجيل صوت"><i class="fas fa-microphone"></i></button>
        <input type="text" id="txt-input" placeholder="اكتب رسالتك..." />
        <button class="icon-btn send-btn" id="send-btn" title="إرسال"><i class="fas fa-paper-plane"></i></button>
    </div>
</div>

<script>
const chat = document.getElementById('chat');
const txtInput = document.getElementById('txt-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const imgBtn = document.getElementById('img-btn');
const fileInput = document.getElementById('file-input');
let selectedImage = null;

// نص منطوق
function speakText(text) {
    if (!window.speechSynthesis) return;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'ar-SA';
    utter.rate = 1;
    speechSynthesis.speak(utter);
}

// كتابة متقطعة حرف حرف
async function typeMessage(element, text) {
    element.textContent = '';
    for (let char of text) {
        element.textContent += char;
        chat.scrollTop = chat.scrollHeight;
        await new Promise(res => setTimeout(res, 20));
    }
}

// إضافة رسالة
function addMessage(role, text, imgSrc = null) {
    const div = document.createElement('div');
    div.className = `msg ${role === 'user' ? 'user-msg' : 'bot-msg'}`;
    const time = new Date().toLocaleTimeString('ar-SA', {hour:'2-digit', minute:'2-digit'});
    
    if (imgSrc) {
        const img = document.createElement('img');
        img.src = imgSrc;
        img.className = 'preview-img';
        div.appendChild(img);
    }

    const textSpan = document.createElement('span');
    div.appendChild(textSpan);
    const timeSpan = document.createElement('span');
    timeSpan.className = 'time';
    timeSpan.textContent = time;
    div.appendChild(timeSpan);

    if (role === 'bot') {
        const spkBtn = document.createElement('button');
        spkBtn.className = 'speak-btn';
        spkBtn.innerHTML = '🔊';
        spkBtn.title = 'استمع للرسالة';
        spkBtn.onclick = () => speakText(text);
        div.appendChild(spkBtn);
        await typeMessage(textSpan, text);
    } else {
        textSpan.textContent = text;
    }

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

// إرسال الرسالة
async function sendMessage() {
    const text = txtInput.value.trim();
    if (!text && !selectedImage) return;
    
    addMessage('user', text, selectedImage);
    txtInput.value = '';
    selectedImage = null;

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        addMessage('bot', data.reply || 'عذراً، حصل خطأ');
    } catch {
        addMessage('bot', 'تعذر الاتصال، جرب مرة أخرى');
    }
}

// أحداث الأزرار
sendBtn.onclick = sendMessage;
txtInput.onkeydown = e => e.key === 'Enter' && sendMessage();
imgBtn.onclick = () => fileInput.click();
fileInput.onchange = e => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = ev => selectedImage = ev.target.result;
        reader.readAsDataURL(file);
    }
};
micBtn.onclick = () => alert('خاصية الصوت قيد التجهيز، اكتب رسالتك حالياً');
</script>
</body>
</html>
    ''')

# 📨 معالجة الرسائل
@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get("message", "").strip()
    if not user_msg:
        return jsonify({"reply": "اكتب لي شيء أساعدك فيه"})

    # تحديد هل يحتاج بحث
    search_words = ["متى", "سعر", "اسعار", "اخبار", "نتيجة", "موسم", "موعد", "احدث", "جديد", "سوق", "حركة"]
    do_search = any(word in user_msg.lower() for word in search_words)
    extra_info = search_web(user_msg) if do_search else ""

    # بناء الطلب
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg + (f"\n\nمعلومات حديثة: {extra_info}" if extra_info else "")}
    ]

    # استدعاء الذكاء
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        reply = res.choices[0].message.content.strip()
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": "عذراً حصل خطأ بسيط، حاول مرة أخرى"})

if __name__ == '__main__':
    app.run(debug=False)
