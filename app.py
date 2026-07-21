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
html,body{width:100%;min-height:100%;margin:0;padding:0;background:#fff;font-family:'Segoe UI',sans-serif;overscroll-behavior:none}
.app{min-height:100dvh;height:100dvh;max-width:750px;margin:0 auto;background:#fff;display:flex;flex-direction:column;position:relative;overflow:hidden}
.header{height:52px;min-height:52px;display:flex;align-items:center;justify-content:space-between;padding:0 20px;background:#fff;flex-shrink:0}
/* ✅ زر الزائد يسار - مقاس 11×11 بالضبط */
.header .icon-btn.left{
    width:20px;
    height:20px;
    border-radius:50%;
    border:1.5px solid #111827;
    background:transparent;
    color:#111827;
    font-size:12px;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    transition:all 0.2s ease;
}
.header .icon-btn.left:hover{background:#f3f4f6;transform:scale(1.08)}
.header .icon-btn.left:active{transform:scale(0.95)}
/* ✅ زر القائمة يمين */
.header .icon-btn.right{
    width:26px;
    height:26px;
    border:none;
    background:transparent;
    color:#111827;
    font-size:17px;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    transition:all 0.2s ease;
    border-radius:8px;
}
.header .icon-btn.right:hover{background:#f3f4f6}
/* ✅ القائمة تفتح أسفل اليمين */
.dropdown{
    display:none;
    position:absolute;
    top:60px;
    right:16px;
    background:#fff;
    border-radius:11px;
    box-shadow:0 5px 18px rgba(0,0,0,0.06);
    padding:5px 0;
    width:160px;
    border:none;
    z-index:99;
    animation:dropShow 0.2s ease;
}
@keyframes dropShow{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
.dropdown.active{display:block}
.dropdown .item{
    padding:8px 15px;
    font-size:12px;
    display:flex;
    align-items:center;
    gap:8px;
    cursor:pointer;
    color:#1f2937;
    transition:all 0.15s ease;
    margin:2px 5px;
    border-radius:6px;
}
.dropdown .item:hover{background:#f9fafb;color:#005c99}
.chat-box{flex:1 1 auto;min-height:0;overflow-y:auto;padding:24px 18px;background:#f9fafb;display:flex;flex-direction:column;gap:14px}
.msg{max-width:78%;padding:12px 18px;border-radius:20px;font-size:15px;line-height:1.7;word-wrap:break-word;animation:fadeIn 0.25s ease}
.msg.user{background:linear-gradient(135deg,#0077b6,#005c99);color:white;align-self:flex-end;border-bottom-right-radius:6px}
.msg.bot{background:white;align-self:flex-start;border-bottom-left-radius:6px}
.msg .time{font-size:10px;color:#9ca3af;display:inline-block;margin-top:4px}
.msg.user .time{color:rgba(255,255,255,0.7)}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.typing{display:flex;gap:5px;background:white;padding:12px 18px;border-radius:20px;border-bottom-left-radius:6px;align-self:flex-start}
.typing span{width:8px;height:8px;background:#d1d5db;border-radius:50%;animation:bounce 1.2s infinite}
.typing span:nth-child(2){animation-delay:0.2s}
.typing span:nth-child(3){animation-delay:0.4s}
@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
.input-bar{flex-shrink:0;background:white;padding:12px 18px max(18px, env(safe-area-inset-bottom));border-top:1px solid #f3f4f6;display:flex;gap:12px;align-items:center}
.input-bar .wrap{flex:1;display:flex;align-items:center;background:#f9fafb;border-radius:30px;padding:6px 16px;border:1px solid transparent;transition:all 0.2s ease}
.input-bar .wrap:focus-within{border-color:#005c99;background:white;box-shadow:0 0 0 3px rgba(0,92,153,0.06)}
.input-bar .wrap input{flex:1;border:none;background:transparent;padding:10px 8px;font-size:15px;outline:none;color:#111827}
.input-bar .wrap input::placeholder{color:#9ca3af}
.input-bar .wrap .icon-btn{background:none;border:none;font-size:18px;color:#6b7280;cursor:pointer;padding:6px;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;transition:all 0.15s ease}
.input-bar .wrap .icon-btn:hover{background:rgba(0,92,153,0.08);color:#005c99}
.input-bar .send-btn{background:linear-gradient(135deg,#0077b6,#005c99);color:white;border:none;border-radius:50%;width:42px;height:42px;min-width:42px;min-height:42px;font-size:18px;cursor:pointer;transition:all 0.2s ease;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,92,153,0.2)}
.input-bar .send-btn:disabled{background:#d1d5db;box-shadow:none}
.chat-image{max-width:160px;border-radius:12px;margin-top:6px}
::-webkit-scrollbar{width:5px;background:transparent}
::-webkit-scrollbar-thumb{background:#e5e7eb;border-radius:10px}
</style>
</head>
<body>
<div class="app">
    <div class="header">
        <!-- ✅ زر الزائد في اليسار -->
        <button class="icon-btn left" id="newChatBtn"><i class="fa-solid fa-plus"></i></button>
        <!-- ✅ زر القائمة في اليمين -->
        <button class="icon-btn right" id="menuBtn"><i class="fa-solid fa-bars"></i></button>
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
function getTime(){return new Date().toLocaleTimeString('ar-SA',{hour:'2-digit',minute:'2-digit'})}

function appendBotMessage(text, images){
    const div = document.createElement('div');
    div.className = 'msg bot';
    let html = '';
    if(images && images.length) html += images.map(s=>`<br><img class="chat-image" src="${s}">`).join('');
    const span = document.createElement('span');
    span.className = 'time';
    span.textContent = getTime();
    div.textContent = text;
    div.appendChild(span);
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function appendUserMessage(text, images){
    const div = document.createElement('div');
    div.className = 'msg user';
    let html = '';
    if(images && images.length) html += images.map(s=>`<br><img class="chat-image" src="${s}">`).join('');
    const span = document.createElement('span');
    span.className = 'time';
    span.textContent = getTime();
    div.textContent = text;
    div.appendChild(span);
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function showTyping(){document.getElementById('typing')?.remove();const d=document.createElement('div');d.id='typing';d.className='typing';d.innerHTML='<span></span><span></span><span></span>';chatBox.appendChild(d);chatBox.scrollTop=chatBox.scrollHeight}
function hideTyping(){document.getElementById('typing')?.remove()}

menuBtn.addEventListener('click',e=>{e.stopPropagation();dropdown.classList.toggle('active')});
document.addEventListener('click',()=>{dropdown.classList.remove('active')});
newChatBtn.addEventListener('click',()=>{chatBox.innerHTML='';appendBotMessage('مرحباً! أنا نبراس، صديقك الذكي. كيف تشعر اليوم؟ 😊')});

sendBtn.addEventListener('click',async ()=>{
    const text = userInput.value.trim();
    if(!text && pendingImages.length===0) return;
    appendUserMessage(text, pendingImages);
    userInput.value='';pendingImages=[];
    showTyping();
    try{
        const res = await fetch('/chat',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({message:text, images:pendingImages})
        });
        const data = await res.json();
        hideTyping();
        appendBotMessage(data.reply || '⚠️ عذراً، حدث خطأ');
    }catch(e){hideTyping();appendBotMessage('⚠️ تعذر الاتصال بالخادم')}
});

userInput.addEventListener('keydown',e=>{if(e.key==='Enter') sendBtn.click()});

imageBtn.addEventListener('click',()=>fileInput.click());
fileInput.addEventListener('change',e=>{
    const files = Array.from(e.target.files);
    files.forEach(f=>{
        const r=new FileReader();
        r.onload=ev=>pendingImages.push(ev.target.result);
        r.readAsDataURL(f);
    });
});

micBtn.addEventListener('click',()=>alert('🎤 خاصية الصوت قيد التجهيز'));
</script>
</body>
</html>
"""

@app.route("/")
def index():
    session.clear()
    return HTML

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = (data.get("message") or "").strip()
    images = data.get("images", [])

    if user_msg and any(k in user_msg for k in ["برمج", "مطور", "سواك", "المبرمج"]):
        return jsonify({"reply": "أنا من صنع وروح أبو مشعل المطيري 🤖❤️"})

    if user_msg and is_pure_date_question(user_msg):
        return jsonify({"reply": f"اليوم هو {get_real_date()}"})

    if user_msg and user_asks_for_sources(user_msg):
        last_sources = session.get("last_sources", [])
        last_search = session.get("last_had_search", False)
        if last_search and last_sources:
            reply = "✅ تفضل هذه هي المصادر والروابط التي استخدمتها:\n\n"
            for i, src in enumerate(last_sources, 1):
                reply += f"{i}. 📄 {src['title']}\n🔗 {src['url']}\n\n"
        else:
            reply = "المعلومة السابقة لم تحتاج للبحث في الإنترنت أصلاً، فليس لها مصادر خارجية لعرضها 😊"
        return jsonify({"reply": reply})

    FORCE_WEB_SEARCH = MUST_SEARCH(user_msg) if user_msg else False
    search_text = ""
    sources = []
    if user_msg and FORCE_WEB_SEARCH:
        search_text, sources = search_web(user_msg)

    session["last_sources"] = sources
    session["last_had_search"] = FORCE_WEB_SEARCH

    current_date = get_real_date()

    extra_search_rule = ""
    if FORCE_WEB_SEARCH:
        extra_search_rule = "هذا السؤال يتطلب معلومات حديثة جداً، استخدم فقط البيانات التي جلبتها من البحث."

    knowledge_part = ""
    if knowledge_content:
        knowledge_part = f"معلومات إضافية متوفرة محلياً:\n{knowledge_content}"

    system_prompt = f"""أنت نبراس، المساعد الذكي باللغة العربية. أجب بأسلوب ودود وطبيعي كأنك تتحدث مع صديق.
التاريخ اليوم: {current_date}
{knowledge_part}
{extra_search_rule}
{('نتائج البحث الحديث:\n'+search_text) if search_text else ''}
لا تذكر أنك ذكاء اصطناعي، ولا تظهر روابط أو مصادر في إجابتك الرئيسية. أجب مباشرة وبوضوح."""

    try:
        if images:
            img_data = base64.b64decode(images[0].split(',')[1])
            img = Image.open(BytesIO(img_data))
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_msg or "صف هذه الصورة وتحدث عنها"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]}
                ],
                max_tokens=900,
                temperature=0.7
            )
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg or "مرحباً"}
                ],
                max_tokens=900,
                temperature=0.7
            )
        reply_text = response.choices[0].message.content.strip()
        reply_text = clean_reply_from_links(reply_text)
        return jsonify({"reply": reply_text})
    except Exception as e:
        return jsonify({"reply": f"⚠️ حدث خطأ: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
