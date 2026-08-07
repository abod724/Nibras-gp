import os
import psycopg2
from psycopg2.extras import Json

# =====================================================================
# 📌 إعدادات الحدود اليومية (عدّل الأرقام هنا بسهولة)
# =====================================================================
FREE_PLAN_DAILY_LIMIT = 5       # الحد اليومي للخطة المجانية
PREMIUM_PLAN_DAILY_LIMIT = 9999 # الحد اليومي للخطة المدفوعة (غير محدود)
# =====================================================================

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL غير موجود في متغيرات البيئة")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """إنشاء جميع الجداول إذا لم تكن موجودة، وإدخال الخطط الافتراضية"""
    conn = get_connection()
    cur = conn.cursor()

    # ===== جدول المستخدمين =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            custom_daily_limit INT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ===== جدول المحادثات =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ===== جدول خطط الاشتراك =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            description TEXT,
            price DECIMAL(10, 2) DEFAULT 0,
            daily_limit INT DEFAULT 5,
            features JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ===== جدول اشتراكات المستخدمين =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            plan_id INTEGER REFERENCES plans(id),
            status VARCHAR(20) DEFAULT 'active',
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP,
            stripe_subscription_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ===== جدول الاستخدام اليومي =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_usage (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            usage_date DATE DEFAULT CURRENT_DATE,
            message_count INT DEFAULT 0,
            UNIQUE(user_id, usage_date)
        )
    """)

    # ===== إدخال الخطط الافتراضية (مجانية ومدفوعة) =====
    cur.execute("""
        INSERT INTO plans (name, description, price, daily_limit)
        VALUES ('free', 'خطة مجانية للاستخدام الأساسي', 0, %s)
        ON CONFLICT (name) DO NOTHING
    """, (FREE_PLAN_DAILY_LIMIT,))

    cur.execute("""
        INSERT INTO plans (name, description, price, daily_limit)
        VALUES ('premium', 'خطة مدفوعة بمميزات غير محدودة', 5.00, %s)
        ON CONFLICT (name) DO NOTHING
    """, (PREMIUM_PLAN_DAILY_LIMIT,))

    conn.commit()
    cur.close()
    conn.close()
    print("✅ تم تهيئة قاعدة البيانات بنجاح")

def execute_query(query, params=None):
    """تنفيذ استعلام (INSERT, UPDATE, DELETE)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

def fetch_all(query, params=None):
    """استرجاع جميع الصفوف من استعلام SELECT"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_one(query, params=None):
    """استرجاع صف واحد من استعلام SELECT"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row
