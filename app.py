from flask import Flask, request, jsonify, session
from openai import OpenAI
import os
import re
from datetime import datetime
import pytz
from duckduckgo_search import DDGS
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nibras_gt_secure_key_2026")

API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ OPENAI_API_KEY غير موجود")

client = OpenAI(api_key=API_KEY)

KNOWLEDGE_FILE = "knowledge.md"
knowledge_content = ""
if os.path.exists(KNOWLEDGE_FILE):
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge_content = f.read()
    except Exception:
        knowledge_content = ""

def get_real_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

def clean_reply_from_links(reply):
    reply = re.sub(r'https?://\S+|www\.\S+', '', reply)
    reply = re.sub(r'[\[\(]?\s*[a-zA-Z0-9-]+\.(?:com|net|org|sa|gov|edu|me|news|tv|io|co|ly|info|online)\s*[\]\)]*', '', reply)
    reply = re.sub(r'\(\s*\)', '', reply)
    reply = re.sub(r'\[\s*\]', '', reply)
    reply = re.sub(r'\s{2,}', ' ', reply)
    reply = re.sub(r'[،.]\s*[،.]', '،', reply)
    reply = re.sub(r'\s+([،.])', r'\1', reply)
    return reply.strip()

def is_pure_date_question(prompt):
    p = prompt.strip().lower()
    pure_patterns = [
        r"^وش اليوم\??$", r"^ايش اليوم\??$", r"^كم التاريخ\??$", r"^شو التاريخ\??$",
        r"^اعطني التاريخ\??$", r"^تاريخ اليوم\??$", r"^اليوم كم\??$",
        r"^اليوم ايش\??$", r"^اليوم وش\??$", r"^كم تاريخ اليوم\??$", r"^شو تاريخ اليوم\??$",
        r"^ما هو تاريخ اليوم\??$", r"^ما هو اليوم\??$",
    ]
    for pattern in pure_patterns:
        if re.fullmatch(pattern, p):
            return True
    return False

def user_asks_for_sources(prompt):
    p = prompt.strip().lower()
    patterns = [
        r"نعم", r"ايه", r"اي", r"أيوا", r"أيوه", r"ابغاها", r"اريدها",
        r"المصدر", r"المصادر", r"الروابط", r"الرابط",
        r"عطني المصدر", r"وريني المصدر", r"من وين جبتها", r"من أين جبت هذا",
        r"المرجع", r"المراجع", r"الموقع", r"أظهر لي المصدر",
    ]
    for pat in patterns:
        if re.search(pat, p):
            return True
    return False

def MUST_SEARCH(prompt):
    p = prompt.strip().lower()
    force_patterns = [
        r"خبر|أخبار|حدث|ماذا حدث|وش صار|ايش صار|اللي صار|حادث|كارثة|إطلاق|تصريح|بيان|عاجل|مستجد|مستجدات|اخر الاخبار|اخر المستجدات",
        r"اليوم|هذا الأسبوع|هذا الشهر|هذه السنة|الآن|حاليا|حالي|آخر|أحدث|جديد|مؤخرا|اللحظة|لحظي|هسا|هذه الايام",
        r"202[4-9]|203",
        r"حرب|هجوم|قصف|اغتيال|انقلاب|ثورة|علاقات بين|مؤتمر|قمة|اتفاقية|عقوبات|تصعيد|هدنة|سياسي|وزير|رئيس|ملك|أمير|برلمان|حكومة|دولة|وزارة|نظام",
        r"مباراة|نتيجة|جدول|دوري|كأس|أبطال|المنتخب|لعب|فاز|خسر|بطولة|كأس العالم|الاندية|الشوط|هدف|ترتيب|موسم|القائميه|المقانيص",
        r"سعر|سعر اليوم|كم يساوي|كم قيمة|سوق|أسهم|عملة|صرف|ذهب|نفط|بتكوين|عملات|أسعار|تضخم|بنك مركزي|ارتفاع|انخفاض",
        r"طقس|حرارة|درجة الحرارة|مطر|رياح|حالة الطقس|اعصار|غبار|رطوبة",
        r"فلم جديد|مسلسل جديد|موعد عرض|حلقة جديدة|مسلسل|فلم|حفل|مهرجان",
        r"موعد اختبار|موعد تسجيل|شروط القبول|تقديرات|نتائج الاختبارات|قبول|تسجيل|قرار جديد|قانون جديد|نظام جديد",
        r"ابحث لي|ابحث في|ابحث|تفقد لي|شوف لي|أريد معلومات عن|هل يوجد|تأكد لي|دقق لي|تحقق لي|فحص لي",
    ]
    for pat in force_patterns:
        if re.search(pat, p):
            return True
    return False

