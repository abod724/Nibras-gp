from flask import Flask, request, jsonify, render_template_string
import openai
import os
import requests

app = Flask(__name__)

API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("المفتاح غير موجود")
client = openai.OpenAI(api_key=API_KEY)

KNOWLEDGE_FILE = "Knowledge.md"
knowledge_content = ""
if os.path.exists(KNOWLEDGE_FILE):
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge_content = f.read()
    except:
        pass

def search_web(query):
    try:
        res = requests.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "kl": "ar-sa"}, timeout=8).json()
        return res.get("AbstractText") or ""
    except:
        return ""

SYSTEM_PROMPT = f"""
أنت نبراس، مساعد أهل السعودية والخليج.
تحدث باللهجة السعودية العامية، جمل قصيرة وطبيعية كإنسان.
لا تقل أبداً "لا أقدر أبحث"، إذا السؤال حديث أو سعر أو موعد سيتم جلب المعلومات لك تلقائياً فأجب بها مباشرة.
تفاعل بود ولا تطيل الكلام.

معلوماتك:
{knowledge_content}
"""

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        *{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}
        html,body{height:100dvh;background:#fff;color:#111;overflow:hidden}
        .container{display:flex;flex-direction:column;height:100dvh}
        .header{padding:10px 15px;position:relative}
        .menu{position:absolute;top:10px;right:15px;border:none;background:none;font-size:20px;cursor:pointer}
        .dropdown{position:absolute;top:40px;right:15px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.15);border-radius:8px;display:none;flex-direction:column;min-width:140px;z-index:999}
        .dropdown.active{display:flex}
        .dropdown button{padding:12px 15px;border:none;background:none;text-align:right;cursor:pointer;border-bottom:1px solid #eee}
        .dropdown button:last-child{border-bottom:none}
        #chat{flex:1;overflow-y:auto;padding:15px}
        .msg{max-width:80%;padding:12px 15px;border-radius:18px;margin-bottom:10px;position:relative;white-space:pre-wrap}
        .user{background:#f0f0f0;margin-left:auto}
        .bot{background:#f8f8f8;margin-right:auto}
        .time{font-size:11px;color:#999;margin-top:5px;display:block;text-align:left}
        .speak{position:absolute;left:8px;bottom:5px;border:none;background:none;color:#888;cursor:pointer}
        .input-area{display:flex;align-items:center;gap:8px;padding:12px 15px;margin:10px;background:#f9f9f9;border-radius:25px;border:1px solid #eee}
        .input-area input{flex:1;border:none;background:transparent;outline:none;font-size:15px}
        .btn{border:none;background:none;font-size:18px;cursor:pointer;color:#555}
        .send{background:#2563eb;color:#fff;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <button class="menu" id="menuBtn"><i class="fas fa-ellipsis-v"></i></button>
        <div class="dropdown" id="menuList">
            <button id="newChat"><i class="fas fa-plus"></i> محادثة جديدة</button>
            <button id="oldChat"><i class="fas fa-history"></i> المحادثات السابقة</button>
        </div>
    </div>
    <div id="chat"></div>
    <div class="input-area">
        <button class="btn"><i class="fas fa-image"></i></button>
        <button class="btn"><i class="fas fa-microphone"></i></button>
        <input type="text" id="txtMsg" placeholder="اكتب رسالتك...">
        <button class="btn send" id="sendBtn"><i class="fas fa-paper-plane"></i></button>
    </div>
</div>

<script>
const chat = document.getElementById('chat');
const txtMsg = document.getElementById('txtMsg');
const sendBtn = document.getElementById('sendBtn');
const menuBtn = document.getElementById('menuBtn');
const menuList = document.getElementById('menuList');

function speakNow(t){if(window.speechSynthesis){let u=new SpeechSynthesisUtterance(t);u.lang='ar-SA';speechSynthesis.speak(u);}}
async function writeType(el, text){
    el.innerText = '';
    for(let i=0; i<text.length; i++){
        el.innerText += text[i];
        chat.scrollTop = chat.scrollHeight;
        await new Promise(r => setTimeout(r, 20));
    }
}
function addMsg(who, text){
    const div = document.createElement('div');
    div.className = `msg ${who}`;
    const time = new Date().toLocaleTimeString('ar-SA', {hour:'2-digit', minute:'2-digit'});
    
    if(who === 'bot'){
        const spkBtn = document.createElement('button');
        spkBtn.className = 'speak';
        spkBtn.innerText = '🔊';
        spkBtn.onclick = () => speakNow(text);
        div.appendChild(spkBtn);
        const textDiv = document.createElement('div');
        div.appendChild(textDiv);
        writeType(textDiv, text);
        const timeDiv = document.createElement('div');
        timeDiv.className = 'time';
        timeDiv.innerText = time;
        div.appendChild(timeDiv);
    }else{
        div.innerText = text;
        const timeDiv = document.createElement('div');
        timeDiv.className = 'time';
        timeDiv.innerText = time;
        div.appendChild(timeDiv);
    }
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

menuBtn.onclick = () => menuList.classList.toggle('active');
document.addEventListener('click', e => {if(!e.target.closest('.header')) menuList.classList.remove('active');});
document.getElementById('newChat').onclick = () => {chat.innerHTML = ''; menuList.classList.remove('active');};
document.getElementById('oldChat').onclick = () => {alert('قيد التجهيز'); menuList.classList.remove('active');};

sendBtn.onclick = sendIt;
txtMsg.onkeydown = e => e.key === 'Enter' && sendIt();
async function sendIt(){
    const v = txtMsg.value.trim();
    if(!v) return;
    addMsg('user', v);
    txtMsg.value = '';
    try{
        const res = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({m: v})
        });
        const data = await res.json();
        addMsg('bot', data.reply || 'تم الاستلام');
    }catch{
        addMsg('bot', 'عذراً حصل خطأ في الاتصال');
    }
}
</script>
</body>
</html>
    ''')

@app.route('/chat', methods=['POST'])
def chat():
    msg = request.json.get("m", "").strip()
    if not msg:
        return jsonify({"reply": "اكتب شيء أساعدك فيه"})
    search_words = ["متى","سعر","اسعار","اخبار","موسم","موعد","احدث","نتيجة","تاريخ","عام"]
    need_search = any(k in msg.lower() for k in search_words)
    search_result = search_web(msg) if need_search else ""
    full_prompt = f"{SYSTEM_PROMPT}\n\nالسؤال: {msg}\n\nمعلومات تم جلبها: {search_result or 'لا يحتاج بحث خارجي'}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":full_prompt},{"role":"user","content":msg}],
        temperature=0.7
    )
    return jsonify({"reply": response.choices[0].message.content.strip()})

if __name__ == '__main__':
    app.run(debug=False)
