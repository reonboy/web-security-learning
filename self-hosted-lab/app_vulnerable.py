from flask import Flask, request
import sqlite3

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

    conn = sqlite3.connect('users.db')
    cur = conn.cursor()

    # ★★★ わざと脆弱に書いている（入力を直接SQLに連結）★★★
    # ここに administrator'-- を撃つと、パスワードチェックが消えて突破できる
    query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
    cur.execute(query)
    user = cur.fetchone()
    conn.close()

    if user:
        return f"ログイン成功！ ようこそ {user[1]} さん"
    else:
        return "ログイン失敗"

if __name__ == '__main__':
    app.run(debug=True)
