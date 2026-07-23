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
