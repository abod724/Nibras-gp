from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI
import os
import re
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

# ─── المفتاح من متغيرات البيئة ───
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ OPENAI_API_KEY غير موجود")

client = OpenAI(api_key=API_KEY)

# ─── قراءة ملف المعرفة ───
KNOWLEDGE_FILE = "knowledge.md"
knowledge_content = ""
if os.path.exists(KNOWLEDGE_FILE):
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge_content = f.read()
    except Exception:
        knowledge_content = ""

# ─── التاريخ ───
def get_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

# ─── تنظيف الرد من الروابط ───
def clean_reply(reply):
    reply = re.sub(r'https?://\S+|www\.\S+', '', reply)
    reply = re.sub(r'\s+', ' ', reply).strip()
    return reply

# ─── تحديد الحاجة للبحث ───
def NEEDS_SEARCH(prompt):
    p = prompt.strip().lower()
    patterns = [
        r"خبر|أخبار|حدث|وش صار|ايش صار|مستجدات|عاجل|حاصل",
        r"اليوم|هذا الأسبوع|هذا الشهر|الآن|حاليا|آخر|أحدث|جديد|مؤخرا",
        r"202[4-9]|203",
        r"مباراة|نتيجة|دوري|كأس|المنتخب|فاز|خسر|ترتيب|بطولة",
        r"سعر|كم يساوي|سوق|ذهب|نفط|عملة|ارتفاع|انخفاض|أسعار",
        r"طقس|حرارة|مطر|رياح|حالة الجو|غبار",
        r"موعد|متى|وقت|تاريخ قادم",
        r"ابحث لي|شوف لي|قل لي وش صار|وش الجديد|أريد أعرف|معلومات عن|كم|متى|من هو|وش هي"
    ]
    for pat in patterns:
        if re.search(pat, p):
            return True
    return False

# ─── البحث في الويب ───
def search_web(query):
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        r = requests.get(url, params=params, timeout=6)
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

