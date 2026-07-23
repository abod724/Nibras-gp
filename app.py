from flask import Flask, request, jsonify, session
from openai import OpenAI
import os, re, base64, pytz
from datetime import datetime
from duckduckgo_search import DDGS
from io import BytesIO
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nibras_gt_secure_key_2026")

API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ OPENAI_API_KEY غير موجود في صندوق الأسرار")

client = OpenAI(api_key=API_KEY)

def get_real_date():
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime("%A، %d %B %Y")

def clean_reply_from_links(reply):
    reply = re.sub(r'https?://\S+|www\.\S+', '', reply)
    reply = re.sub(r'[\[\(]?\s*[a-zA-Z0-9-]+\.(?:com|net|org|sa|gov|edu|me|news|tv|io|co|ly|info|online)\s*[\]\)]*', '', reply)
    reply = re.sub(r'\(\s*\)', '', reply)
    reply = re.sub(r'\[\s*\]', '', reply)
    reply = re.sub(r'\s{2,}', ' ', reply)
    reply = re.sub(r'[،.]\s*[،.]', '،', reply)
    reply = re.sub(r'\s+([،.])', r'\1', reply)
    return reply.strip()

def is_pure_date_question(prompt):
    p = prompt.strip().lower()
    pure_patterns = [
        r"^وش اليوم\??$", r"^ايش اليوم\??$", r"^كم التاريخ\??$", r"^شو التاريخ\??$",
        r"^اعطني التاريخ\??$", r"^تاريخ اليوم\??$", r"^اليوم كم\??$",
        r"^اليوم ايش\??$", r"^اليوم وش\??$", r"^كم تاريخ اليوم\??$", r"^شو تاريخ اليوم\??$",
        r"^ما هو تاريخ اليوم\??$", r"^ما هو اليوم\??$",
    ]
    for pattern in pure_patterns:
        if re.fullmatch(pattern, p):
            return True
    return False

def user_asks_for_sources(prompt):
    p = prompt.strip().lower()
    patterns = [
        r"نعم", r"ايه", r"اي", r"أيوا", r"أيوه", r"ابغاها", r"اريدها",
        r"المصدر", r"المصادر", r"الروابط", r"الرابط",
        r"عطني المصدر", r"وريني المصدر", r"من وين جبتها", r"من أين جبت هذا",
        r"المرجع", r"المراجع", r"الموقع", r"أظهر لي المصدر",
    ]
    for pat in patterns:
        if re.search(pat, p):
            return True
    return False

def MUST_SEARCH(prompt):
    p = prompt.strip().lower()
    force_patterns = [
        r"خبر|أخبار|حدث|ماذا حدث|وش صار|ايش صار|اللي صار|حادث|كارثة|إطلاق|تصريح|بيان|عاجل|مستجد|مستجدات|اخر الاخبار|اخر المستجدات",
        r"اليوم|هذا الأسبوع|هذا الشهر|هذه السنة|الآن|حاليا|حالي|آخر|أحدث|جديد|مؤخرا|اللحظة|لحظي|هسا|هذه الايام",
        r"202[4-9]|203",
        r"حرب|هجوم|قصف|اغتيال|انقلاب|ثورة|علاقات بين|مؤتمر|قمة|اتفاقية|عقوبات|تصعيد|هدنة|سياسي|وزير|رئيس|ملك|أمير|برلمان|حكومة|دولة|وزارة|نظام",
        r"مباراة|نتيجة|جدول|دوري|كأس|أبطال|المنتخب|لعب|فاز|خسر|بطولة|كأس العالم|الاندية|الشوط|هدف|ترتيب|موسم",
        r"سعر|سعر اليوم|كم يساوي|كم قيمة|سوق|أسهم|عملة|صرف|ذهب|نفط|بتكوين|عملات|أسعار|تضخم|بنك مركزي|ارتفاع|انخفاض",
        r"طقس|حرارة|درجة الحرارة|مطر|رياح|حالة الطقس|اعصار|غبار|رطوبة",
        r"فلم جديد|مسلسل جديد|موعد عرض|حلقة جديدة|مسلسل|فلم|حفل|مهرجان",
        r"موعد اختبار|موعد تسجيل|شروط القبول|تقديرات|نتائج الاختبارات|قبول|تسجيل|قرار جديد|قانون جديد|نظام جديد",
        r"ابحث لي|ابحث في|ابحث|تفقد لي|شوف لي|أريد معلومات عن|هل يوجد|تأكد لي|دقق لي|تحقق لي|فحص لي",
    ]
    for pat in force_patterns:
        if re.search(pat, p):
            return True
    return False

