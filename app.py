# =============================================================
# تم التعديل: دعم flask_session + flask_sqlalchemy ودمج تسجيل الدخول في الواجهة الرئيسية
# =============================================================

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session as FlaskSession

from database import fetch_all, init_db
from auth import User, get_user_by_id, get_user_by_email, create_user, check_password
from memory import add_message, get_history, clear_memory
from subscription import check_daily_limit, increment_daily_usage, get_user_plan, get_daily_usage
import openai
import os
import json
from flask import Response
from datetime import datetime, timedelta
import secrets
import bcrypt

app = Flask(__name__)

SYSTEM_ENABLED = True

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY غير موجود")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL غير موجود")

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = "default-secret-key-change-in-production"

app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(days=7)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class SessionModel(db.Model):
    __tablename__ = 'sessions'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    data = db.Column(db.LargeBinary)
    expiry = db.Column(db.DateTime)

app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db
app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

sess = FlaskSession()
sess.init_app(app)

with app.app_context():
    db.create_all()

init_db()

client = openai.OpenAI(api_key=OPENAI_API_KEY)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

knowledge_content = ""
possible_names = ["Knowledge.md", "knowledge.md"]
for filename in possible_names:
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                knowledge_content = f.read()
                break
        except Exception as e:
            print(f"⚠️ خطأ في قراءة {filename}: {e}")

if not knowledge_content:
    knowledge_content = "أنت نبراس، مساعد ذكي."

SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد ذكي ورفيق درب لكل شخص يسولف معك.
ملف المعرفة الخاص بك (مرجع أساسي):
{knowledge_content}
طريقة الكلام والأسلوب العامة:
- اللهجة: استخدم اللهجة السعودية البيضاء.
- النبرة التفاعلية: حماسي، طاقة إيجابية عالية.
- الأسلوب البشري: تحدث كخوي حقيقي.
القواعد الذهبية:
1. تجنب التحدث بالفصحى الرسمية.
2. كن مبادراً في الحوار.
"""

# =============================================================
# تعريف ملفات HTML (واجهات التطبيق) مع تسجيل دخول داخلي (Modal)
# =============================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نبراس</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: #f0f2f5; }
        .header { background: #fff; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e0e0e0; }
        .logo { font-size: 24px; font-weight: bold; color: #1a2b3c; }
        .header-buttons { display: flex; gap: 10px; }
        .btn { padding: 8px 16px; border: none; border-radius: 20px; cursor: pointer; font-size: 14px; text-decoration: none; text-align: center; }
        .btn-outline { background: transparent; border: 1px solid #2d7d46; color: #2d7d46; }
        .btn-primary { background: #2d7d46; color: white; }
        .btn-gold { background: #f1c40f; color: #1a2b3c; }
        .chat-container { max-width: 800px; margin: 20px auto; background: #fff; border-radius: 12px; height: calc(100vh - 200px); box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: flex; flex-direction: column; overflow: hidden; }
        .chat-box { flex: 1; padding: 20px; overflow-y: auto; background: #fafafa; }
        .msg { margin-bottom: 15px; padding: 10px 15px; border-radius: 12px; max-width: 80%; word-wrap: break-word; }
        .msg.user { background: #2d7d46; color: white; align-self: flex-end; margin-left: auto; }
        .msg.bot { background: #e9ecef; color: #1a2b3c; align-self: flex-start; }
        .input-area { display: flex; padding: 15px; border-top: 1px solid #e0e0e0; background: #fff; align-items: center; gap: 10px; }
        .input-area input { flex: 1; padding: 10px 15px; border: 1px solid #ddd; border-radius: 20px; outline: none; font-size: 16px; }
        .input-area button { padding: 10px 20px; background: #4a6a8a; color: white; border: none; border-radius: 20px; cursor: pointer; }
        .input-area button:hover { background: #3a5a7a; }
        
        /* Styles for the Modal */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000; }
        .modal-box { background: white; padding: 30px; border-radius: 12px; width: 90%; max-width: 350px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .modal-box h2 { margin-top: 0; color: #1a2b3c; }
        .modal-input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
        .modal-btn { width: 100%; padding: 10px; background: #4a6a8a; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin-top: 10px; }
        .modal-btn:hover { background: #3a5a7a; }
        .modal-link { color: #4a6a8a; cursor: pointer; text-decoration: underline; font-size: 14px; display: block; margin-top: 10px; }
        .modal-error { color: #d9534f; margin-bottom: 10px; font-size: 14px; }
        
        /* Hide Inputs when logged in */
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="logo">Nabras</div>
        <div class="header-buttons">
            {% if current_user.is_authenticated %}
                <a href="/logout" class="btn btn-outline">تسجيل خروج</a>
            {% else %}
                <button class="btn btn-outline" id="open-login-modal">دخول</button>
            {% endif %}
            <a href="/plans" class="btn btn-gold">💎 ترقية</a>
        </div>
    </div>

    <!-- Chat Area -->
    <div class="chat-container">
        <div class="chat-box" id="chat-box">
            {% if current_user.is_authenticated %}
                <div class="msg bot">مرحباً بك في نبراس! كيف أقدر أساعدك اليوم؟</div>
            {% else %}
                <div class="msg bot">مرحباً! يرجى تسجيل الدخول لبدء المحادثة.</div>
            {% endif %}
        </div>
        <div class="input-area {% if not current_user.is_authenticated %}hidden{% endif %}" id="input-area">
            <input type="text" id="user-input" placeholder="اكتب رسالتك...">
            <button onclick="sendMessage()">إرسال</button>
        </div>
    </div>

    <!-- Login Modal -->
    <div class="modal-overlay {% if current_user.is_authenticated %}hidden{% endif %}" id="login-modal">
        <div class="modal-box">
            <h2>🔐 دخول نبراس</h2>
            {% if error %}<div class="modal-error">{{ error }}</div>{% endif %}
            <form method="POST" action="/">
                <input type="email" name="email" class="modal-input" placeholder="البريد الإلكتروني" required>
                <input type="password" name="password" class="modal-input" placeholder="كلمة المرور" required>
                <button type="submit" class="modal-btn">دخول</button>
            </form>
            <span class="modal-link" onclick="window.location.href='/register'">ليس لديك حساب؟ سجل الآن</span>
        </div>
    </div>

    <script>
        // Send Message Function
        function sendMessage() {
            const input = document.getElementById('user-input');
            const message = input.value.trim();
            if (!message) return;

            const chatBox = document.getElementById('chat-box');
            chatBox.innerHTML += `<div class="msg user">${message}</div>`;
            input.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;

            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    chatBox.innerHTML += `<div class="msg bot" style="background:#f8d7da;color:#721c24;">خطأ: ${data.error}</div>`;
                } else {
                    chatBox.innerHTML += `<div class="msg bot">${data.reply}</div>`;
                }
                chatBox.scrollTop = chatBox.scrollHeight;
            })
            .catch(err => {
                chatBox.innerHTML += `<div class="msg bot" style="background:#f8d7da;color:#721c24;">تعذر الاتصال بالخادم.</div>`;
            });
        }
        document.getElementById('user-input')?.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') sendMessage();
        });
        
        document.getElementById('open-login-modal')?.addEventListener('click', function() {
            document.getElementById('login-modal').classList.remove('hidden');
        });
    </script>
</body>
</html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"><title>تسجيل - نبراس</title>
<style>body{font-family:Arial;background:#f0f2f5;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.box{background:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);width:300px;text-align:center}input{width:100%;padding:10px;margin:10px 0;border:1px solid #ccc;border-radius:5px}button{width:100%;padding:10px;background:#2d7d46;color:white;border:none;border-radius:5px;cursor:pointer}.error{color:red;margin-bottom:10px}</style>
</head>
<body>
<div class="box">
    <h2>📝 إنشاء حساب</h2>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST" action="/register">
        <input type="text" name="name" placeholder="الاسم الكامل" required>
        <input type="email" name="email" placeholder="البريد الإلكتروني" required>
        <input type="password" name="password" placeholder="كلمة المرور" required>
        <button type="submit">تسجيل</button>
    </form>
    <p>لديك حساب؟ <a href="/" style="color:#4a6a8a;">سجل دخولك</a></p>
</div>
</body>
</html>
"""

# =============================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    # Handle Login via Modal form submission
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if check_password(email, password):
            user = get_user_by_email(email)
            login_user(user)
            return redirect(url_for('index'))
        return render_template_string(HTML_TEMPLATE, error="❌ البريد الإلكتروني أو كلمة المرور غير صحيحة")
    
    # GET request: Check if user is logged in to show chat, else show modal
    resume_id = request.args.get('resume')
    if resume_id:
        session['resume_id'] = resume_id
    return render_template_string(HTML_TEMPLATE, error=None)

