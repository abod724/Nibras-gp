from flask import Flask, request, jsonify
import os
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>نبراس GT</title>

<style>
    body {
        margin: 0;
        font-family: Tahoma, sans-serif;
        background: #ffffff;
        display: flex;
        flex-direction: column;
        height: 100vh;
        overflow: hidden;
    }

    /* الشريط العلوي */
    .top-bar {
        height: 65px;
        background: #ffffff;
        border-bottom: 1px solid #e6e6e6;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 25px;
        flex-shrink: 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    /* زر محادثة جديدة */
    .new-chat {
        font-size: 32px;
        cursor: pointer;
        color: #007bff;
        font-weight: bold;
        transition: 0.2s;
    }
    .new-chat:hover {
        transform: scale(1.15);
    }

    /* القائمة ثلاث نقاط */
    .menu-btn {
        font-size: 28px;
        cursor: pointer;
        color: #444;
        padding: 5px 10px;
        border-radius: 8px;
        transition: 0.2s;
    }
    .menu-btn:hover {
        background: #f2f2f2;
    }

    .menu-content {
        display: none;
        position: absolute;
        right: 25px;
        top: 70px;
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 10px;
        width: 180px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.15);
        overflow: hidden;
    }

    .menu-content a {
        display: block;
        padding: 12px;
        text-decoration: none;
        color: #333;
        border-bottom: 1px solid #eee;
        font-size: 14px;
    }
    .menu-content a:hover {
        background: #f5f5f5;
    }

    /* منطقة المحادثة */
    .chat-area {
        flex: 1;
        overflow-y: auto;
        padding: 25px;
        max-width: 900px;
        margin: 0 auto;
        width: 100%;
        box-sizing: border-box;
    }

    .msg {
        background: #f7f7f7;
        padding: 18px;
        border-radius: 16px;
        margin-bottom: 18px;
        font-size: 17px;
        line-height: 1.7;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        animation: fadeIn 0.25s ease;
        max-width: 100%;
    }

    .msg.user {
        background: #e8f0ff;
        border-right: 6px solid #4a8cff;
    }

    .msg.bot {
        background: #f2f2f2;
        border-right: 6px solid #999;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* شريط الإدخال */
    .input-bar {
        flex-shrink: 0;
        border-top: 1px solid #e0e0e0;
        padding: 15px 25px;
        background: #fafafa;
        display: flex;
        gap: 12px;
        max-width: 900px;
        margin: 0 auto;
        width: 100%;
        box-sizing: border-box;
    }

    input {
        flex: 1;
        padding: 16px;
        border-radius: 14px;
        border: 1px solid #ccc;
        font-size: 17px;
        transition: 0.2s;
    }
    input:focus {
        border-color: #007bff;
        outline: none;
        box-shadow: 0 0 5px rgba(0,123,255,0.3);
    }

    button {
        padding: 16px 24px;
        border: none;
        background: #007bff;
        color: white;
        border-radius: 14px;
        cursor: pointer;
        font-size: 17px;
        transition: 0.2s;
    }
    button:hover {
        background: #005fcc;
        transform: scale(1.05);
    }
</style>

<script>
    function toggleMenu() {
        const menu = document.getElementById("menu-content");
        menu.style.display = menu.style.display === "block" ? "none" : "block";
    }

    function newChat() {
        document.getElementById("chat").innerHTML = "";
    }

    async function sendMsg() {
        const text = document.getElementById("input").value;
        if (!text) return;

        const chat = document.getElementById("chat");
        chat.innerHTML += `<div class="msg user">👤 ${text}</div>`;

        const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: text })
        });

        const data = await res.json();
        chat.innerHTML += `<div class="msg bot">🤖 ${data.reply}</div>`;
        document.getElementById("input").value = "";
        chat.scrollTop = chat.scrollHeight;
    }
</script>

</head>

<body>

<div class="top-bar">
    <div class="new-chat" onclick="newChat()">+</div>
    <div class="menu-btn" onclick="toggleMenu()">⋮</div>
</div>

<div class="menu-content" id="menu-content">
    <a href="#">إعدادات</a>
    <a href="#">حول نبراس</a>
    <a href="#">تسجيل خروج</a>
</div>

<div class="chat-area" id="chat"></div>

<div class="input-bar">
    <input id="input" placeholder="اكتب رسالتك هنا...">
    <button onclick="sendMsg()">إرسال</button>
</div>

</body>
</html>
"""

@app.get("/")
def home():
    return HTML_PAGE

@app.post("/ask")
def ask_ai():
    data = request.json
    prompt = data["prompt"]

    keywords = ["من برمجك", "مين برمجك", "من سواك", "مين سواك",
                "من طورك", "مين طورك", "المبرمج", "من صممك",
                "من صنعك", "مين صنعك", "من جهزك"]

    if any(k in prompt for k in keywords):
        return jsonify({
            "reply": "تم تطويري وبرمجتي من قبل أبو مشعل المطيري يعمل بالتأهيل الشامل قسم الاتصالات الإدارية."
        })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "أنت مساعد ذكي اسمه نبراس."},
            {"role": "user", "content": prompt}
        ]
    )

    reply = response.choices[0].message.content
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