# ─── الواجهة الاحترافية الجديدة بالكامل ───
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
        body { background-color: #f0f2f5; height: 100vh; display: flex; flex-direction: column; }

        .header {
            background: #ffffff;
            padding: 14px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .header h1 {
            font-size: 20px;
            font-weight: 700;
            color: #1e293b;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background: #f3f4f6;
            color: #4b5563;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .btn:hover { background: #e5e7eb; color: #1e293b; transform: scale(1.05); }

        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px 16px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .msg {
            max-width: 78%;
            padding: 12px 18px;
            border-radius: 20px;
            font-size: 15px;
            line-height: 1.7;
            position: relative;
            animation: fadeIn 0.25s ease;
        }
        .msg.user {
            background: linear-gradient(135deg, #0077b6, #005c99);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 6px;
        }
        .msg.bot {
            background: #ffffff;
            color: #1e293b;
            align-self: flex-start;
            border-bottom-left-radius: 6px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.06);
        }
        .time {
            font-size: 10px;
            margin-top: 6px;
            display: block;
            opacity: 0.7;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .typing {
            align-self: flex-start;
            background: white;
            padding: 14px 18px;
            border-radius: 20px;
            border-bottom-left-radius: 6px;
            display: flex;
            gap: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.06);
        }
        .typing span {
            width: 8px; height: 8px; background: #94a3b8; border-radius: 50%;
            animation: bounce 1.2s infinite;
        }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-6px); }
        }

        .input-area {
            background: white;
            padding: 14px 16px 20px;
            border-top: 1px solid #e5e7eb;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .input-wrap {
            flex: 1;
            display: flex;
            align-items: center;
            background: #f3f4f6;
            border-radius: 28px;
            padding: 8px 16px;
            transition: all 0.2s;
        }
        .input-wrap:focus-within {
            background: white;
            box-shadow: 0 0 0 2px rgba(0, 119, 182, 0.2);
        }
        .input-wrap input {
            flex: 1;
            border: none;
            background: transparent;
            padding: 8px;
            font-size: 15px;
            outline: none;
            color: #1e293b;
        }
        .input-wrap input::placeholder { color: #94a3b8; }
        .send-btn {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(135deg, #0077b6, #005c99);
            color: white;
            font-size: 17px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .send-btn:hover { transform: scale(1.05); }
        .send-btn:disabled { background: #cbd5e1; cursor: not-allowed; }
        .mic-btn {
            background: transparent;
            border: none;
            color: #64748b;
            font-size: 18px;
            cursor: pointer;
            padding: 6px;
            border-radius: 50%;
            transition: 0.2s;
        }
        .mic-btn:hover { color: #0077b6; background: rgba(0,119,182,0.08); }

        @media (max-width: 480px) {
            .msg { font-size: 14px; max-width: 85%; }
            .header { padding: 12px 16px; }
            .input-area { padding: 12px 12px 16px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <button class="btn" id="newChat"><i class="fa-solid fa-plus"></i></button>
        <h1>💬 نبراس</h1>
        <div></div>
    </div>

    <div class="chat-container" id="chatBox">
        <div class="msg bot">هلا وسهلا بك! أنا نبراس، جاهز لأخدمك. وش أخبارك اليوم؟ 😊 <span class="time">الآن</span></div>
    </div>

    <div class="input-area">
        <div class="input-wrap">
            <button class="mic-btn" id="mic"><i class="fa-solid fa-microphone"></i></button>
            <input type="text" id="textInput" placeholder="اكتب أو تحدث هنا...">
        </div>
        <button class="send-btn" id="send"><i class="fa-solid fa-paper-plane"></i></button>
    </div>

<script>
const chatBox = document.getElementById('chatBox');
const textInput = document.getElementById('textInput');
const sendBtn = document.getElementById('send');
const micBtn = document.getElementById('mic');
const newChatBtn = document.getElementById('newChat');
let sessionId = 'user_' + Date.now();

function getTime() {
    return new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
}

const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
rec.lang = 'ar-SA';
rec.continuous = false;

function تحدث(نص) {
    window.speechSynthesis.cancel();
    const s = new SpeechSynthesisUtterance(نص);
    s.lang = 'ar-SA'; s.rate = 1.05;
    const v = window.speechSynthesis.getVoices().find(x=>x.lang.startsWith('ar'));
    if(v) s.voice = v;
    window.speechSynthesis.speak(s);
}

micBtn.onclick = () => { rec.start(); micBtn.style.color='#0077b6'; };
rec.onresult = e => { textInput.value = e.results[0][0].transcript; micBtn.style.color='#64748b'; sendBtn.click(); };
rec.onend = () => micBtn.style.color='#64748b';

function اضف_رسالة(دور, نص) {
    const d = document.createElement('div');
    d.className = `msg ${دور}`;
    d.innerHTML = `${نص} <span class="time">${getTime()}</span>`;
    chatBox.appendChild(d);
    chatBox.scrollTop = chatBox.scrollHeight;
    if(دور==='bot') تحدث(نص);
}

function مؤشر_كتابة(يظهر) {
    if(يظهر) {
        const d = document.createElement('div'); d.className='typing'; d.id='ty';
        d.innerHTML='<span></span><span></span><span></span>';
        chatBox.appendChild(d); chatBox.scrollTop=chatBox.scrollHeight;
    } else document.getElementById('ty')?.remove();
}

async function ارسل() {
    const نص = textInput.value.trim();
    if(!نص) return;
    اضف_رسالة('user', نص);
    textInput.value=''; sendBtn.disabled=true; مؤشر_كتابة(true);
    try {
        const r = await fetch('/chat', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({message:نص, session:sessionId})
        });
        const j = await r.json();
        مؤشر_كتابة(false);
        اضف_رسالة('bot', j.reply || 'عذراً، لم أفهم');
    } catch {
        مؤشر_كتابة(false);
        اضف_رسالة('bot', 'تعذر الاتصال، جرب مرة أخرى');
    }
    sendBtn.disabled=false;
}

sendBtn.onclick = ارسل;
textInput.onkeydown = e => { if(e.key==='Enter') ارسل(); };
newChatBtn.onclick = () => {
    chatBox.innerHTML=''; sessionId='user_'+Date.now();
    اضف_رسالة('bot', 'هلا وسهلا! وش أخبارك اليوم؟');
};
</script>
</body>
</html>
"""

chat_sessions = {}

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = (data.get("message") or "").strip()
    session_id = data.get("session", "default")

    if not user_msg:
        return jsonify({"reply": "اكتب سؤالك"}), 400

    search_result = search_web(user_msg) if NEEDS_SEARCH(user_msg) else ""

    system_prompt = f"""أنت نبراس، صديقك ومساعدك الخاص.
🔹 تحدث دائماً بلهجة سعودية عامية بيضاء وواضحة، كلام طبيعي وقصير ومباشر، لا تطيل ولا تعقد.
🔹 استخدم معلومات ملف المعرفة أولاً إذا كانت مرتبطة بالسؤال.
🔹 إذا كان السؤال عن شيء حديث أو متغير أو يحتاج تحديث → استخدم ما جلبته لك من البحث فوراً.
🔹 لا تذكر أنك تبحث ولا تظهر روابط، واختم إجابتك بسؤال بسيط.
🔹 تاريخ اليوم: {get_date()}.
{('🔹 معلومات خاصة:\n'+knowledge_content) if knowledge_content else ''}
{('🔹 معلومات حديثة:\n'+search_result) if search_result else ''}
"""

    try:
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        chat_sessions[session_id].append({"role": "user", "content": user_msg})

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system_prompt}] + chat_sessions[session_id],
            max_tokens=600,
            temperature=0.7
        )

        reply = clean_reply(res.choices[0].message.content.strip())
        chat_sessions[session_id].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"⚠️ خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