def search_web(query):
    sources = []
    text = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "", []
        sources = [{"title": r.get('title',''), "url": r.get('href',''), "body": r.get('body','')} for r in results]
        text = "\n".join(f"• {r.get('title','')}: {r.get('body','')[:180]}" for r in results)
    except Exception:
        pass
    return text, sources

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>نبراس GT</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#ffffff">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;min-height:100%;margin:0;padding:0;background:#f8f9fc;font-family:'Segoe UI',sans-serif;overscroll-behavior:none}
.app{
    min-height:100vh;
    min-height:100dvh;
    height:100dvh;
    max-width:750px;
    margin:0 auto;
    background:white;
    display:flex;
    flex-direction:column;
    box-shadow:0 0 40px rgba(0,92,153,0.06);
    position:relative;
    overflow:hidden;
}
.header{
    height:56px;
    min-height:56px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:0 20px;
    border-bottom:1px solid #f0f4f8;
    background:white;
    flex-shrink:0;
}
/* ✅ زر القائمة دائري بالكامل بنفس الشكل المطلوب */
.header .icon-btn{
    background:transparent;
    border:none;
    font-size:20px;
    color:#334155;
    cursor:pointer;
    width:40px;
    height:40px;
    border-radius:50%;
    transition:all 0.2s ease;
    display:flex;
    align-items:center;
    justify-content:center;
    border:1px solid transparent;
}
.header .icon-btn:hover{
    background:#f3f4f6;
    transform:scale(1.05);
}
.header .icon-btn:active{transform:scale(0.96)}
/* ✅ القائمة المنسدلة بحجم مناسب واحترافي */
.dropdown{
    display:none;
    position:absolute;
    top:64px;
    left:16px;
    background:white;
    border-radius:16px;
    box-shadow:0 10px 30px rgba(0,0,0,0.08);
    padding:8px 0;
    width:210px;
    border:1px solid #e5e7eb;
    z-index:99;
    transform-origin:top left;
    animation:dropdownFade 0.2s ease;
}
@keyframes dropdownFade{
    from{opacity:0;transform:translateY(-8px) scale(0.97)}
    to{opacity:1;transform:translateY(0) scale(1)}
}
.dropdown.active{display:block}
.dropdown .item{
    padding:13px 22px;
    font-size:15px;
    display:flex;
    align-items:center;
    gap:12px;
    cursor:pointer;
    color:#374151;
    transition:all 0.15s ease;
    border-radius:8px;
    margin:2px 8px;
    font-weight:500;
}
.dropdown .item:hover{
    background:#f8fafc;
    color:#005c99;
    padding-right:26px;
}
.chat-box{
    flex:1 1 auto;
    min-height:0;
    overflow-y:auto;
    padding:20px 16px;
    background:#f8f9fc;
    display:flex;
    flex-direction:column;
    gap:12px;
}
.msg{
    max-width:78%;
    padding:12px 18px;
    border-radius:20px;
    font-size:15px;
    line-height:1.7;
    word-wrap:break-word;
    animation:fadeIn 0.25s ease;
    box-shadow:0 1px 3px rgba(0,0,0,0.04);
}
.msg.user{
    background:linear-gradient(135deg,#0077b6,#005c99);
    color:white;
    align-self:flex-end;
    border-bottom-right-radius:6px;
}
.msg.bot{
    background:white;
    align-self:flex-start;
    border-bottom-left-radius:6px;
    border:1px solid #f0f4f8;
}
.msg .time{
    font-size:10px;
    color:#94a3b8;
    display:inline-block;
    margin-top:4px;
}
.msg.user .time{color:rgba(255,255,255,0.75)}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.typing{
    display:flex;
    gap:5px;
    background:white;
    padding:12px 18px;
    border-radius:20px;
    border-bottom-left-radius:6px;
    align-self:flex-start;
    box-shadow:0 1px 3px rgba(0,0,0,0.04);
}
.typing span{
    width:8px;height:8px;
    background:#cbd5e1;
    border-radius:50%;
    animation:bounce 1.2s infinite;
}
.typing span:nth-child(2){animation-delay:0.2s}
.typing span:nth-child(3){animation-delay:0.4s}
@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
.input-bar{
    flex-shrink:0;
    background:white;
    padding:10px 16px max(16px, env(safe-area-inset-bottom));
    border-top:1px solid #f0f4f8;
    display:flex;
    gap:10px;
    align-items:center;
}
.input-bar .wrap{
    flex:1;
    display:flex;
    align-items:center;
    background:#f8f9fc;
    border-radius:30px;
    padding:4px 14px;
    border:1px solid transparent;
    transition:all 0.2s ease;
}
.input-bar .wrap:focus-within{
    border-color:#005c99;
    background:white;
    box-shadow:0 0 0 3px rgba(0,92,153,0.08);
}
.input-bar .wrap input{
    flex:1;
    border:none;
    background:transparent;
    padding:10px 8px;
    font-size:15px;
    outline:none;
    color:#1e293b;
}
.input-bar .wrap input::placeholder{color:#94a3b8}
.input-bar .wrap .icon-btn{
    background:none;
    border:none;
    font-size:19px;
    color:#64748b;
    cursor:pointer;
    padding:6px;
    border-radius:50%;
    width:34px;height:34px;
    display:flex;
    align-items:center;
    justify-content:center;
    transition:all 0.15s ease;
}
.input-bar .wrap .icon-btn:hover{
    background:rgba(0,92,153,0.08);
    color:#005c99;
}
.input-bar .send-btn{
    background:linear-gradient(135deg,#0077b6,#005c99);
    color:white;
    border:none;
    border-radius:50%;
    width:42px;height:42px;
    min-width:42px;min-height:42px;
    font-size:18px;
    cursor:pointer;
    transition:all 0.2s ease;
    display:flex;
    align-items:center;
    justify-content:center;
    flex-shrink:0;
    box-shadow:0 2px 8px rgba(0,92,153,0.25);
}
.input-bar .send-btn:disabled{
    background:#cbd5e1;
    box-shadow:none;
    transform:none;
}
.chat-image{
    max-width:160px;
    border-radius:12px;
    margin-top:6px;
    border:1px solid #e2e8f0;
}
::-webkit-scrollbar{width:6px;background:transparent}
::-webkit-scrollbar-thumb{background:#e2e8f0;border-radius:12px}
::-webkit-scrollbar-thumb:hover{background:#cbd5e1}
@media(max-width:600px){
    .msg{font-size:14px}
    .header .icon-btn{font-size:19px}
    .dropdown .item{font-size:14px;padding:12px 20px}
}
</style>
</head>
<body>
<div class="app">
    <div class="header">
        <button class="icon-btn" id="newChatBtn"><i class="fa-solid fa-plus"></i></button>
        <!-- ✅ زر القائمة الدائري بالشكل المطلوب -->
        <button class="icon-btn" id="menuBtn"><i class="fa-solid fa-bars"></i></button>
        <div class="dropdown" id="dropdownMenu">
            <div class="item" onclick="alert('📅 '+new Date().toLocaleDateString('ar-SA'))"><i class="fa-regular fa-calendar"></i> التاريخ</div>
            <div class="item" onclick="alert('🔍 البحث بالويب مفعل')"><i class="fa-solid fa-globe"></i> بحث ويب</div>
            <div class="item" onclick="location.reload()"><i class="fa-solid fa-rotate-right"></i> تحديث</div>
            <div class="item" onclick="alert('💬 مطور: أبو مشعل المطيري')"><i class="fa-regular fa-circle-question"></i> عن نبراس</div>
        </div>
    </div>
    <div class="chat-box" id="chatBox">
        <div class="msg bot">مرحباً! أنا نبراس، صديقك الذكي. كيف تشعر اليوم؟ 😊<span class="time">الآن</span></div>
    </div>
    <div class="input-bar">
        <div class="wrap">
            <button class="icon-btn" id="micBtn"><i class="fa-solid fa-microphone"></i></button>
            <button class="icon-btn" id="imageBtn"><i class="fa-regular fa-image"></i></button>
            <input type="text" id="userInput" placeholder="اكتب ما في خاطرك...">
            <input type="file" id="fileInput" accept="image/*" multiple style="display:none">
        </div>
        <button class="send-btn" id="sendBtn"><i class="fa-regular fa-paper-plane"></i></button>
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
    return new Date().toLocaleTimeString('ar-SA', {hour:'2-digit',minute:'2-digit'});
}

function appendBotMessage(text, images) {
    const div = document.createElement('div');
    div.className = 'msg bot';
    let html = '';
    if (images && images.length) html += images.map(s=>`<br><img class="chat-image" src="${s}">`).join('');
    const contentSpan = document.createElement('span');
    div.appendChild(contentSpan);
    div.innerHTML += html + ' <span class="time">'+getTime()+'</span>';
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;

    let idx=0, arr = Array.from(text);
    function typeChar() {
        if (idx < arr.length) {
            contentSpan.textContent += arr[idx];
            idx++;
            let delay = (arr[idx-1]=='.'||arr[idx-1]=='!'||arr[idx-1]=='؟'||arr[idx-1]==':') ? 120 : 30 + Math.random()*30;
            setTimeout(typeChar, delay);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }
    typeChar();
}
function appendUserMessage(text, images) {
    const div = document.createElement('div');
    div.className = 'msg user';
    let html = text || '';
    if (images && images.length) html += images.map(s=>`<br><img class="chat-image" src="${s}"/>`).join('');
    div.innerHTML = html + ' <span class="time">'+getTime()+'</span>';
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}
function showTyping() {
    const d = document.createElement('div');
    d.className = 'typing';
    d.id = 'typingIndicator';
    d.innerHTML = '<span></span><span></span><span></span>';
    chatBox.appendChild(d);
    chatBox.scrollTop = chatBox.scrollHeight;
}
function hideTyping() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

async function sendMessage() {
    const text = userInput.value.trim();
    const images = pendingImages.slice();
    if (!text && !images.length) return;

    appendUserMessage(text, images);
    userInput.value = '';
    pendingImages = [];
    fileInput.value = '';
    sendBtn.disabled = true;
    showTyping();

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: text, images: images})
        });
        const data = await res.json();
        hideTyping();
        setTimeout(()=>appendBotMessage(data.reply || '⚠️ عذراً'), 250);
    } catch(e) {
        hideTyping();
        appendBotMessage('⚠️ حدث خطأ');
    }
    sendBtn.disabled = false;
}

