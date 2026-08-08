import openai
import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ========== إعدادات OpenAI ==========
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY غير موجود!")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ========== إعدادات Ultramsg (واتساب) ==========
ULTRAMSG_TOKEN = os.environ.get("ULTRAMSG_TOKEN")
ULTRAMSG_INSTANCE = os.environ.get("ULTRAMSG_INSTANCE")

# ========== تحميل ملف المعرفة ==========
knowledge_content = ""
possible_names = ["Knowledge.md", "knowledge.md", "معرفة.md", "README.md"]
for filename in possible_names:
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                knowledge_content = f.read()
                break
        except:
            pass

if not knowledge_content:
    knowledge_content = "أنت نبراس، مساعد ودود."

# ========== تعليمات النظام ==========
SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد شخصي ودود تتحدث باللهجة العامية البيضاء.

**مصادر معرفتك:**
1. **ملف المعرفة** (أدناه) هو مرجعك الأساسي.
2. **معرفتك العامة**.

**ملف المعرفة الخاص بك:**
{knowledge_content}

**تعليمات مهمة:**
- إذا سألك المستخدم عن أي شيء، حاول الإجابة من ملف المعرفة أولاً.
- إذا لم تجد المعلومة، استخدم معرفتك العامة.
- دائماً حافظ على لهجتك العامية البيضاء والودية.
- اسأل المستخدم عن أحواله واهتم بحديثه.
- إذا لم تجد المعلومة، قل بصراحة "ما عندي علم".
- **لا تذكر أبداً أنك بوت**، وتحدث كما لو كنت صديقاً.
"""

# ========== نظام حفظ المحادثات ==========
CONVERSATIONS_FILE = "whatsapp_conversations.json"

def load_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_conversations(data):
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_memory(user_id):
    all_conv = load_conversations()
    return all_conv.get(str(user_id), [])

def save_user_memory(user_id, messages):
    all_conv = load_conversations()
    all_conv[str(user_id)] = messages
    save_conversations(all_conv)

# ========== دالة إرسال رسالة واتساب ==========
def send_whatsapp_message(to, message):
    if not ULTRAMSG_TOKEN or not ULTRAMSG_INSTANCE:
        print("⚠️ Ultramsg غير مهيأ")
        print(message)
        return
    
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": to,
        "body": message
    }
    try:
        requests.post(url, data=payload)
        print(f"✅ تم إرسال الرد إلى {to}")
    except Exception as e:
        print(f"❌ فشل إرسال الرسالة: {e}")

# ========== دالة الرد الرئيسية (مع GPT-5) ==========
def generate_reply(user_message, user_id):
    # تحميل تاريخ المحادثة
    conversation = get_user_memory(user_id)

    # إضافة رسالة المستخدم
    conversation.append({"role": "user", "content": user_message})
    chat_history = conversation[-15:]  # آخر 15 رسالة للسياق

    # بناء الرسائل
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for entry in chat_history:
        messages.append({"role": entry["role"], "content": entry["content"]})

    # استدعاء OpenAI باستخدام GPT-5
    try:
        response = client.chat.completions.create(
            model="gpt-5",  # ✅ تم التعديل هنا إلى GPT-5
            messages=messages,
            max_tokens=500,
            reasoning_effort="low",  # يقلل التكلفة (ميزة خاصة بـ GPT-5)
            temperature=0.8
        )
        reply = response.choices[0].message.content.strip()
        if not reply:
            reply = "ما قدرت أجيب لك رد، حاول مرة أخرى."
    except Exception as e:
        reply = f"❌ حدث خطأ: {e}"

    # حفظ الرد
    conversation.append({"role": "assistant", "content": reply})
    save_user_memory(user_id, conversation[-30:])  # احتفظ بآخر 30 رسالة

    return reply

# ========== نقاط نهاية Flask ==========
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error"}), 400

    user_message = data.get("body", "").strip()
    sender = data.get("from", "").strip()

    if not sender:
        return jsonify({"status": "error"}), 400

    print(f"📩 رسالة من {sender}: {user_message}")

    # توليد الرد
    reply = generate_reply(user_message, sender)

    # إرسال الرد
    send_whatsapp_message(sender, reply)

    return jsonify({"status": "success"})

@app.route("/", methods=["GET"])
def home():
    return "🤖 بوت نبراس (GPT-5) يعمل!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
