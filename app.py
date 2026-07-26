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

# ---------------------------------------------------------
# 🔥 بحث ويب فعلي (محسّن)
# ---------------------------------------------------------

def search_web(query):
    results = []

    # 1) DuckDuckGo
    try:
        ddg = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "kl": "ar-sa"},
            timeout=10
        ).json()

        txt = ddg.get("AbstractText") or ddg.get("Answer") or ""
        if txt:
            results.append(txt)
    except:
        pass

    # 2) Wikipedia API (يعطي نتائج عربية ممتازة)
    try:
        wiki = requests.get(
            "https://ar.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json"
            },
            timeout=10
        ).json()

        if "query" in wiki and wiki["query"]["search"]:
            snippet = wiki["query"]["search"][0]["snippet"]
            snippet = snippet.replace("<span class=\"searchmatch\">", "").replace("</span>", "")
            results.append(snippet)
    except:
        pass

    # لو كل شيء فشل
    if not results:
        return "لم يتم العثور على معلومات خارجية."

    return results[0]  # أفضل نتيجة

# ---------------------------------------------------------

SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد ودود ومتعاون لأهل السعودية والخليج.
تحدث باللهجة السعودية العامية الواضحة والطبيعية تماماً كإنسان حقيقي.
تفاعل مع المستخدم بكل رحابة صدر، جاوب على أسئلته، واطلب منه التفاصيل إن احتجت، واقترح عليه أمور مفيدة، واطرح عليه أسئلة لتبادل الحديث والفائدة.
لا تقل "لا أقدر أبحث"، أنت تحصل على معلومات حديثة تم جلبها لك عند الحاجة، وكذلك معلوماتك الخاصة، استخدمها بطريقتك الخاصة.

معلوماتك الخاصة:
{knowledge_content}
"""

@app.route('/')
def index():
    return render_template_string(""" 
    (واجهة HTML الأصلية بدون أي تغيير)
    """)

@app.route('/chat', methods=['POST'])
def chat():
    msg = request.json.get("m", "").strip()
    if not msg:
        return jsonify({"reply": "اكتب شيء أساعدك فيه"})

    # 🔥 الآن البحث يشتغل دائمًا
    search_result = search_web(msg)

    full_data = f"""
    السؤال: {msg}
    معلومات خارجية: {search_result}
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":full_data}
        ],
        temperature=0.8
    )

    return jsonify({"reply": res.choices[0].message.content.strip()})

if __name__ == '__main__':
    app.run(debug=False)
