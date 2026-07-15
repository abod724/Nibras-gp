from flask import Flask, request, jsonify
import os
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================
# واجهة HTML كاملة داخل متغير
# ============================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>نبراس GT</title>

<style>
    body {
        background: #ffffff;
        margin: 0;
        font-family: Tahoma, sans-serif;
    }

    .top-bar {
        width: 100%;
        height: 55px;
        background: #f8f8f8;
        border-bottom: 1px solid #ddd;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 15px;
    }

    .new-chat {
        font-size: 26px;
        cursor: pointer;
        color: #444;
    }

    .menu {
        position: relative;
    }

    .menu-btn {
        background: #eee;
        padding: 8px 12px;
        border-radius: 6px;
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
        border-radius: 6px;
        width: 150px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }

    .menu-content a {
        display: block;
        padding: 10px;
        text-decoration: none;
        color: #333;
        border-bottom: 1px solid #eee;
    }

    .menu-content a:hover {
        background: #f2f2f2;
    }

    .chat-box {
        width: 100%;
        max-width: 700px;
        margin: 40px auto;
        padding: 20px;
    }

    .msg {
        background: #f7f7f7;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }

    .input-area {
        display: flex;
        gap: 10px;
        margin-top: 20px;
    }

    input {
        flex: 1;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #ccc;
    }

    button {
        padding: 12px 20px;
        border: none;
        background: #007bff;
        color: white;
        border-radius: 8px;
        cursor: pointer;
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
        chat.innerHTML += `<div class="msg">👤 ${text}</div>`;

        const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: text })
        });

        const data = await res.json();
        chat.innerHTML += `<div class="msg">🤖 ${data.reply}</div>`;
        document.getElementById("input").value = "";
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

<div class="chat-box">
    <div id="chat"></div>

    <div class="input-area">
        <input id="input" placeholder="اكتب رسالتك هنا...">
        <button onclick="sendMsg()">إرسال</button>
    </div>
</div>

</body>
</html>
"""

# ============================
# صفحة الواجهة
# ============================

@app.get("/")
def home():
    return HTML_PAGE

# ============================
# API الردود + بحث ويب
# ============================

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

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        web_search={"enable": True}
    )

    reply = response.output_text

    return jsonify({"reply": reply})

# ============================
# تشغيل السيرفر
# ============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
