import sqlite3
import hashlib

conn = sqlite3.connect('users.db')
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    password TEXT
)
''')

# パスワードをハッシュ化する関数
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ハッシュ化して保存
cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
            ('administrator', hash_password('admin123')))
cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
            ('wiener', hash_password('peter')))

conn.commit()
conn.close()
print("DB作成完了（ハッシュ化）")
