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
    }

    .top-bar {
        height: 55px;
        background: #fafafa;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 20px;
        flex-shrink: 0;
    }

    .new-chat {
        font-size: 26px;
        cursor: pointer;
        color: #007bff;
        font-weight: bold;
    }

    .menu {
        position: relative;
    }

    .menu-btn {
        background: #eee;
        padding: 8px 12px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
    }

    .menu-content {
        display: none;
        position: absolute;
        right: 0;
        top: 40px;
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
        width: 160px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }

    .menu-content a {
        display: block;
        padding: 10px;
        text-decoration: none;
        color: #333;
        border-bottom: 1px solid #eee;
        font-size: 13px;
    }

    .menu-content a:hover {
        background: #f5f5f5;
    }

    .chat-area {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        max-width: 900px;
        margin: 0 auto;
        box-sizing: border-box;
    }

    .msg {
        background: #f7f7f7;
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 10px;
        font-size: 15px;
        line-height: 1.6;
    }

    .msg.user {
        background: #e8f0ff;
        border-right: 4px solid #4a8cff;
    }

    .msg.bot {
        background: #f2f2f2;
        border-right: 4px solid #999;
    }

    .input-bar {
        flex-shrink: 0;
        border-top: 1px solid #e0e0e0;
        padding: 10px 20px;
        background: #fafafa;
        display: flex;
        gap: 10px;
        max-width: 900px;
        margin: 0 auto;
        width: 100%;
        box-sizing: border-box;
    }

    input {
        flex: 1;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #ccc;
        font-size: 15px;
    }

    button {
        padding: 12px 18px;
        border: none;
        background: #007bff;
        color: white;
        border-radius: 10px;
        cursor: pointer;
        font-size: 15px;
    }

    button:hover {
        background: #005fcc;
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

    <div class="menu">
        <div class="menu-btn" onclick="toggleMenu()">خيارات</div>
        <div class="menu-content" id="menu-content">
            <a href="#">إعدادات</a>
            <a href="#">حول نبراس</a>
            <a href="#">تسجيل خروج</a>
        </div>
    </div>
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

    keywords = [
        "من برمجك", "مين برمجك", "من سواك", "مين سواك",
        "من طورك", "مين طورك", "المبرمج", "من صممك",
        "من صنعك", "مين صنعك", "من جهزك"
    ]
    if any(k in prompt for k in keywords):
        return jsonify({
            "reply": "تم تطويري وبرمجتي من قبل أبو مشعل المطيري يعمل بالتأهيل الشامل قسم الاتصالات الإدارية."
        })

    # لو تبي بحث ويب فعلي لازم يكون حسابك مفعّل له،
    # هنا نخليها رد عادي من الموديل:
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
