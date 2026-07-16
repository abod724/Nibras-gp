from flask import Flask, request, jsonify
from openai import OpenAI
import os
from datetime import datetime
import pytz
from duckduckgo_search import DDGS

app = Flask(__name__)

# ─── المفتاح من متغيرات البيئة ───
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("OPENAI_API_KEY غير موجود")
client = OpenAI(api_key=API_KEY)

# ─── التاريخ الصحيح ───
def get_real_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

# ─── البحث في الويب ───
def search_web(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=2))
        if not results:
            return ""
        return "\n".join(f"• {r.get('title','')}: {r.get('body','')[:140]}..." for r in results)
    except:
        return ""

# ─── واجهة HTML ───
HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>نبراس GT</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:#f5f5fa;font-family:sans-serif}
.app{height:100vh;max-width:750px;margin:0 auto;background:white;display:flex;flex-direction:column;box-shadow:0 0 30px rgba(0,0,0,0.04)}
.header{height:52px;display:flex;align-items:center;padding:0 18px;border-bottom:1px solid #eaeef3;background:white}
.header .icon-btn{background:none;border:none;font-size:26px;color:#005c99;cursor:pointer;padding:6px 12px;border-radius:50%;transition:0.15s}
.header .icon-btn:hover{background:#e9f0fc}
.dropdown{display:none;position:absolute;top:56px;left:20px;background:white;border-radius:14px;box-shadow:0 8px 30px rgba(0,60,130,0.1);padding:6px 0;width:200px;border:1px solid #e6edf5;z-index:99}
.dropdown.active{display:block}
.dropdown .item{padding:12px 22px;font-size:15px;display:flex;align-items:center;gap:12px;cursor:pointer;color:#1a2a3a;transition:0.15s;border-radius:6px;margin:2px 6px}
.dropdown .item:hover{background:#f0f6ff;color:#005c99}
.chat-box{flex:1;overflow-y:auto;padding:18px 16px;background:#f5f5fa;display:flex;flex-direction:column;gap:10px}
.msg{max-width:78%;padding:10px 16px;border-radius:18px;font-size:15px;line-height:1.6;word-wrap:break-word;animation:fadeIn 0.25s}
.msg.user{background:#005c99;color:white;align-self:flex-end;border-bottom-right-radius:6px}
.msg.bot{background:white;align-self:flex-start;border-bottom-left-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,0.04)}
.msg .time{font-size:10px;color:#999;display:inline-block;margin-top:3px}
.msg.user .time{color:#b0d4ee}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.typing{display:flex;gap:4px;background:white;padding:10px 16px;border-radius:16px;border-bottom-left-radius:6px;align-self:flex-start}
.typing span{width:8px;height:8px;background:#b0b8c8;border-radius:50%;animation:bounce 1.2s infinite}
.typing span:nth-child(2){animation-delay:0.2s}
.typing span:nth-child(3){animation-delay:0.4s}
@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
.input-bar{background:white;padding:8px 14px 14px;border-top:1px solid #e0e8f0;display:flex;gap:8px;align-items:center}
.input-bar .wrap{flex:1;display:flex;align-items:center;background:#f3f5fa;border-radius:26px;padding:2px 10px;border:1px solid transparent;transition:0.2s}
.input-bar .wrap:focus-within{border-color:#005c99;background:white}
.input-bar .wrap input{flex:1;border:none;background:transparent;padding:10px 6px;font-size:15px;outline:none}
.input-bar .wrap .icon-btn{background:none;border:none;font-size:18px;color:#5a6a7a;cursor:pointer;padding:4px;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;transition:0.15s}
.input-bar .wrap .icon-btn:hover{background:#e5edf5;color:#005c99}
.input-bar .send-btn{background:#005c99;color:white;border:none;border-radius:50%;width:40px;height:40px;font-size:17px;cursor:pointer;transition:0.15s;display:flex;align-items:center;justify-content:center}
.input-bar .send-btn:disabled{background:#b0b8c8}
.chat-image{max-width:160px;border-radius:10px;margin-top:6px;border:1px solid #e0e0ec}
::-webkit-scrollbar{width:5px;background:#f0f0f5}
::-webkit-scrollbar-thumb{background:#d0d8e0;border-radius:12px}
@media(max-width:600px){.msg{font-size:14px}.header .icon-btn{font-size:22px}}
</style>
</head>
<body>
<div class="app">
    <div class="header">
        <button class="icon-btn" id="menuBtn" title="القائمة"><i class="fa-solid fa-bars"></i></button>
        <div class="dropdown" id="dropdownMenu">
            <div class="item" onclick="alert('📅 ' + new Date().toLocaleDateString('ar-SA'))"><i class="fa-regular fa-calendar"></i> التاريخ</div>
            <div class="item" onclick="alert('🔍 البحث عبر DuckDuckGo مفعل تلقائياً')"><i class="fa-solid fa-globe"></i> بحث ويب</div>
            <div class="item" onclick="location.reload()"><i class="fa-solid fa-rotate-right"></i> تحديث</div>
            <div class="item" onclick="alert('💬 مطور: أبو مشعل المطيري\\nنبراس GT v2.2')"><i class="fa-regular fa-circle-question"></i> عن نبراس</div>
        </div>
    </div>
    <div class="chat-box" id="chatBox">
        <div class="msg bot">مرحباً! أنا نبراس GT، كيف أساعدك؟ <span class="time">الآن</span></div>
    </div>
    <div class="input-bar">
        <div class="wrap">
            <button class="icon-btn" id="micBtn"><i class="fa-solid fa-microphone"></i></button>
            <button class="icon-btn" id="imageBtn"><i class="fa-regular fa-image"></i></button>
            <input type="text" id="userInput" placeholder="اكتب سؤالك...">
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
        setTimeout(()=>appendBotMessage(data.reply || '⚠️ عذراً، لم أستطع الرد'), 250);
    } catch(e) {
        hideTyping();
        appendBotMessage('⚠️ حدث خطأ في الاتصال بالخادم');
    }
    sendBtn.disabled = false;
    userInput.focus();
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
        alert('متصفحك لا يدعم التسجيل الصوتي. استخدم Chrome.');
        return;
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SR();
    rec.lang = 'ar-SA';
    rec.onresult = e => { userInput.value += e.results[0][0].transcript + ' '; userInput.focus(); };
    rec.onerror = ()=>alert('فشل التسجيل');
    rec.start();
    micBtn.style.color = '#005c99';
    setTimeout(()=>micBtn.style.color='', 2000);
};

menuBtn.onclick = (e)=>{ e.stopPropagation(); dropdown.classList.toggle('active'); };
document.addEventListener('click', (e)=>{ if(!dropdown.contains(e.target) && e.target!==menuBtn) dropdown.classList.remove('active'); });

sendBtn.onclick = sendMessage;
userInput.onkeydown = e => { if(e.key==='Enter') sendMessage(); };
userInput.focus();

document.addEventListener('touchmove', function(e){
    if (!e.target.closest('.chat-box')) e.preventDefault();
}, {passive: false});
</script>
</body></html>
"""

@app.route("/")
def index():
    return HTML

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = (data.get("message") or '').strip()
    images = data.get("images", [])

    # ─── رد على "من برمجك" (دائماً يعمل) ───
    if user_msg and any(k in user_msg for k in ['برمج', 'مطور', 'سواك', 'المبرمج']):
        return jsonify({
            "reply": "تم تطويري وبرمجتي من قبل أبو مشعل المطيري (قسم الاتصالات الإدارية - التأهيل الشامل) 🤖🔥"
        })

    # ─── التحقق من صلاحية المفتاح ───
    try:
        test_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
    except Exception as e:
        return jsonify({
            "reply": "⚠️ مفتاح OpenAI غير صالح أو الرصيد منتهي. يرجى شحن الرصيد أو استخدام مفتاح آخر."
        })

    # ─── البحث في الويب ───
    search_context = search_web(user_msg) if user_msg else ""
    current_date = get_real_date()
    system_prompt = f"""أنت نبراس GT، مساعد ذكي حديث. أجب بجمل قصيرة (حد أقصى 3 جمل).
اليوم: {current_date}.
{('📌 نتائج بحث الويب:\n'+search_context) if search_context else ''}
عند سؤال المستخدم عن المبرمج عرف بنفسك.
"""

    # ─── معالجة الصور أو النص ───
    try:
        if images:
            content = [{"type":"text","text":user_msg or "صف هذه الصورة"}]
            for img in images[:3]:
                content.append({"type":"image_url","image_url":{"url":img}})
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":system_prompt},{"role":"user","content":content}],
                max_tokens=200,
                temperature=0.3
            )
            return jsonify({"reply": response.choices[0].message.content})
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_msg or "مرحباً"}],
                max_tokens=200,
                temperature=0.33
            )
            return jsonify({"reply": response.choices[0].message.content})
    except Exception as e:
        return jsonify({
            "reply": f"⚠️ حدث خطأ في الذكاء الاصطناعي: {str(e)[:100]}"
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
