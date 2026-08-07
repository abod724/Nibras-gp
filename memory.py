from database import execute_query, fetch_all, fetch_one, init_db

# تهيئة قاعدة البيانات (إنشاء الجداول)
init_db()

def add_message(user_id, role, content):
    """إضافة رسالة جديدة للمستخدم"""
    execute_query(
        "INSERT INTO conversations (user_id, role, content) VALUES (%s, %s, %s)",
        (str(user_id), role, content)
    )
    trim_history(user_id)

def get_history(user_id, limit=10):
    """استرجاع آخر N رسائل للمستخدم (مرتبة من الأقدم للأحدث)"""
    rows = fetch_all(
        "SELECT role, content FROM conversations WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
        (str(user_id), limit)
    )
    history = [{"role": row[0], "content": row[1]} for row in rows]
    history.reverse()  # نرجعها من الأقدم للأحدث
    return history

def clear_memory(user_id):
    """مسح جميع محادثات المستخدم"""
    execute_query("DELETE FROM conversations WHERE user_id = %s", (str(user_id),))

def trim_history(user_id, max_len=20):
    """حذف أقدم الرسائل إذا تجاوز العدد 20"""
    execute_query("""
        DELETE FROM conversations 
        WHERE user_id = %s 
        AND id NOT IN (
            SELECT id FROM conversations 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        )
    """, (str(user_id), str(user_id), max_len))

def get_all_memories():
    """استرجاع إحصائيات المحادثات لجميع المستخدمين (للتشخيص)"""
    rows = fetch_all("SELECT user_id, COUNT(*) FROM conversations GROUP BY user_id")
    return {row[0]: row[1] for row in rows}

def get_session_count():
    """عدد المستخدمين النشطين (الذين لديهم محادثات)"""
    row = fetch_one("SELECT COUNT(DISTINCT user_id) FROM conversations")
    return row[0] if row else 0
