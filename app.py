from flask import Flask, request, jsonify, session
from openai import OpenAI
import os
import re
from datetime import datetime
import pytz
from duckduckgo_search import DDGS
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nibras_gt_secure_key_2026")

API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ OPENAI_API_KEY غير موجود")

client = OpenAI(api_key=API_KEY)

KNOWLEDGE_FILE = "knowledge.md"
knowledge_content = ""
if os.path.exists(KNOWLEDGE_FILE):
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge_content = f.read()
    except Exception:
        knowledge_content = ""
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
HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>نبراس GT</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#ffffff">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;min-height:100%;margin:0;padding:0;background:#fff;font-family:'Segoe UI',sans-serif;overscroll-behavior:none}
.app{min-height:100dvh;height:100dvh;max-width:750px;margin:0 auto;background:#fff;display:flex;flex-direction:column;position:relative;overflow:hidden}
.header{height:52px;min-height:52px;display:flex;align-items:center;justify-content:space-between;padding:0 20px;background:#fff;flex-shrink:0}
.header .icon-btn.left{width:20px;height:20px;border-radius:50%;border:1.5px solid #111827;background:transparent;color:#111827;font-size:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.2s ease}
.header .icon-btn.left:hover{background:#f3f4f6;transform:scale(1.08)}
.header .icon-btn.left:active{transform:scale(0.95)}
.header .icon-btn.right{width:26px;height:26px;border:none;background:transparent;color:#111827;font-size:17px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.2s ease;border-radius:8px}
.header .icon-btn.right:hover{background:#f3f4f6}
.dropdown{display:none;position:absolute;top:60px;right:16px;background:#fff;border-radius:11px;box-shadow:0 5px 18px rgba(0,0,0,0.06);padding:5px 0;width:160px;border:none;z-index:99;animation:dropShow 0.2s ease}
@keyframes dropShow{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
.dropdown.active{display:block}
.dropdown .item{padding:8px 15px;font-size:12px;display:flex;align-items:center;gap:8px;cursor:pointer;color:#1f2937;transition:all 0.15s ease;margin:2px 5px;border-radius:6px}
.dropdown .item:hover{background:#f9fafb;color:#005c99}
.chat-box{flex:1 1 auto;min-height:0;overflow-y:auto;padding:24px 18px;background:#f9fafb;display:flex;flex-direction:column;gap:14px}
.msg{max-width:78%;padding:12px 18px;border-radius:20px;font-size:15px;line-height:1.7;word-wrap:break-word;animation:fadeIn 0.25s ease}
.msg.user{background:linear-gradient(135deg,#0077b6,#005c99);color:white;align-self:flex-end;border-bottom-right-radius:6px}
.msg.bot{background:white;align-self:flex-start;border-bottom-left-radius:6px}
.msg .time{font-size:10px;color:#9ca3af;display:inline-block;margin-top:4px}
.msg.user .time{color:rgba(255,255,255,0.7)}
.typing{display:flex;gap:5px;background:white;padding:12px 18px;border-radius:20px;border-bottom-left-radius:6px;align-self:flex-start}
.typing span{width:8px;height:8px;background:#d1d5db;border-radius:50%;animation:bounce 1.2s infinite}
.typing span:nth-child(2){animation-delay:0.2s}
.typing span:nth-child(3){animation-delay:0.4s}
@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}
.input-bar{flex-shrink:0;background:white;padding:12px 18px max(18px, env(safe-area-inset-bottom));border-top:1px solid #f3f4f6;display:flex;gap:12px;align-items:center}
.input-bar .wrap{flex:1;display:flex;align-items:center;background:#f9fafb;border-radius:30px;padding:6px 16px;border:1px solid transparent;transition:all 0.2s ease}
.input-bar .wrap:focus-within{border-color:#005c99;background:white;box-shadow:0 0 0 3px rgba(0,92,153,0.06)}
.input-bar .wrap input{flex:1;border:none;background:transparent;padding:10px 8px;font-size:15px;outline:none;color:#111827}
.input-bar .wrap input::placeholder{color:#9ca3af}
.input-bar .wrap .icon-btn{background:none;border:none;font-size:18px;color:#6b7280;cursor:pointer;padding:6px;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;transition:all 0.15s ease}
.input-bar .wrap .icon-btn:hover{background:rgba(0,92,153,0.08);color:#005c99}
.input-bar .send-btn{background:linear-gradient(135deg,#0077b6,#005c99);color:white;border:none;border-radius:50%;width:42px;height:42px;min-width:42px;min-height:42px;font-size:18px;cursor:pointer;transition:all 0.2s ease;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,92,153,0.2)}
.input-bar .send-btn:disabled{background:#d1d5db;box-shadow:none}
.chat-image{max-width:160px;border-radius:12px;margin-top:6px}
::-webkit-scrollbar{width:5px;background:transparent}
::-webkit-scrollbar-thumb{background:#e5e7eb;border-radius:10px}
</style>
</head>
<body>
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
- يتفاعل مع كلام المستخدم ويعطي ردود فيها اهتمام بدون مبالغة

نبرة نبراس:
- ودّي، خفيف، مريح
- ما يستخدم كلمات عاطفية قوية مثل: يا عمري، يا حبيبي
- يستبدلها بعبارات طبيعية مثل: يا صاحبي، يا غالي، يا رجل، يا هلا فيك

إرشادات أساسية:
- يبدأ كلامه بترحيب لطيف: يا هلا ومرحبا يا غالي وش علومك اليوم أنا موجود إذا تبي نسولف
- إذا المستخدم فتح موضوع اجتماعي، يسترسل شوي: اسمع يا صاحبي، الدنيا تمشي، أهم شي تكون مرتاح، وش عندك اليوم؟
- إذا المستخدم سأل سؤال مباشر، يجاوب بوضوح ويشرح: خلني أفهمك، الموضوع كذا وكذا
- إذا الموضوع يحتاج بحث، يبحث ويجيب العلم الحديث بأسلوب سوالف
- يسأل المستخدم أسئلة خفيفة بدون مبالغة: وش وضعك هالأيام؟ تدرس؟ تشتغل؟ وش ناوي عليه؟
- يعطي كلام طبيعي بدون حساسية: أهم شي تكون بخير، وإذا عندك شي بخاطرك قول لي

تعليمات الكتابة:
- بدون علامات نهاية الجملة
- بدون نقاط
- بدون تعجب
- بدون ترقيم
- أسلوب سوالف طبيعي

تاريخ اليوم: {get_real_date()}
{('🔹 معلومات حديثة جلبتها لك:\n'+search_text) if search_text else ''}
"""
