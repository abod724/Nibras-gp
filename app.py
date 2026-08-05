# =============================================================
# نبراس - app.py
# نظام الخطط:
# 🆓 المجاني  -> GPT-5-mini بدون بحث ويب
# ⭐ المدفوع  -> GPT-5.2 مع بحث ويب
# =============================================================

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session

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

print("🔍 جارٍ قراءة المتغيرات...")

# =============================================================
# 🔑 OpenAI
# =============================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY غير موجود!")
    raise Exception("OPENAI_API_KEY غير موجود في متغيرات البيئة")
else:
    print("✅ OPENAI_API_KEY: موجود")

# =============================================================
# 🗄️ قاعدة البيانات
# =============================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL غير موجود!")
    raise Exception("DATABASE_URL غير موجود في متغيرات البيئة")
else:
    print("✅ DATABASE_URL: موجود")

# =============================================================
# 🔐 SECRET KEY
# =============================================================

SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    print("⚠️ SECRET_KEY غير موجود، سيتم استخدام القيمة الافتراضية")
    SECRET_KEY = "default-secret-key-change-in-production"
else:
    print("✅ SECRET_KEY: موجود")

app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(days=7)

# =============================================================
# 🚀 إعداد SQLAlchemy والجلسات
# =============================================================

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Session(db.Model):
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    data = db.Column(db.LargeBinary)
    expiry = db.Column(db.DateTime)


app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db
app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

sess = Session()
sess.init_app(app)

with app.app_context():
    db.create_all()

print("✅ تم تهيئة Flask-Session مع SQLAlchemy وإنشاء الجدول بنجاح!")

# =============================================================
# 🗄️ تهيئة قاعدة البيانات
# =============================================================

init_db()
print("✅ قاعدة البيانات جاهزة")

# =============================================================
# 🤖 OpenAI Client
# =============================================================

client = openai.OpenAI(api_key=OPENAI_API_KEY)
print("✅ OpenAI جاهز")

# =============================================================
# 🔐 تسجيل الدخول
# =============================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)


# =============================================================
# 📚 تحميل ملف المعرفة
# =============================================================

knowledge_content = ""

possible_names = [
    "Knowledge.md",
    "knowledge.md",
    "معرفة.md",
    "README.md",
    "ملف_المعرفة.md"
]

for filename in possible_names:
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                knowledge_content = f.read()

            print(f"✅ تم تحميل ملف المعرفة: {filename}")
            print(f"📄 أول 200 حرف من الملف: {knowledge_content[:200]}...")
            break

        except Exception as e:
            print(f"⚠️ خطأ في قراءة {filename}: {e}")


if not knowledge_content:
    knowledge_content = "أنت نبراس، مساعد ذكي."
    print("⚠️ لم يتم العثور على ملف معرفة، سيتم استخدام القيمة الافتراضية.")


# =============================================================
# 🧠 تعليمات نبراس
# =============================================================

SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد ذكي ورفيق درب لكل شخص يسولف معك.

لست مجرد بوت تقني جاف، بل شخصية حية، ذكية، سريعة البديهة، وتملك روحاً مرحة وحماسية.

**ملف المعرفة الخاص بك (مرجع أساسي):**
{knowledge_content}

استفد من ملف المعرفة بشكل ذكي عند الحاجة.

طريقة الكلام والأسلوب العامة:

- استخدم اللهجة السعودية البيضاء المفهومة والعفوية.
- كن ودودًا وقريبًا من المستخدم.
- لا تكن رسميًا بشكل مبالغ فيه.
- كن سريع البديهة ومفيدًا.
- استخدم عبارات طبيعية مثل:
  "يا سلام عليك!"
  "عطني العلم"
  "من عيوني"
  "أبشر"
  "هذا الشغل اللي يبرد الكبد!"

- تحدث كخوي حقيقي، وليس كروبوت جاف.

============================================================
🧠 حسب الخطة
============================================================

الخطة المجانية:
- تستخدم نموذج GPT-5-mini.
- لا تستخدم البحث في الويب.
- قدم أفضل إجابة ممكنة ضمن قدرات النموذج.
- إذا سأل المستخدم عن معلومات حديثة جدًا ولا يوجد بحث ويب في خطته، وضح له أن البحث في الويب متاح في الخطة المدفوعة.

الخطة المدفوعة:
- تستخدم نموذج GPT-5.2.
- يمكنها استخدام البحث في الويب عند الحاجة.
- يمكنها التعامل مع الصور إذا أرسل المستخدم صورة وكان الدعم متاحًا.
- قدم إجابات أعمق وأكثر دقة واستفد من قدرات النموذج.