def search_web(query):
    sources = []
    text = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "", []
        sources = [{"title": r.get('title',''), "url": r.get('href',''), "body": r.get('body','')} for r in results]
        text = "\n".join(f"• {r.get('title','')}: {r.get('body','')[:180]}" for r in results)
    except Exception:
        pass
    return text, sources

system_prompt = f"""
نبراس يتكلم باللهجة السعودية العامية بأسلوب سوالف طبيعي، ودي، خفيف، ويطول شوي إذا الموضوع يحتاج. هدفه يخلي المستخدم يحس إنه يسولف مع شخص طبيعي بدون مبالغة في اللطافة أو العاطفة. نبراس يعطي حلول واقتراحات، ويساعد المستخدم بشكل عملي، ويتفاعل معه بطريقة مريحة.
تم تطويري وبرمجتي على يد مبرمجين ومطورين عالميين، ومهمتي إني أساعدك بأفضل شكل ممكن بدون ذكر أي معلومات عن المطورين بشكل شخصي.
قدرات نبراس:
- يفهم سياق الكلام
- إذا السؤال يحتاج معلومات حديثة، يستخدم البحث بالويب ويجيب العلم الواكد
- إذا السؤال واضح وما يحتاج بحث، يجاوب مباشرة
- يطرح حلول واقتراحات عملية للمستخدم
- يشرح ويفصّل إذا الموضوع يحتاج
- يتفاعل مع المستخدم بأسلوب طبيعي بدون مبالغة
أسلوب نبراس:
- لهجة سعودية بيضاء
- سوالف طبيعية بدون رسمية
- يطوّل شوي في الردود غير المباشرة
- يشرح ويفصّل إذا الموضوع يحتاج
- يستخدم عبارات يومية مثل: يا هلا، وش علومك، وش عندك، وش تبي نسولف عنه
نبرة نبراس:
- ودّي، خفيف، مريح
- ما يستخدم كلمات عاطفية قوية مثل: يا عمري، يا حبيبي
- يستبدلها بعبارات طبيعية مثل: يا صاحبي، يا غالي، يا رجل، يا هلا فيك
إرشادات أساسية:
- يبدأ كلامه بترحيب لطيف
- إذا المستخدم فتح موضوع اجتماعي، يسترسل شوي
- إذا المستخدم سأل سؤال مباشر، يجاوب بوضوح
تعليمات الكتابة:
- بدون علامات نهاية الجملة
- بدون نقاط
- بدون تعجب
- بدون ترقيم
تاريخ اليوم: {get_real_date()}
"""

@app.route("/api", methods=["POST"])
def api():
    data = request.json
    user_msg = data.get("message", "")
    images = data.get("images", [])

    if is_pure_date_question(user_msg):
        return jsonify({"reply": get_real_date()})

    search_text = ""
    sources = []
    session["last_had_search"] = False

    if MUST_SEARCH(user_msg):
        search_text, sources = search_web(user_msg)
        session["last_had_search"] = True

    try:
        if images:
            img = Image.open(BytesIO(base64.b64decode(images[0].split(',')[1])))
            buf = BytesIO()
            img.save(buf, 'JPEG')
            b64 = base64.b64encode(buf.getvalue()).decode()

            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_msg or "شوف لي الصورة دي"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        ]
                    }
                ],
                max_tokens=900,
                temperature=0.8
            )
        else:
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg or "هلا نبراس"}
                ],
                max_tokens=900,
                temperature=0.8
            )

        reply = clean_reply_from_links(res.choices[0].message.content.strip())

        if session.get("last_had_search"):
            reply += "\n💡 لو تبي المصادر قل لي"

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"⚠️ صار خطأ: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
