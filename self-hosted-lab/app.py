from flask import Flask, request
import sqlite3
import hashlib

app = Flask(__name__)

@app.route('/')
def home():
    return '''
        <h2>ログイン</h2>
        <form method="POST" action="/login">
            ユーザー名: <input name="username"><br>
            パスワード: <input name="password"><br>
            <button type="submit">ログイン</button>
        </form>
    '''

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # 入力パスワードをハッシュ化（DBにはハッシュが保存されているため）
    hashed = hashlib.sha256(password.encode()).hexdigest()

    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    # プリペアドステートメント（? のプレースホルダー）で SQLi を防ぐ
    query = "SELECT * FROM users WHERE username = ? AND password = ?"
    cur.execute(query, (username, hashed))
    user = cur.fetchone()
    conn.close()

    if user:
        return f"ログイン成功！ ようこそ {user[1]} さん"
    else:
        return "ログイン失敗"

if __name__ == '__main__':
    app.run(debug=True)