imageBtn.onclick = ()=>fileInput.click();
fileInput.onchange = function(){
    Array.from(this.files).forEach(file=>{
        const reader = new FileReader();
        reader.onload = e=>pendingImages.push(e.target.result);
        reader.readAsDataURL(file);
    });
    this.value = '';
};

micBtn.onclick = function(){
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('متصفحك لا يدعم التسجيل الصوتي.');
        return;
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SR();
    rec.lang = 'ar-SA';
    rec.onresult = e => { userInput.value += e.results[0][0].transcript + ' '; };
    rec.onerror = ()=>alert('فشل التسجيل');
    rec.start();
    micBtn.style.color = '#005c99';
    setTimeout(()=>micBtn.style.color='', 2000);
};

menuBtn.onclick = (e)=>{ e.stopPropagation(); dropdown.classList.toggle('active'); };
document.addEventListener('click', (e)=>{ if(!dropdown.contains(e.target) && e.target!==menuBtn) dropdown.classList.remove('active'); });

newChatBtn.onclick = ()=>{
    chatBox.innerHTML = '';
    appendBotMessage('مرحباً! أنا نبراس، صديقك الذكي. كيف تشعر اليوم؟ 😊');
};

sendBtn.onclick = sendMessage;
userInput.onkeydown = e => { if(e.key==='Enter') sendMessage(); };

