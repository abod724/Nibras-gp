from flask import Flask, request, jsonify
from openai import OpenAI
import os
from datetime import datetime
import pytz
from duckduckgo_search import DDGS

app = Flask(__name__)

API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("OPENAI_API_KEY غير موجود")
client = OpenAI(api_key=API_KEY)

def get_real_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

def search_web(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=2))
        if not results:
            return ""
        context = "\n".join(
            f"• {r.get('title','')}: {r.get('body','')[:140]}..." for r in results
        )
        return context
    except Exception:
        return ""

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>نبراس GT</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
body,html {height:100%;overflow:hidden;background:#f5f5fa;}
*{box-sizing:border-box;}
.app {height:100vh;max-width:750px;margin:0 auto;background:white;box-shadow:0 0 22px rgba(0,0,0,0.08);display:flex;flex-direction:column;}
.header {height:58px;display:flex;align-items:center;justify-content:space-between;background:white;border-bottom:1.5px solid #edeef0;padding:0 16px;}
.header .title {font-size:18px;font-weight:700;color:#005c99;letter-spacing:1px;display:flex;align-items:center;gap:7px;}
.header .icon-btn {background:none;border:none;padding:7px;color:#005c99;font-size:23px;border-radius:50%;cursor:pointer;transition:0.15s;}
.header .icon-btn:hover {background:#e7f0fd;}
.dropdown {position:absolute;top:64px;right:26px;background:#fff;box-shadow:0 6px 28px rgba(0,60,150,0.09);border-radius:14px;padding:4px;width:205px;display:none;flex-direction:column;gap:2px;z-index:81; border:1.5px solid #e9e9e9;}
.dropdown.active{display:flex;}
.dropdown .item{padding:12px 20px;font-size:15px;font-weight:500;display:flex;align-items:center;gap:9px;color:#224;cursor:pointer;border-radius:8px;transition:0.18s;}
.dropdown .item:hover{background:#f4f8ff;color:#1676c7;}
.chat-box{flex:1;overflow-y:auto;padding:16px 14px 0;background:#f5f5fa;display:flex;flex-direction:column;gap:10px;}
.msg{max-width:78%;padding:10px 15px;border-radius:18px;font-size:15.5px;line-height:1.7;animation:fadeIn 0.28s ease;word-break:break-word;position:relative;}
.msg.user{background:#005c99;color:white;align-self:flex-end;border-bottom-right-radius:8px;}
.msg.bot{background:white;color:#232;align-self:flex-start;border-bottom-left-radius:8px;box-shadow:0 1px 4px rgba(50,50,70,.07);}
.msg .time{font-size:11px;color:#969;background:none;display:inline-block;margin-top:4px;}
.msg.user .time{color:#aad;}
@keyframes fadeIn {from {opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
.typing {display:flex;align-items:center;padding:9px 14px;border-radius:16px;gap:5px;background:white;align-self:flex-start;border-bottom-left-radius:7px;}
.typing span{display:inline-block;width:8px;height:8px;margin:0 2px;border-radius:50%;background:#cbc;animation:bounce 1.2s infinite;}
.typing span:nth-child(2){animation-delay:0.19s;}
.typing span:nth-child(3){animation-delay:0.37s;}
@keyframes bounce{0%,60%,100%{transform:translateY(0);}30%{transform:translateY(-7px);}}
.input-bar{flex-shrink:0;display:flex;align-items:center;gap:7px;background:#fff;padding:11px 12px 13px;border-top:1.1px solid #e0e6ee;}
.input-bar .wrap{display:flex;align-items:center;flex:1;gap:4px;background:#f3f5fa;border-radius:23px;padding:2px 9px;border:1px solid transparent;transition:.23s;}
.input-bar .wrap:focus-within{border:1.25px solid #005c99;background:white;}
.input-bar input[type=text]{font-size:15.5px;flex:1;background:transparent;border:none;outline:none;padding:7px 4px;}
.input-bar .icon-btn {background:transparent;border:none;font-size:18.5px;color:#586a8c;transition:0.13s;border-radius:50%;margin:0 2px;cursor:pointer;width:32px;height:32px;display:flex;align-items:center;justify-content:center;}
.input-bar .icon-btn:hover{background:#e7f1fb;color:#005c99;}
.input-bar .send-btn {background:#005c99;color:white;border:none;border-radius:50%;width:40px;height:40px;font-size:18px;cursor:pointer;transition:0.18s;box-shadow:0 1px 6px rgba(0,60,220,0.03);}
.input-bar .send-btn:disabled{background:#bbb;}
.chat-image{max-width:170px;border-radius:9px;margin-top:7px;border:1px solid #e0e0ec;}
::-webkit-scrollbar{width:7px;border-radius:6px;background:#f3f3fa;}
::-webkit-scrollbar-thumb{background:#e6eaf3;border-radius:14px;}
@media(max-width:600px){.chat-box{padding:8px 1vw 0;}.msg{font-size:14px;}}
</style>
</head><body>
<div class="app">
    <div class="header">
        <button class="icon-btn" id="newChatBtn" title="محادثة جديدة"><i class="fa-solid fa-plus"></i></button>
        <span class="title"><i class="fa-solid fa-bolt"></i> نبراس GT</span>
        <button class="icon-btn" id="menuBtn" title="المزيد"><i class="fa-solid fa-bars"></i></button>
        <div class="dropdown" id="dropdownMenu">
            <div class="item" onclick="alert('📅 التـاريخ: ' + new Date().toLocaleDateString('ar-SA'))"><i class="fa-solid fa-calendar-days"></i> معرفة التاريخ</div>
            <div class="item" onclick="alert('🔎 عند سؤالك يتم البحث تلقائيا عن أحدث النتائج عبر DuckDuckGo')" ><i class="fa-solid fa-globe"></i> البحث بالويب مباشر</div>
            <div class="item" onclick="location.reload()"><i class="fa-solid fa-arrow-rotate-right"></i> إعادة تحميل</div>
            <div class="item" onclick="alert('💬 مطور النظام: أبو مشعل المطيري\\nنبراس GT v2.1')"><i class="fa-solid fa-circle-info"></i> عن النظام</div>
        </div>
    </div>
    <div class="chat-box" id="chatBox">
        <div class="msg bot">مرحباً! أنا نبراس GT، كيف أساعدك؟ <span class="time">الآن</span></div>
    </div>
    <div class="input-bar">
        <div class="wrap">
            <button class="icon-btn" id="micBtn" title="تسجيل صوتي"><i class="fa-solid fa-microphone"></i></button>
            <button class="icon-btn" id="imageBtn" title="إضافة صورة"><i class="fa-solid fa-image"></i></button>
            <input type="text" id="userInput" placeholder="اكتب سؤالك أو طلبك...">
            <input type="file" id="fileInput" accept="image/*" multiple style="display:none">
        </div>
        <button class="send-btn" id="sendBtn"><i class="fa-solid fa-paper-plane"></i></button>
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

// كتابة متقطعة
async function appendBotMessage(text, images) {
    const div = document.createElement('div');
    div.className = 'msg bot';
    let html = "";
    if (images && images.length > 0) {
        html += images.map(src=>`<br><img class="chat-image" src="${src}">`).join('');
    }
    let contentDiv = document.createElement('span');
    div.appendChild(contentDiv);
    div.innerHTML += html + ' <span class="time">'+getTime()+'</span>';
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;

    // تحليل النص إلى كلمات أو حرف
    let idx=0;
    let arr = Array.from(text);
    function typeChar() {
        if(idx < arr.length){
            contentDiv.textContent += arr[idx];
            idx++;
            setTimeout(typeChar, (arr[idx-1]=='.'||arr[idx-1]=='!'||arr[idx-1]=='؟'||arr[idx-1]==':')?120:32+Math.random()*32);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }
    typeChar();
}
function appendUserMessage(text, images) {
    const div = document.createElement('div');
    div.className = 'msg user';
    let html = text||'';
    if(images && images.length > 0)
        html += images.map(src => `<br><img class='chat-image' src='${src}'/>`).join('');
    div.innerHTML = `${html} <span class="time">${getTime()}</span>`;
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
    let el = document.getElementById('typingIndicator');
    if(el) el.remove();
}
// إرسال الرسالة
async function sendMessage() {
    const text = userInput.value.trim();
    const images = pendingImages;
    if(!text && images.length===0) return;
    appendUserMessage(text,images);
    userInput.value = '';
    pendingImages = [];
    fileInput.value = '';
    sendBtn.disabled = true;
    showTyping();
    // api request
    try {
        const res = await fetch('/chat', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({message:text,images:images})
        });
        const data = await res.json();
        hideTyping();
        setTimeout(()=>appendBotMessage(data.reply||'⚠️ لم أستطع الرد'),350);
    } catch {
        hideTyping();
        appendBotMessage('⚠️ حدث خطأ في الاتصال');
    }
    sendBtn.disabled = false;
    userInput.focus();
}
// الصور
imageBtn.onclick = ()=>fileInput.click();
fileInput.onchange = function(){
    Array.from(this.files).forEach(file=>{
        const reader = new FileReader();
        reader.onload = e=>pendingImages.push(e.target.result);
        reader.readAsDataURL(file);
    });this.value='';
};
// ميكرفون
micBtn.onclick = function(){
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('متصفحك لا يدعم التسجيل الصوتي. استخدم Chrome.');
        return;
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SR();
    recognition.lang = 'ar-SA';
    recognition.onresult = e=>{userInput.value += e.results[0][0].transcript+' ';userInput.focus();};
    recognition.onerror = ()=>alert('حدث خطأ في التسجيل');
    recognition.start();
    micBtn.style.background = '#e0eaf4'; micBtn.style.color = '#1892c8';
    setTimeout(()=>{micBtn.style.background = '';micBtn.style.color='';},2000);
};
// القائمة
menuBtn.onclick = ()=>dropdown.classList.toggle('active');
document.addEventListener('click',e=>{
    if(!menuBtn.contains(e.target) && !dropdown.contains(e.target)) dropdown.classList.remove('active');
});
// بداية جديدة
newChatBtn.onclick = ()=>{
    chatBox.innerHTML = '';
    appendBotMessage('مرحباً! أنا نبراس GT، كيف أساعدك؟');
};
// الإدخال والسهم لإرسال
sendBtn.onclick = sendMessage;
userInput.onkeydown = function(e){if(e.key==='Enter') sendMessage();}
userInput.focus();

// منع التمرير خارج منطقة الشات في الجوال
document.body.addEventListener('touchmove', function(e){
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

    if user_msg and any(key in user_msg for key in ['برمج', 'مطور', 'سواك', 'المبرمج']):
        return jsonify({
            "reply": "تم تطويري وبرمجتي من قبل أبو مشعل المطيري (قسم الاتصالات الإدارية - التأهيل الشامل) 🤖🔥"
        })

    search_context = search_web(user_msg) if user_msg else ""
    current_date = get_real_date()
    # نضيف البحث فقط إذا يوجد سياق فعلا
    system_prompt = f"""أنت نبراس GT، مساعد ذكي متجدد السرد وحديث، ترد بجمل قصيرة وواضحة (حد أقصى 3 جمل).
اليوم: {current_date}.
{('📌 نتائج بحث الويب:\n'+search_context) if search_context else ''}
عند سؤال المستخدم عن المبرمج عرف بنفسك (أبو مشعل المطيري).
"""

    if images:
        try:
            content = [{"type":"text","text":user_msg or "صف هذه الصورة"}]
            for img in images[:3]:
                content.append({"type": "image_url", "image_url": {"url": img}})
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":system_prompt},{"role":"user","content":content}],
                max_tokens=200,
                temperature=0.3
            )
            return jsonify({"reply": response.choices[0].message.content})
        except Exception as e:
            return jsonify({"reply": f"⚠️ خطأ في معالجة الصورة: {str(e)}"}), 500

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_msg or "مرحباً"}],
            max_tokens=200,
            temperature=0.33
        )
        return jsonify({"reply": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"reply": f"⚠️ خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
