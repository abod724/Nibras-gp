# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from functools import wraps
import json

app = Flask(__name__)
app.secret_key = 'nibras_secret_key_2026'  # غيّرها في الإنتاج

# ------------------- قاعدة بيانات وهمية -------------------
users_db = {
    'admin@nibras.com': '123456',
    'test@test.com': 'password'
}

# ------------------- ديكور حماية الصفحات -------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'email' not in session:
            flash('الرجاء تسجيل الدخول أولاً', 'warning')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

# ------------------- صفحات HTML (مضمنة) -------------------

# صفحة الدخول (تصميم احترافي مع تدرج وخلفية ضبابية)
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نبراس - دخول</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: 'Cairo', sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            padding: 20px;
        }
        .card {
            background: rgba(255,255,255,0.08);
            backdrop-filter: blur(14px);
            border-radius: 28px;
            padding: 45px 35px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 30px 60px -12px rgba(0,0,0,0.6);
            border: 1px solid rgba(255,255,255,0.12);
            text-align: center;
            color: #fff;
        }
        .card h1 { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
        .card .sub { color: #cbd5e1; margin-bottom: 30px; font-size: 15px; }
        .card .logo { font-size: 52px; margin-bottom: 8px; }
        .input-group {
            position: relative;
            margin-bottom: 22px;
            text-align: right;
        }
        .input-group input {
            width: 100%;
            padding: 14px 20px 14px 48px;
            border: none;
            border-radius: 40px;
            background: rgba(255,255,255,0.12);
            color: #fff;
            font-size: 16px;
            outline: none;
            transition: 0.3s;
            font-family: 'Cairo', sans-serif;
        }
        .input-group input::placeholder { color: #94a3b8; }
        .input-group input:focus {
            background: rgba(255,255,255,0.22);
            box-shadow: 0 0 0 3px rgba(99,102,241,0.3);
        }
        .input-group .icon {
            position: absolute;
            left: 18px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 20px;
            color: #94a3b8;
        }
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 40px;
            background: #6366f1;
            color: #fff;
            font-size: 19px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.3s;
            margin-top: 8px;
            font-family: 'Cairo', sans-serif;
        }
        .btn:hover { background: #4f46e5; transform: scale(1.02); box-shadow: 0 10px 25px -5px #4f46e5; }
        .footer { margin-top: 25px; font-size: 14px; color: #cbd5e1; }
        .footer a { color: #a5b4fc; text-decoration: none; font-weight: 700; }
        .footer a:hover { text-decoration: underline; }
        .flash-msg { background:#ef4444; color:#fff; padding:10px; border-radius:12px; margin-bottom:18px; font-size:14px; }
    </style>
</head>
<body>
<div class="card">
    <div class="logo">📚</div>
    <h1>نبراس</h1>
    <p class="sub">مرحباً بعودتك 👋</p>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, msg in messages %}
                <div class="flash-msg">{{ msg }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <form method="POST" action="{{ url_for('login') }}">
        <div class="input-group">
            <span class="icon">✉️</span>
            <input type="email" name="email" placeholder="البريد الإلكتروني" required>
        </div>
        <div class="input-group">
            <span class="icon">🔒</span>
            <input type="password" name="password" placeholder="كلمة المرور" required>
        </div>
        <button type="submit" class="btn">دخول</button>
    </form>
    <div class="footer">
        ليس لديك حساب؟ <a href="{{ url_for('signup_page') }}">سجل الآن</a>
    </div>
</div>
</body>
</html>
'''

# صفحة التسجيل
SIGNUP_HTML = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نبراس - تسجيل</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: 'Cairo', sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            padding: 20px;
        }
        .card {
            background: rgba(255,255,255,0.08);
            backdrop-filter: blur(14px);
            border-radius: 28px;
            padding: 45px 35px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 30px 60px -12px rgba(0,0,0,0.6);
            border: 1px solid rgba(255,255,255,0.12);
            text-align: center;
            color: #fff;
        }
        .card h1 { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
        .card .sub { color: #cbd5e1; margin-bottom: 30px; font-size: 15px; }
        .input-group {
            position: relative;
            margin-bottom: 22px;
            text-align: right;
        }
        .input-group input {
            width: 100%;
            padding: 14px 20px 14px 48px;
            border: none;
            border-radius: 40px;
            background: rgba(255,255,255,0.12);
            color: #fff;
            font-size: 16px;
            outline: none;
            transition: 0.3s;
            font-family: 'Cairo', sans-serif;
        }
        .input-group input::placeholder { color: #94a3b8; }
        .input-group input:focus {
            background: rgba(255,255,255,0.22);
            box-shadow: 0 0 0 3px rgba(99,102,241,0.3);
        }
        .input-group .icon {
            position: absolute;
            left: 18px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 20px;
            color: #94a3b8;
        }
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 40px;
            background: #10b981;
            color: #fff;
            font-size: 19px;
            font-weight: 700;
            cursor: pointer;
            transition: 0.3s;
            margin-top: 8px;
            font-family: 'Cairo', sans-serif;
        }
        .btn:hover { background: #059669; transform: scale(1.02); box-shadow: 0 10px 25px -5px #059669; }
        .footer { margin-top: 25px; font-size: 14px; color: #cbd5e1; }
        .footer a { color: #a5b4fc; text-decoration: none; font-weight: 700; }
        .footer a:hover { text-decoration: underline; }
        .flash-msg { background:#ef4444; color:#fff; padding:10px; border-radius:12px; margin-bottom:18px; font-size:14px; }
        .flash-success { background:#10b981; }
    </style>
</head>
<body>
<div class="card">
    <div class="logo">📚</div>
    <h1>حساب جديد</h1>
    <p class="sub">انضم إلى نبراس 🚀</p>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, msg in messages %}
                <div class="flash-msg {% if category=='success' %}flash-success{% endif %}">{{ msg }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <form method="POST" action="{{ url_for('signup') }}">
        <div class="input-group">
            <span class="icon">✉️</span>
            <input type="email" name="email" placeholder="البريد الإلكتروني" required>
        </div>
        <div class="input-group">
            <span class="icon">🔒</span>
            <input type="password" name="password" placeholder="كلمة المرور" required>
        </div>
        <div class="input-group">
            <span class="icon">✓</span>
            <input type="password" name="confirm" placeholder="تأكيد كلمة المرور" required>
        </div>
        <button type="submit" class="btn">تسجيل</button>
    </form>
    <div class="footer">
        لديك حساب؟ <a href="{{ url_for('login_page') }}">سجل دخول</a>
    </div>
</div>
</body>
</html>
'''

# صفحة المحادثة (التصميم الاحترافي اللي طلبته)
CHAT_HTML = '''
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نبراس - المحادثة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: 'Cairo', sans-serif;
            background: #e5ded8;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 15px;
        }
        .chat-container {
            width: 100%;
            max-width: 420px;
            height: 700px;
            background: #f0f2f5;
            border-radius: 28px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }
        .chat-header {
            background: #ffffff;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid #e9edef;
            flex-shrink: 0;
        }
        .chat-header .avatar {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #4f8cf7, #3b6ed9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-weight: 700;
            font-size: 18px;
        }
        .chat-header .info { flex:1; }
        .chat-header .info h3 { font-size:17px; font-weight:700; color:#111b21; }
        .chat-header .info span { font-size:13px; color:#667781; }
        .chat-header .action { color:#54656f; font-size:22px; cursor:default; }
        .chat-header .logout-btn {
            background: #ef4444;
            color: #fff;
            border: none;
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            font-family: 'Cairo', sans-serif;
            transition: 0.2s;
        }
        .chat-header .logout-btn:hover { background: #dc2626; }

        .chat-messages {
            flex: 1;
            padding: 18px 16px 10px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
            background: #efeae6;
            background-image: radial-gradient(#d1c7bd 0.8px, transparent 0.8px);
            background-size: 20px 20px;
        }
        .message {
            display: flex;
            flex-direction: column;
            max-width: 82%;
            animation: fadeIn 0.25s ease;
        }
        @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        .message.user { align-self: flex-end; align-items: flex-end; }
        .message.bot { align-self: flex-start; align-items: flex-start; }
        .message .bubble {
            padding: 10px 14px;
            border-radius: 16px;
            font-size: 15px;
            line-height: 1.6;
            word-wrap: break-word;
            box-shadow: 0 1px 2px rgba(0,0,0,0.08);
        }
        .message.user .bubble { background: #4f8cf7; color:#fff; border-bottom-right-radius:4px; }
        .message.bot .bubble { background: #ffffff; color:#111b21; border-bottom-left-radius:4px; }
        .message .sender { font-size:12px; font-weight:600; margin-bottom:3px; padding:0 4px; }
        .message.user .sender { color:#4f8cf7; }
        .message.bot .sender { color:#667781; }
        .message .time {
            font-size:11px;
            color:#8d9ba6;
            margin-top:4px;
            padding:0 6px;
            display:flex;
            align-items:center;
            gap:4px;
        }
        .message.user .time { justify-content:flex-end; }
        .message.bot .time { justify-content:flex-start; }
        .message.user .time .check { color:#53bdeb; font-size:14px; }

        .chat-input {
            background: #f0f2f5;
            padding: 10px 16px 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            border-top: 1px solid #e9edef;
            flex-shrink: 0;
        }
        .chat-input input {
            flex: 1;
            border: none;
            border-radius: 30px;
            padding: 12px 18px;
            font-size: 15px;
            font-family: 'Cairo', sans-serif;
            background: #ffffff;
            outline: none;
            transition: 0.2s;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .chat-input input:focus { box-shadow: 0 0 0 2px #4f8cf7; }
        .chat-input input::placeholder { color:#8d9ba6; }
        .chat-input button {
            background: #4f8cf7;
            border: none;
            color: #fff;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            font-size: 22px;
            cursor: pointer;
            transition: 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .chat-input button:hover { background:#3b6ed9; transform:scale(1.04); }
        .chat-input button:active { transform:scale(0.94); }
        .chat-messages::-webkit-scrollbar { width:4px; }
        .chat-messages::-webkit-scrollbar-track { background:transparent; }
        .chat-messages::-webkit-scrollbar-thumb { background:#c4c9cc; border-radius:10px; }

        /* رسالة ترحيب من السيرفر */
        .server-welcome {
            text-align:center;
            font-size:13px;
            color:#667781;
            padding:8px;
            background:rgba(0,0,0,0.04);
            border-radius:30px;
            margin:6px auto;
            width:fit-content;
        }
    </style>
</head>
<body>
<div class="chat-container">
    <div class="chat-header">
        <div class="avatar">ن</div>
        <div class="info">
            <h3>نبراس</h3>
            <span>متصل الآن</span>
        </div>
        <form method="POST" action="{{ url_for('logout') }}" style="margin:0;">
            <button type="submit" class="logout-btn">🚪 خروج</button>
        </form>
        <div class="action">⋯</div>
    </div>

    <div class="chat-messages" id="messagesContainer">
        <!-- الرسائل ستضاف بواسطة JS -->
    </div>

    <div class="chat-input">
        <input type="text" id="messageInput" placeholder="اكتب رسالة..." dir="rtl">
        <button id="sendBtn" aria-label="إرسال">➤</button>
    </div>
</div>

<script>
    // بيانات الرسائل الأولية (محاكاة المحادثة في الصورة)
    const initialMessages = [
        { sender: 'bot', name: 'نبراس', text: 'السالم عليكم', time: '10:28' },
        { sender: 'bot', name: 'نبراس', text: 'وعليكم السلام! كيف حالك؟ إن شاء الله بخير! وش الجديد عندك اليوم؟ عطني خبر!', time: '10:29' },
        { sender: 'user', name: '{{ session.get("name", "أنت") }}', text: 'وش الاخبار', time: '10:29' },
        { sender: 'bot', name: 'نبراس', text: 'الأخبار دايتم تتجدد، بس أنا هنا أساعدك بال معلومات اللي تحتاجها! إذا في موضوع معين تبني تعرف عنه أو حديث يجذبك، خبرني! سواء رياضة، تقنية، أو حتى مواضيع ثقافية. عطني العلم!', time: '10:29' }
    ];

    const container = document.getElementById('messagesContainer');
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');

    function addMessage(sender, name, text, time) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;

        const senderSpan = document.createElement('div');
        senderSpan.className = 'sender';
        senderSpan.textContent = name;

        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.textContent = text;

        const timeDiv = document.createElement('div');
        timeDiv.className = 'time';
        timeDiv.innerHTML = `${time} ${sender === 'user' ? '<span class="check">✓✓</span>' : ''}`;

        msgDiv.appendChild(senderSpan);
        msgDiv.appendChild(bubble);
        msgDiv.appendChild(timeDiv);
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;
    }

    // تحميل الرسائل الأولية
    initialMessages.forEach(msg => {
        addMessage(msg.sender, msg.name, msg.text, msg.time);
    });

    // إضافة رسالة ترحيب من السيرفر
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'server-welcome';
    welcomeDiv.textContent = '✨ مرحباً بك في نبراس - أنا هنا لمساعدتك';
    container.appendChild(welcomeDiv);

    function getCurrentTime() {
        const now = new Date();
        const h = String(now.getHours()).padStart(2, '0');
        const m = String(now.getMinutes()).padStart(2, '0');
        return `${h}:${m}`;
    }

    function sendMessage() {
        const text = input.value.trim();
        if (text === '') return;
        const time = getCurrentTime();

        // إرسال رسالة المستخدم
        addMessage('user', '{{ session.get("name", "أنت") }}', text, time);
        input.value = '';

        // محاكاة رد البوت
        setTimeout(() => {
            const botReplies = [
                'شكراً لك! 😊 هل تحتاج مساعدة في شيء معين؟',
                'فكرة رائعة! أخبرني المزيد عنها.',
                'تمام، أنا معك. كيف تقيم تجربتك مع نبراس؟',
                'ممتاز! سأبحث لك عن أفضل المعلومات بخصوص هذا الموضوع.',
                'حسناً، دعني أفكر في ذلك... نعم، لدي بعض الاقتراحات.',
                'أهلاً بك دائماً! كيف يمكنني مساعدتك اليوم؟'
            ];
            const randomReply = botReplies[Math.floor(Math.random() * botReplies.length)];
            const botTime = getCurrentTime();
            addMessage('bot', 'نبراس', randomReply, botTime);
        }, 700);
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });
    input.focus();
</script>
</body>
</html>
'''

# ------------------- Routes -------------------

@app.route('/')
def home():
    if 'email' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    if 'email' in session:
        return redirect(url_for('chat'))
    return render_template_string(LOGIN_HTML)

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    if email in users_db and users_db[email] == password:
        session['email'] = email
        session['name'] = email.split('@')[0]  # اسم المستخدم من البريد
        flash('تم تسجيل الدخول بنجاح!', 'success')
        return redirect(url_for('chat'))
    else:
        flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
        return redirect(url_for('login_page'))

@app.route('/signup', methods=['GET'])
def signup_page():
    if 'email' in session:
        return redirect(url_for('chat'))
    return render_template_string(SIGNUP_HTML)

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form.get('email')
    password = request.form.get('password')
    confirm = request.form.get('confirm')

    if not email or not password:
        flash('الرجاء ملء جميع الحقول', 'danger')
        return redirect(url_for('signup_page'))

    if password != confirm:
        flash('كلمة المرور غير متطابقة', 'danger')
        return redirect(url_for('signup_page'))

    if email in users_db:
        flash('هذا البريد مسجل مسبقاً', 'danger')
        return redirect(url_for('signup_page'))

    # حفظ المستخدم الجديد
    users_db[email] = password
    flash('تم إنشاء الحساب بنجاح! يمكنك الدخول الآن', 'success')
    return redirect(url_for('login_page'))

@app.route('/chat')
@login_required
def chat():
    return render_template_string(CHAT_HTML)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('login_page'))

# ------------------- تشغيل السيرفر -------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