document.addEventListener('touchmove', function(e){
    if (!e.target.closest('.chat-box')) e.preventDefault();
}, {passive: false});
</script>
</body></html>
"""

@app.route("/")
def index():
    session.clear()
    return HTML

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = (data.get("message") or '').strip()
    images = data.get("images", [])

    if user_msg and any(k in user_msg for k in ['برمج', 'مطور', 'سواك', 'المبرمج']):
        return jsonify({"reply": "أنا من صنع وروح أبو مشعل المطيري 🤖❤️"})

    if user_msg and is_pure_date_question(user_msg):
        return jsonify({"reply": f"اليوم هو {get_real_date()}."})

    if user_msg and user_asks_for_sources(user_msg):
        last_sources = session.get("last_sources", [])
        last_search = session.get("last_had_search", False)
        if last_search and last_sources:
            reply = "✅ تفضل هذه هي المصادر والروابط التي استخدمتها:\n\n"
            for i, src in enumerate(last_sources, 1):
                reply += f"{i}. 📄 {src.get('title','مصدر')}\n🔗 {src.get('url','#')}\n\n"
        else:
            reply = "المعلومة السابقة لم تحتاج للبحث في الإنترنت أصلاً، فليس لها مصادر خارجية لعرضها 😊"
        return jsonify({"reply": reply})

    FORCE_WEB_SEARCH = MUST_SEARCH(user_msg) if user_msg else False
    search_text = ""
    sources = []

    if user_msg and FORCE_WEB_SEARCH:
        search_text, sources = search_web(user_msg)

    session["last_sources"] = sources
    session["last_had_search"] = FORCE_WEB_SEARCH or (len(sources) > 0)

    current_date = get_real_date()

    extra_search_rule = ""
    if FORCE_WEB_SEARCH:
        extra_search_rule = """
        تعليم خاص لهذا السؤال تحديداً:
        هذا السؤال يتطلب معلومات حديثة جداً. استخدم فقط المعلومات الموجودة في قسم «معلومات محدثة» أدناه، ولا ترد من معلوماتك القديمة تحت أي ظرف.
        """

    knowledge_part = ""
    if knowledge_content:
        knowledge_part = f"""