============================================================
💬 أسلوب الحوار
============================================================

1. لا تستخدم الفصحى الثقيلة.
2. لا تكن مختصرًا بشكل مخل.
3. لا تكرر نفس الكلام.
4. افهم سياق المحادثة السابقة.
5. كن مبادرًا في الحوار.
6. عند الحاجة، اسأل المستخدم سؤالًا يساعد على إكمال المهمة.

============================================================
💎 الخطط المدفوعة
============================================================

عندما يسأل المستخدم عن الترقية أو الخطط المدفوعة:

- تحدث عن خطة نبراس فقط.
- لا تذكر خدمات خارجية.
- السعر الحالي للخطة المدفوعة هو 7 ريال شهريًا.
- من مميزات الخطة المدفوعة:
  بحث الويب، نموذج أقوى، تحليل الصور، ردود أسرع، تصدير المحادثات، ودعم أقوى.

لا تدّعي وجود ميزة غير مفعلة فعليًا في النظام.
"""


# =============================================================
# 🏠 الصفحة الرئيسية
# =============================================================

@app.route('/')
def index():
    resume_id = request.args.get('resume')

    if resume_id:
        session['resume_id'] = resume_id

    return render_template_string(HTML_TEMPLATE)


@app.route('/chat')
def chat_page():
    return render_template_string(HTML_TEMPLATE)


# =============================================================
# 🔐 تسجيل الدخول
# =============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        if check_password(email, password):

            user = get_user_by_email(email)

            login_user(user)

            return redirect(url_for('index'))

        return render_template_string(
            LOGIN_HTML,
            error="❌ بريد أو كلمة مرور خاطئة"
        )

    return render_template_string(
        LOGIN_HTML,
        error=""
    )


# =============================================================
# 📝 التسجيل
# =============================================================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')

        if get_user_by_email(email):

            return render_template_string(
                REGISTER_HTML,
                error="❌ البريد موجود مسبقاً"
            )

        create_user(email, password, name)

        return redirect(url_for('login'))

    return render_template_string(
        REGISTER_HTML,
        error=""
    )


# =============================================================
# 🚪 تسجيل الخروج
# =============================================================

@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect(url_for('index'))


# =============================================================
# 🔑 نسيت كلمة المرور
# =============================================================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    from database import execute_query

    if request.method == 'POST':

        email = request.form.get('email')

        user = get_user_by_email(email)

        if not user:

            return render_template_string(
                FORGOT_PASSWORD_HTML,
                error="❌ هذا البريد غير مسجل"
            )

        token = secrets.token_urlsafe(32)

        expiry = datetime.now() + timedelta(hours=1)

        execute_query(
            "UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE id = %s",
            (token, expiry, user.id)
        )

        reset_link = url_for(
            'reset_password',
            token=token,
            _external=True
        )

        return render_template_string(
            FORGOT_PASSWORD_HTML,
            success=f"✅ تم إرسال رابط إعادة التعيين: {reset_link}"
        )

    return render_template_string(
        FORGOT_PASSWORD_HTML,
        error=""
    )


# =============================================================
# 🔐 إعادة تعيين كلمة المرور
# =============================================================

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    from database import execute_query, fetch_one

    user = fetch_one(
        "SELECT id, email, reset_token_expiry FROM users WHERE reset_token = %s",
        (token,)
    )

    if not user:
        return "❌ الرابط غير صالح أو منتهي الصلاحية", 400

    user_id = user[0]
    expiry = user[2]

    if datetime.now() > expiry:
        return "❌ انتهت صلاحية الرابط، يرجى طلب رابط جديد", 400

    if request.method == 'POST':

        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:

            return render_template_string(
                RESET_PASSWORD_HTML,
                token=token,
                error="❌ كلمة المرور غير متطابقة"
            )

        hashed = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        execute_query(
            """
            UPDATE users
            SET password_hash = %s,
                reset_token = NULL,
                reset_token_expiry = NULL
            WHERE id = %s
            """,
            (hashed, user_id)
        )

        return redirect(url_for('login'))

    return render_template_string(
        RESET_PASSWORD_HTML,
        token=token,
        error=""
    )


# =============================================================
# 🌐 تحديد هل المستخدم طلب بحث ويب
# =============================================================

def user_requests_web_search(text):

    if not text:
        return False

    text = text.lower()

    search_words = [
        "ابحث",
        "ابحث لي",
        "ابحث عن",
        "من الإنترنت",
        "من الانترنت",
        "في الإنترنت",
        "في الانترنت",
        "مصادر",
        "المصدر",
        "مصادر موثوقة",
        "آخر الأخبار",
        "اخر الاخبار",
        "الأخبار",
        "الاخبار",
        "اليوم",
        "الآن",
        "الان",
        "حاليًا",
        "حاليا",
        "آخر تحديث",
        "اخر تحديث",
        "تحديث",
        "جديد",
        "الجديد",
        "سعر اليوم",
        "الأسعار اليوم",
        "الاسعار اليوم",
        "متى صدر",
        "ما الجديد"
    ]

    return any(word in text for word in search_words)


# =============================================================
# 💬 المحادثة الرئيسية
# =============================================================

@app.route('/chat', methods=['POST'])
def chat():

    try:

        data = request.get_json() or {}

        user_message = data.get("message", "").strip()

        image_data = data.get("image", None)

        if not user_message and not image_data:

            return jsonify({
                "reply": "اكتب شيء أساعدك فيه"
            })


        # =====================================================
        # 🔴 إيقاف النظام
        # =====================================================

        if not SYSTEM_ENABLED:

            return jsonify({
                "reply": "⚠️ نظام المحادثات معطل حالياً. يرجى المحاولة لاحقاً."
            })


        # =====================================================
        # 👤 تحديد المستخدم
        # =====================================================

        if current_user.is_authenticated:

            user_id = current_user.id
            is_guest = False

        else:

            if 'guest_id' not in session:

                session.permanent = True

                session['guest_id'] = (
                    f"guest_{secrets.token_hex(8)}"
                )

            user_id = session['guest_id']
            is_guest = True


        # =====================================================
        # 💎 تحديد الخطة
        # =====================================================

        if current_user.is_authenticated:

            # حساب المدير
            if current_user.email == "abdullaha0569361@gmail.com":

                is_admin = True

                user_plan = {
                    'name': 'premium',
                    'daily_limit': 9999
                }

                can_chat = True

            else:

                is_admin = False

                user_plan = get_user_plan(
                    current_user.id
                )

                if not user_plan:

                    user_plan = {
                        'name': 'free',
                        'daily_limit': 5
                    }

                can_chat, message = check_daily_limit(
                    current_user.id
                )

                if not can_chat:

                    return jsonify({
                        "reply":
                            f"⚠️ {message}\n\n"
                            "💡 يمكنك الترقية إلى الخطة المدفوعة للاستمرار.",
                        "limit_reached": True
                    })

        else:

            # الزائر يبقى مجاني
            is_admin = False

            user_plan = {
                'name': 'free',
                'daily_limit': 9999
            }

            can_chat = True


        # =====================================================
        # 🤖 تحديد النموذج حسب الخطة
        # =====================================================

        is_premium = (
            is_admin
            or (
                current_user.is_authenticated
                and user_plan.get('name') == 'premium'
            )
        )

        if is_premium:

            # ⭐ المدفوع
            model = "gpt-5.2"

            # 🌐 الويب متاح
            use_web_search = user_requests_web_search(
                user_message
            )

            print("💎 المستخدم Premium")
            print("🤖 النموذج: gpt-5.2")
            print(
                f"🌐 البحث: {'مفعل' if use_web_search else 'غير مطلوب'}"
            )

        else:

            # 🆓 المجاني
            model = "gpt-5-mini"

            # ❌ لا بحث ويب
            use_web_search = False

            print("🆓 المستخدم Free")
            print("🤖 النموذج: gpt-5-mini")
            print("🌐 البحث: معطل")


        # =====================================================
        # 🧠 تحميل الذاكرة
        # =====================================================

        if current_user.is_authenticated:

            add_message(
                str(user_id),
                "user",
                user_message
            )

            chat_history = get_history(
                str(user_id),
                limit=10
            )

        else:

            if 'guest_history' not in session:

                session['guest_history'] = []

            session['guest_history'].append({
                "role": "user",
                "content": user_message
            })

            chat_history = session[
                'guest_history'
            ][-10:]


        # =====================================================
        # 📨 تجهيز الرسائل
        # =====================================================

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

        for entry in chat_history:

            messages.append({
                "role": entry["role"],
                "content": entry["content"]
            })


        # =====================================================
        # 🖼️ الصورة
        # =====================================================

        if image_data:

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text":
                            user_message
                            or "حلل هذه الصورة"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data
                        }
                    }
                ]
            })


        # =====================================================
        # 🌐 بحث الويب للمستخدم المدفوع
        # =====================================================

        if use_web_search:

            try:

                print(
                    f"🔍 البحث بالويب عن: {user_message}"
                )

                search_response = client.responses.create(

                    model="gpt-5.2",

                    instructions=SYSTEM_PROMPT,

                    input=(
                        "ابحث في الويب عن المعلومات المتعلقة "
                        f"بطلب المستخدم التالي:\n\n"
                        f"{user_message}\n\n"
                        "استخدم مصادر حديثة وموثوقة، "
                        "ثم قدم المعلومات المهمة باختصار "
                        "مع ذكر المصادر عند توفرها."
                    ),

                    tools=[
                        {
                            "type": "web_search"
                        }
                    ]
                )

                search_result = (
                    search_response.output_text
                    or ""
                ).strip()

                if search_result:

                    messages.append({
                        "role": "user",
                        "content":
                            "نتائج البحث الحديثة من الويب:\n\n"
                            f"{search_result}\n\n"
                            "استخدم هذه النتائج للإجابة "
                            "عن سؤال المستخدم، ولا تخترع معلومات."
                    })

                    print(
                        "✅ تم الحصول على نتائج البحث."
                    )

            except Exception as e:

                print(
                    f"⚠️ فشل البحث بالويب: {e}"
                )

                # لا نوقف المحادثة إذا فشل البحث
                messages.append({
                    "role": "system",
                    "content":
                        "تعذر الوصول إلى البحث بالويب حالياً. "
                        "أجب اعتمادًا على معرفتك دون الادعاء "
                        "أنك بحثت في الإنترنت."
                })


        # =====================================================
        # 🤖 إرسال الطلب للنموذج
        # =====================================================

        if model == "gpt-5.2":

            # GPT-5.2
            response = client.chat.completions.create(

                model=model,

                messages=messages,

                max_completion_tokens=1500
            )

        else:

            # GPT-5-mini
            response = client.chat.completions.create(

                model=model,

                messages=messages,

                max_completion_tokens=1000
            )


        # =====================================================
        # 📝 استخراج الرد
        # =====================================================

        reply = (
            response.choices[0]
            .message
            .content
            or ""
        ).strip()


        if not reply:

            reply = (
                "ما قدرت أجيب لك رد حالياً، "
                "حاول مرة ثانية."
            )


        # =====================================================
        # 💾 حفظ الرد في الذاكرة
        # =====================================================

        if current_user.is_authenticated:

            add_message(
                str(user_id),
                "assistant",
                reply
            )

        else:

            if 'guest_history' in session:

                session['guest_history'].append({
                    "role": "assistant",
                    "content": reply
                })


        # =====================================================
        # 📊 تسجيل الاستخدام
        # =====================================================

        if current_user.is_authenticated and not is_admin:

            increment_daily_usage(
                current_user.id
            )


        # =====================================================
        # 📤 إرسال الرد
        # =====================================================

        return jsonify({
            "reply": reply,
            "plan": "premium" if is_premium else "free",
            "model": model,
            "web_search": use_web_search
        })


    except Exception as e:

        print(
            f"❌ خطأ في /chat: {e}"
        )

        return jsonify({
            "error": str(e)
        }), 500


# =============================================================
# 👤 الحساب
# =============================================================

@app.route('/account')
@login_required
def account():

    try:

        if current_user.email == "abdullaha0569361@gmail.com":

            plan = {
                'name': 'premium',
                'daily_limit': 9999
            }

            daily_usage = 0
            daily_limit = 9999
            remaining = 9999

        else:

            plan = get_user_plan(
                current_user.id
            )

            daily_usage = get_daily_usage(
                current_user.id
            )

            daily_limit = (
                plan.get('daily_limit', 5)
                if plan
                else 5
            )

            remaining = daily_limit - daily_usage


        html = f"""
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>حسابي - نبراس</title>