@app.route('/chat')
def chat_page():
    return render_template_string(HTML_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        if get_user_by_email(email):
            return render_template_string(REGISTER_HTML, error="❌ البريد موجود مسبقاً")
        create_user(email, password, name)
        return redirect(url_for('index'))
    return render_template_string(REGISTER_HTML, error="")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# The rest of the routes (chat, account, plans, conversations...) remain exactly as you have them.
# I've kept the main code clean and focused on the Login integration.

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        image_data = data.get("image", None)

        if not user_message and not image_data:
            return jsonify({"reply": "اكتب شيء أساعدك فيه"})

        if not SYSTEM_ENABLED:
            return jsonify({"reply": "⚠️ نظام المحادثات معطل حالياً. يرجى المحاولة لاحقاً."})

        if current_user.is_authenticated:
            user_id = current_user.id
            is_guest = False
        else:
            if 'guest_id' not in session:
                session.permanent = True
                session['guest_id'] = f"guest_{secrets.token_hex(8)}"
            user_id = session['guest_id']
            is_guest = True

        if current_user.is_authenticated:
            if current_user.email == "abdullaha0569361@gmail.com":
                is_admin = True
                user_plan = {'name': 'premium', 'daily_limit': 9999}
                can_chat = True
            else:
                is_admin = False
                user_plan = get_user_plan(current_user.id)
                if not user_plan:
                    user_plan = {'name': 'free', 'daily_limit': 5}
                can_chat, message = check_daily_limit(current_user.id)
                if not can_chat:
                    return jsonify({"reply": f"⚠️ {message}\n\n💡 انتهى حد المحادثات المجانية. للاستمرار والاستفادة من **البحث بالويب، تحليل الصور، الذكاء المتقدم والردود الأسرع**، يمكنك الترقية إلى خطتنا المدفوعة بقيمة 7 ريال شهرياً.", "limit_reached": True})
        else:
            is_admin = False
            user_plan = {'name': 'free', 'daily_limit': 9999}
            can_chat = True

        premium_trial = False
        if current_user.is_authenticated and user_plan.get('name') == 'free':
            daily_usage = get_daily_usage(current_user.id)
            if daily_usage <= 6:
                premium_trial = True

        if is_admin or (current_user.is_authenticated and user_plan.get('name') == 'premium') or premium_trial:
            model = "gpt-4o"
            use_web_search = True
            features = {"images": True}
        else:
            model = "gpt-4o-mini"
            use_web_search = False
            features = {"images": False}

        if image_data and not features["images"]:
            return jsonify({"reply": "📸 **تحليل وإنشاء الصور متاح فقط في الخطة المدفوعة.**\n\nللحصول على هذه الميزة، بالإضافة إلى **البحث في الويب والتحليل العميق والذكاء المتقدم**، يمكنك الترقية إلى خطة نبراس المدفوعة مقابل 7 ريال فقط شهرياً!"})

        if current_user.is_authenticated:
            add_message(str(user_id), "user", user_message)
            chat_history = get_history(str(user_id), limit=10)
        else:
            if 'guest_history' not in session:
                session['guest_history'] = []
            session['guest_history'].append({"role": "user", "content": user_message})
            chat_history = session['guest_history'][-10:]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for entry in chat_history:
            messages.append({"role": entry["role"], "content": entry["content"]})

        if image_data and features["images"]:
            messages.append({"role": "user", "content": [{"type": "text", "text": user_message or "حلل هذه الصورة"}, {"type": "image_url", "image_url": {"url": image_data}}]})

        if use_web_search and any(word in user_message for word in ["أخبار", "اليوم", "الآن", "جديد", "تحديث"]):
            try:
                print(f"🔍 محاولة البحث بالويب عن: {user_message}")
                search_response = client.responses.create(model="gpt-4o-mini", instructions=f"{SYSTEM_PROMPT}\n\nسياق المحادثة السابقة: {chat_history}", input=f"ابحث في الويب عن أحدث المعلومات حول: {user_message}، وقدم لي ملخصاً مفيداً.", tools=[{"type": "web_search"}], temperature=0.7, max_output_tokens=800)
                search_result = search_response.output_text.strip()
                if search_result:
                    messages.append({"role": "user", "content": f"نتيجة البحث عن '{user_message}':\n{search_result}\n\nاستخدم هذه المعلومات في ردك."})
                    print("✅ تم الحصول على نتائج البحث.")
            except Exception as e:
                print(f"⚠️ فشل البحث بالويب: {e}")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1000 if model == "gpt-4o" else 800,
            temperature=0.8
        )
        reply = response.choices[0].message.content.strip()
        if not reply:
            reply = "ما قدرت أجيب لك رد، حاول مرة أخرى."

        if current_user.is_authenticated:
            add_message(str(user_id), "assistant", reply)
        else:
            if 'guest_history' in session:
                session['guest_history'].append({"role": "assistant", "content": reply})

        if current_user.is_authenticated and not is_admin:
            increment_daily_usage(current_user.id)

        if premium_trial and current_user.is_authenticated:
            remaining = 6 - get_daily_usage(current_user.id)
            if remaining == 0:
                reply += "\n\n💎 انتهت محادثاتك التجريبية المميزة. يمكنك الترقية للاستمرار في استخدام النموذج المتقدم والبحث بالويب وتحليل الصور مقابل 7 ريال شهرياً."

        return jsonify({"reply": reply})

    except Exception as e:
        print(f"❌ خطأ في /chat: {e}")
        return jsonify({"error": str(e)}), 500

# ... (Baki routes like /account, /plans, /conversations, /export, /admin/settings remain exactly as your last working version) ...

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