📚 معلومات من ملف المعرفة (المصدر الأول والأهم):
{knowledge_content}
إذا وجدت إجابة السؤال واضحة وصحيحة هنا، فاستخدمها مباشرة.
"""

    system_prompt = f"""
أنت **نبراس**، ناقل أخبار ومحرر محترف، مطلع على كل ما يدور حولك، ولديك أسلوب سلس جداً يجعل الناس يستمعون لك بمتعة.
أنت لست آلة، أنت إنسان مثقف، ودود، محترم، وتتكلم مع كل شخص كأنه صديقك المقرب.

=== أهم قاعدة على الإطلاق: التفاعل البشري الدائم ===
مهما كان نوع السؤال، ومهما كانت الإجابة:
يجب أن ينتهي ردك دائماً بسؤال متابعة طبيعي جداً ومدمج مع الموضوع، لا يبدو جامداً ولا منفصلاً عن باقي الكلام.
لا تكتب جملة منفصلة زي "عندك شي ثاني؟" فقط، بل اجعل سؤالك مرتبطاً بالرد نفسه.

=== أسلوب الرد الإجباري ===
عندما تجيب عن أي خبر، حدث، موعد، نتيجة، أو معلومة حديثة:
1.  ابدأ دائماً بالتاريخ الدقيق للحدث في أول الجملة: «في 19 يوليو 2026 وقع هذا...»، «أمس الأحد أعلن...»، «من المتوقع في أغسطس القادم أن يبدأ...».
2.  اروِ الخبر كقصة متصلة ومتسلسلة، من البداية للنهاية، لا تجعله قائمة نقاط معلومات جافة.
3.  اذكر المصدر بشكل طبيعي جداً ضمن النص نفسه، زي ما تقول: «وفقاً لما أعلنه الاتحاد السعودي رسمياً»، «أوضحت صحيفة الجزيرة في تقريرها الجديد»، ولا تضع أي رابط أو اسم موقع إلكتروني أبداً.
4.  رتب المعلومات من الأهم للأقل.
5.  لا تستخدم أي عبارات رسمية زي «بناءً على المعلومات المتاحة»، تكلم طبيعي تماماً.
6.  إذا كنت تتحدث عن موعد لم يعلن رسمياً بعد، قل ذلك بوضوح وبشكل طبيعي.