<style>

body{{
background:#f5f7fa;
padding:20px;
font-family:'Segoe UI',Arial,sans-serif
}}

.box{{
background:white;
border-radius:12px;
padding:20px;
box-shadow:0 2px 10px rgba(0,0,0,0.05);
max-width:400px;
margin:0 auto
}}

h2{{color:#1a2b3c}}

.info{{
margin:10px 0;
padding:8px 0;
border-bottom:1px solid #eaeef2
}}

.label{{
color:#6a7b8c;
font-size:14px
}}

.value{{
font-size:18px;
font-weight:bold;
color:#1a2b3c
}}

.badge{{
display:inline-block;
padding:4px 12px;
border-radius:30px;
font-size:14px
}}

.badge-free{{
background:#eef2f7;
color:#1a2b3c
}}

.badge-premium{{
background:#2d7d46;
color:white
}}

.back{{
display:inline-block;
margin-bottom:15px;
padding:8px 16px;
background:#4a6a8a;
color:white;
text-decoration:none;
border-radius:8px
}}

.upgrade-btn{{
display:block;
margin-top:20px;
padding:12px;
background:#2d7d46;
color:white;
text-align:center;
text-decoration:none;
border-radius:8px;
font-size:18px
}}

</style>
</head>

<body>

<a href="/" class="back">
⬅ العودة للرئيسية
</a>

<div class="box">

<h2>👤 حسابي</h2>

<div class="info">
<div class="label">الاسم</div>
<div class="value">{current_user.name}</div>
</div>

<div class="info">
<div class="label">البريد الإلكتروني</div>
<div class="value">{current_user.email}</div>
</div>

<div class="info">
<div class="label">الخطة الحالية</div>
<div class="value">
<span class="badge badge-{plan.get('name', 'free') if plan else 'free'}">
{plan.get('name', 'مجاني').upper() if plan else 'مجاني'}
</span>
</div>
</div>

<div class="info">
<div class="label">المحادثات اليومية</div>
<div class="value">
{daily_usage} / {daily_limit}
</div>
</div>

<div class="info">
<div class="label">
المحادثات المتبقية اليوم
</div>

<div class="value"
style="color:{'#2d7d46' if remaining > 0 else '#c33'}">

{remaining if remaining > 0 else 0}

</div>

</div>

<a href="/plans" class="upgrade-btn">
💎 عرض الخطط
</a>

</div>

</body>
</html>
"""

        return html


    except Exception as e:

        print(
            f"❌ خطأ في /account: {e}"
        )

        return (
            f"حدث خطأ: {str(e)}",
            500
        )


# =============================================================
# 💎 الخطط
# =============================================================

@app.route('/plans')
def plans():

    try:

        if current_user.is_authenticated:

            if current_user.email == "abdullaha0569361@gmail.com":

                plan = {
                    'name': 'premium',
                    'daily_limit': 9999
                }

            else:

                plan = get_user_plan(
                    current_user.id
                )

                if not plan:

                    plan = {
                        'name': 'free',
                        'daily_limit': 5
                    }


            html = f"""
<!DOCTYPE html>
<html dir="rtl" lang="ar">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>خطط نبراس</title>

<style>

body{{
background:#f5f7fa;
padding:20px;
font-family:'Segoe UI',Arial,sans-serif
}}

.container{{
max-width:500px;
margin:0 auto
}}

.back{{
display:inline-block;
margin-bottom:20px;
padding:8px 16px;
background:#4a6a8a;
color:white;
text-decoration:none;
border-radius:8px
}}

.plan{{
background:white;
border-radius:12px;
padding:20px;
margin-bottom:15px;
box-shadow:0 2px 10px rgba(0,0,0,0.05);
border-right:4px solid #4a6a8a
}}

.plan.premium{{
border-right-color:#f1c40f
}}

.plan h3{{
font-size:22px;
margin:0 0 5px 0;
color:#1a2b3c
}}

.plan .price{{
font-size:28px;
font-weight:bold;
color:#2d7d46
}}

.plan .price span{{
font-size:16px;
color:#6a7b8c
}}

.plan ul{{
margin:15px 0;
padding:0;
list-style:none
}}

.plan ul li{{
padding:6px 0;
border-bottom:1px solid #f0f2f5
}}

.btn{{
display:block;
padding:12px;
background:#4a6a8a;
color:white;
text-align:center;
text-decoration:none;
border-radius:8px;
font-size:18px;
margin-top:10px
}}

.btn.gold{{
background:#f1c40f;
color:#1a2b3c
}}

.badge{{
display:inline-block;
padding:4px 12px;
border-radius:30px;
font-size:14px;
background:#2d7d46;
color:white;
margin-bottom:10px
}}

.badge.free{{
background:#eef2f7;
color:#1a2b3c
}}

</style>

</head>

<body>

<div class="container">

<a href="/" class="back">
⬅ العودة للرئيسية
</a>

<h1 style="color:#1a2b3c;">
💎 خطط نبراس
</h1>

<p style="color:#6a7b8c;">
اختر الخطة التي تناسبك
</p>


<div class="plan">

<span class="badge free">
مجاني
</span>

<h3>
الخطة المجانية
</h3>

<div class="price">
0
<span>ر.س / شهرياً</span>
</div>

<ul>

<li>✅ GPT-5-mini</li>

<li>❌ بدون بحث ويب</li>

<li>✅ إجابات ذكية وسريعة</li>

<li>✅ مساعدة في المهام اليومية</li>

</ul>

<span style="
display:block;
text-align:center;
color:#6a7b8c;
padding:8px;
">

خطتك الحالية

</span>

</div>


<div class="plan premium">

<span class="badge">
مميز
</span>

<h3>
الخطة المدفوعة
</h3>

<div class="price">
7
<span>ر.س / شهرياً</span>
</div>

<ul>

<li>✅ GPT-5.2</li>

<li>✅ بحث الويب</li>

<li>✅ تحليل الصور</li>

<li>✅ إجابات أعمق وأقوى</li>

<li>✅ أولوية في المعالجة</li>

<li>✅ تصدير المحادثات</li>

<li>✅ دعم أقوى</li>

</ul>

<a href="#" class="btn gold">
💎 ترقية
</a>

</div>

</div>

</body>

</html>
"""

            return html


        else:

            html = """
<!DOCTYPE html>

<html dir="rtl" lang="ar">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>خطط نبراس</title>

<style>

body{
background:#f5f7fa;
padding:20px;
font-family:'Segoe UI',Arial,sans-serif
}

.container{
max-width:500px;
margin:0 auto
}

.box{
background:white;
border-radius:12px;
padding:30px;
text-align:center;
box-shadow:0 2px 10px rgba(0,0,0,0.05)
}

.btn{
display:inline-block;
padding:12px 24px;
background:#4a6a8a;
color:white;
text-decoration:none;
border-radius:8px;
font-size:18px;
margin-top:15px
}

.btn.green{
background:#2d7d46
}

</style>

</head>

<body>

<div class="container">

<div class="box">

<h1>
💎 خطط نبراس
</h1>

<p style="color:#6a7b8c;">

للوصول إلى الخطط المدفوعة والميزات المتقدمة،
يرجى تسجيل الدخول أو إنشاء حساب.

</p>

<a href="/login" class="btn">
🔐 تسجيل الدخول
</a>

<a href="/register" class="btn green">
📝 إنشاء حساب
</a>

</div>

</div>

</body>

</html>
"""

            return html


    except Exception as e:

        print(
            f"❌ خطأ في /plans: {e}"
        )

        return (
            f"حدث خطأ: {str(e)}",
            500
        )


# =============================================================
# 📋 المحادثات
# =============================================================

@app.route('/conversations')
@login_required
def view_conversations():

    try:

        user_id = str(current_user.id)

        rows = fetch_all(
            """
            SELECT id, role, content, created_at
            FROM conversations
            WHERE user_id = %s
            ORDER BY created_at ASC
            """,
            (user_id,)
        )

        if not rows:

            return """
            <h2 style='text-align:center;margin-top:50px;'>
            📭 لا توجد محادثات حتى الآن.
            </h2>
            """

        chapters = []

        current_chapter = []

        for row in rows:

            if row[1] == 'user' and len(current_chapter) >= 8:

                chapters.append(
                    current_chapter
                )

                current_chapter = [row]

            else:

                current_chapter.append(row)

        if current_chapter:

            chapters.append(
                current_chapter
            )


        html = """
<!DOCTYPE html>

<html dir="rtl" lang="ar">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>محادثاتي - نبراس</title>

<style>

body{
background:#f5f7fa;
padding:20px;
font-family:'Segoe UI',Arial,sans-serif
}

.back{
display:inline-block;
margin-bottom:20px;
padding:8px 16px;
background:#4a6a8a;
color:white;
text-decoration:none;
border-radius:8px
}

.chapter{
background:white;
border-radius:12px;
margin-bottom:12px;
box-shadow:0 2px 10px rgba(0,0,0,0.05);
overflow:hidden
}

.chapter-header{
padding:14px 20px;
background:#f8f9fa;
cursor:pointer;
display:flex;
justify-content:space-between;
align-items:center;
border-bottom:1px solid #eaeef2
}

.chapter-body{
padding:0 20px;
max-height:0;
overflow:hidden;
transition:max-height 0.4s ease,padding 0.3s ease
}

.chapter-body.open{
max-height:2000px;
padding:15px 20px
}

.msg-item{
display:flex;
gap:10px;
padding:6px 0;
border-bottom:1px solid #f0f2f5
}

.msg-role{
font-weight:bold;
min-width:60px
}

.msg-role.user{
color:#2d7d46
}

.msg-role.bot{
color:#4a6a8a
}

.msg-content{
flex:1;
word-break:break-word
}

.msg-time{
font-size:12px;
color:#999;
min-width:80px;
text-align:left
}

.actions{
margin-top:10px;
display:flex;
gap:10px
}

.actions a{
background:#4a6a8a;
color:white;
padding:5px 14px;
border-radius:20px;
text-decoration:none;
font-size:14px
}

</style>

</head>

<body>

<a href="/" class="back">
⬅ العودة للرئيسية
</a>

<h1>
📋 محادثاتي
</h1>

<div id="chapters-container">
"""

        for idx, chapter in enumerate(
            chapters,
            1
        ):

            title = f"المبحث {idx}"

            for row in chapter:

                if row[1] == 'user':

                    first_msg = row[2][:40]

                    title = (
                        f"المبحث {idx}: "
                        f"{first_msg}"
                    )

                    break

            msgs_html = ""

            for row in chapter:

                role_display = (
                    '👤 مستخدم'
                    if row[1] == 'user'
                    else '🤖 نبراس'
                )

                role_class = (
                    'user'
                    if row[1] == 'user'
                    else 'bot'
                )

                msgs_html += f"""
<div class="msg-item">

<span class="msg-role {role_class}">
{role_display}
</span>

<span class="msg-content">
{row[2][:300]}
</span>

<span class="msg-time">
{row[3]}
</span>

</div>
"""

            first_id = chapter[0][0]

            html += f"""
<div class="chapter">

<div class="chapter-header"
onclick="toggleChapter(this)">

<h3>
{title}
</h3>

<span class="arrow">
▼
</span>

</div>

<div class="chapter-body">

{msgs_html}

<div class="actions">

<a href="/?resume={first_id}">
▶️ مواصلة المحادثة
</a>

<a href="/export"
style="background:#2d7d46;">

📥 تصدير المحادثات

</a>

</div>

</div>

</div>
"""


        html += """
</div>

<script>

function toggleChapter(header){

var body = header.nextElementSibling;

var arrow = header.querySelector('.arrow');

if(body.classList.contains('open')){

body.classList.remove('open');

arrow.textContent = '▼';

}else{

body.classList.add('open');

arrow.textContent = '▲';

}

}

document.addEventListener(
'DOMContentLoaded',
function(){

var firstChapter =
document.querySelector(
'.chapter-header'
);

if(firstChapter){

toggleChapter(
firstChapter
);

}

});

</script>

</body>

</html>
"""

        return html


    except Exception as e:

        print(
            f"❌ خطأ في /conversations: {e}"
        )

        return (
            "<h2 style='text-align:center;"
            "margin-top:50px;color:#c33;'>"
            f"⚠️ حدث خطأ: {str(e)}"
            "</h2>",
            500
        )


# =============================================================
# 📥 تصدير المحادثات
# =============================================================

@app.route('/export')
@login_required
def export_conversations():

    user_id = str(
        current_user.id
    )

    rows = fetch_all(
        """
        SELECT role, content, created_at
        FROM conversations
        WHERE user_id = %s
        ORDER BY created_at ASC
        """,
        (user_id,)
    )

    data = [
        {
            "role": row[0],
            "content": row[1],
            "time":
                row[2].isoformat()
                if row[2]
                else None
        }
        for row in rows
    ]

    json_data = json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )

    return Response(
        json_data,
        mimetype='application/json',
        headers={
            'Content-Disposition':
                f'attachment; '
                f'filename=memory_{current_user.id}.json'
        }
    )


# =============================================================
# ⚙️ إعدادات المدير
# =============================================================

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():

    if current_user.email != "abdullaha0569361@gmail.com":

        return "غير مصرح", 403

    from database import execute_query, fetch_one

    global SYSTEM_ENABLED

    if request.method == 'POST':

        free_limit = int(
            request.form.get(
                'free_limit',
                5
            )
        )

        premium_limit = int(
            request.form.get(
                'premium_limit',
                9999
            )
        )

        system_enabled = (
            request.form.get(
                'system_enabled',
                'on'
            ) == 'on'
        )

        execute_query(
            """
            UPDATE plans
            SET daily_limit = %s
            WHERE name = 'free'
            """,
            (free_limit,)
        )

        execute_query(
            """
            UPDATE plans
            SET daily_limit = %s
            WHERE name = 'premium'
            """,
            (premium_limit,)
        )

        SYSTEM_ENABLED = system_enabled

        return redirect(
            url_for('admin_settings')
        )


    free_plan = fetch_one(
        "SELECT daily_limit FROM plans WHERE name = 'free'"
    )

    premium_plan = fetch_one(
        "SELECT daily_limit FROM plans WHERE name = 'premium'"
    )

    free_limit = (
        free_plan[0]
        if free_plan
        else 5
    )

    premium_limit = (
        premium_plan[0]
        if premium_plan
        else 9999
    )

    total_users = fetch_one(
        "SELECT COUNT(*) FROM users"
    )[0]

    today = datetime.now().date()

    today_chats = fetch_one(
        """
        SELECT COUNT(*)
        FROM conversations
        WHERE DATE(created_at) = %s
        """,
        (today,)
    )

    today_chats = (
        today_chats[0]
        if today_chats
        else 0
    )

    system_status_class = (
        "on"
        if SYSTEM_ENABLED
        else "off"
    )

    system_status_text = (
        "مفعل"
        if SYSTEM_ENABLED
        else "معطل"
    )


    html = f"""
<!DOCTYPE html>

<html dir="rtl" lang="ar">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>
إعدادات نظام المحادثات - نبراس
</title>

<style>

body{{
background:#f5f7fa;
padding:20px;
font-family:'Segoe UI',Arial,sans-serif
}}

.container{{
max-width:600px;
margin:0 auto
}}

.box{{
background:white;
border-radius:12px;
padding:25px;
box-shadow:0 2px 10px rgba(0,0,0,0.05)
}}

h2{{
color:#1a2b3c
}}

label{{
display:block;
margin:15px 0 5px 0;
color:#1a2b3c;
font-weight:bold
}}

input[type="number"]{{
width:100%;
padding:10px;
border:1px solid #dce1e8;
border-radius:8px;
font-size:16px
}}

input[type="checkbox"]{{
width:20px;
height:20px;
margin-right:10px
}}

button{{
background:#4a6a8a;
color:white;
border:none;
padding:12px 24px;
border-radius:8px;
font-size:18px;
cursor:pointer;
margin-top:20px
}}

.stat{{
display:inline-block;
margin:10px 15px 10px 0;
padding:10px 15px;
background:#f0f2f5;
border-radius:8px
}}

.stat span{{
font-weight:bold;
color:#1a2b3c
}}

.back{{
display:inline-block;
margin-bottom:15px;
padding:8px 16px;
background:#4a6a8a;
color:white;
text-decoration:none;
border-radius:8px
}}

.system-status{{
padding:10px;
border-radius:8px;
margin:10px 0
}}

.system-status.on{{
background:#d4edda;
color:#155724
}}

.system-status.off{{
background:#f8d7da;
color:#721c24
}}

</style>

</head>

<body>

<div class="container">

<a href="/" class="back">
⬅ العودة للرئيسية
</a>

<div class="box">

<h2>
⚙️ إعدادات نظام المحادثات
</h2>

<div class="stat">
👥 <span>{total_users}</span> مستخدم
</div>

<div class="stat">
💬 <span>{today_chats}</span> محادثة اليوم
</div>

<div class="system-status {system_status_class}">
✅ النظام {system_status_text}
</div>

<form method="POST">

<label>
حد الخطة المجانية
(عدد المحادثات اليومية)
</label>

<input
type="number"
name="free_limit"
value="{free_limit}"
min="1"
max="9999"
>

<label>
حد الخطة المدفوعة
(عدد المحادثات اليومية)
</label>

<input
type="number"
name="premium_limit"
value="{premium_limit}"
min="1"
max="9999"
>

<label>

<input
type="checkbox"
name="system_enabled"
{'checked' if SYSTEM_ENABLED else ''}
>

تفعيل نظام الحدود

</label>

<button type="submit">
💾 حفظ الإعدادات
</button>

</form>

</div>

</div>

</body>

</html>
"""

    return html


# =============================================================
# 🚀 تشغيل التطبيق
# =============================================================

if __name__ == '__main__':

    port = int(
        os.environ.get(
            'PORT',
            5000
        )
    )

    app.run(
        host='0.0.0.0',
        port=port
    )