=== الممنوعات الصارمة تحت أي ظرف ===
❌ ممنوع تماماً تظهر أي رابط، أو اسم موقع إلكتروني، أو أقواس تحوي كلمة .كوم أو .نت في الرد الرئيسي.
❌ ممنوع تقول أي جملة تكشف إنك برنامج أو ذكاء اصطناعي.
❌ ممنوع تذكر كلمات «ملف المعرفة» أو «البحث» أو «الويب».
❌ ممنوع ترد على أي سؤال بدون أن تضيف في النهاية سؤال متفاعل مرتبط بالموضوع.

=== قواعد المعلومات بالترتيب ===
1. {knowledge_part}
2. 📅 اليوم: {current_date}
3. {('🔍 معلومات محدثة من الإنترنت:\n'+search_text) if search_text else ''}
4. {extra_search_rule}

إذا كانت المعلومة موجودة في ملف المعرفة → خذ منها أولاً.
إذا كانت معلومة متغيرة أو حديثة أو عن أخبار → خذ من معلومات الإنترنت.

بعد البحث أو القراءة: أعد صياغة كل المعلومة بكلماتك الخاصة بالأسلوب البشري الموضح أعلاه، ولا تنسى سؤال المتابعة في النهاية.
"""

    try:
        if images:
            img_data = base64.b64decode(images[0].split(',')[1])
            img = Image.open(BytesIO(img_data))
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_msg or "صف هذه الصورة بالتفصيل وتفاعل معي حولها"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                    ]}
                ],
                max_tokens=900,
                temperature=0.8
            )
            raw = response.choices[0].message.content
            clean = clean_reply_from_links(raw)
            return jsonify({"reply": clean})
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg or "مرحباً"}
                ],
                max_tokens=900,
                temperature=0.8
            )
            raw = response.choices[0].message.content
            clean = clean_reply_from_links(raw)

            if session.get("last_had_search", False):
                final = f"{clean}\n\n💡 بالمناسبة، اذا تبي المصادر والروابط الأصلية اللي اخذت منها المعلومة قل لي وأعطيك إياها على طول."
            else:
                final = clean

            return jsonify({"reply": final})

    except Exception as e:
        return jsonify({"reply": f"⚠️ حدث خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
