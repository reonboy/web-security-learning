# 自作ラボ: SQLインジェクション と パスワード保護

Kali Linux + Flask + SQLite で作った、わざと脆弱なログインサイト。
「攻撃する側」と「守る側」の両方を、自分の手で体験するための箱庭。
作成日: 2026-11-02

> このラボは学習用。わざと脆弱に書いた部分がある。外部公開は絶対しないこと（localhost だけで動かす）。

---

## 構成ファイル

| ファイル | 役割 |
|---|---|
| `init_db.py` | DB（users.db）を作る。ユーザー2人を登録 |
| `app_vulnerable.py` | **脆弱版**。SQLi が刺さるログイン |
| `app.py` | **防御版**。プリペアドステートメント + パスワードのハッシュ化 |

動かし方:
```
python3 init_db.py      # DBを作る
python3 app.py          # サーバー起動（http://127.0.0.1:5000）
```

---

## 1. init_db.py（DBを作る）

```python
import sqlite3
import hashlib

conn = sqlite3.connect('users.db')      # DBファイルに接続（無ければ作られる）
cur = conn.cursor()                     # SQLを送る窓口（カーソル）

cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,             # 各行の背番号（自動）
    username TEXT,
    password TEXT
)
''')

def hash_password(password):            # パスワードをハッシュ化する関数
    return hashlib.sha256(password.encode()).hexdigest()

cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
            ('administrator', hash_password('admin123')))
cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
            ('wiener', hash_password('peter')))

conn.commit()                           # 変更を確定（これをしないと保存されない）
conn.close()
print("DB作成完了（ハッシュ化）")
```

### SQLの基本動詞
- `CREATE TABLE` … 表を作る
- `INSERT` … データを入れる
- `SELECT` … データを取り出す（ログインで使う）
- `UPDATE` … 更新 / `DELETE` … 削除

### できる表（ハッシュ化後）
```
id | username      | password（ハッシュ）
1  | administrator | 240be518fabd...（admin123のハッシュ）
2  | wiener        | 026ad9b14a74...（peterのハッシュ）
```
生のパスワード（admin123）は保存していない。ハッシュだけ。

---

## 2. app_vulnerable.py（脆弱版）— 攻撃される側

問題の行:
```python
query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
cur.execute(query)
```
**入力を `+` で直接つなげて SQL を組んでいる。** だから入力に含まれる `'` や `--` が「命令」として効いてしまう。

### 攻撃: SQLインジェクション
ログインフォームに:
```
ユーザー名: administrator'--
パスワード: （何でもいい）
```

クエリはこうなる:
```sql
SELECT * FROM users WHERE username = 'administrator'--' AND password = 'test'
                                                  ↑'で閉じる  ↑--で後ろ全部コメント
   ↓ 実質
SELECT * FROM users WHERE username = 'administrator'
```
パスワードチェック（AND password=...）が消え、**パスワードを知らなくても administrator でログインできる。**

**原理:** データのはずの入力が、SQLの「命令」として解釈された。= Never trust user input。

---

## 3. app.py（防御版）— 守る側

### 防御1: プリペアドステートメント（SQLi対策）
```python
query = "SELECT * FROM users WHERE username = ? AND password = ?"
cur.execute(query, (username, hashed))
```
`?` は「ここに値が入る」という**穴（プレースホルダー）**。値を別口で渡す。

- SQLの「構造」を先に確定（? の形で）
- 入力の「値」は後から、データとして流し込む
- → 入力に `'` や `--` が入っても「ただのデータ」扱い。命令として働かない

`administrator'--` を入れても「そんな変な名前のユーザーは居ない」で失敗する。

**キモ:** 構造（命令）と 値（データ）を混ぜない。これが注入系（SQLi, OSコマンド, XSS）共通の対策。

### 防御2: パスワードのハッシュ化
```python
hashed = hashlib.sha256(password.encode()).hexdigest()
```
- **ハッシュ化** = 元に戻せない変換。盗まれても元のパスワードが分からない
- **照合の仕組み**: 登録時も、ログイン時も、両方ハッシュ化して「ハッシュ同士」を比較
  - 同じ入力は必ず同じハッシュ → 元に戻さなくても本人確認できる
- **暗号化との違い**: 暗号化は鍵で戻せる（双方向）。ハッシュは戻せない（一方通行）。パスワードは戻せちゃダメなのでハッシュ

### 確認
- `wiener` / `peter` → 「ようこそ wiener さん」（正常は通る）
- `administrator'--` / 適当 → 「ログイン失敗」（攻撃は弾く）
- DBの中身（`sqlite3 users.db "SELECT * FROM users;"`）→ パスワードがハッシュになっている

---

## 4. さらに深い話（この日の深掘りメモ）

### SHA-256 では、実はまだ弱い
- SHA-256 は「速い」→ 攻撃者が1秒に何億回も試せる → 総当たりしやすい
- パスワード用のハッシュ（**bcrypt / argon2**）は、わざと「遅く」作られている
  - 正規ユーザー: ログイン1回だけ → 0.1秒は気づかない
  - 攻撃者: 何億回試す → 0.1秒 × 何億回 = 現実的に無理
- bcrypt はコスト（遅さ）を調整でき、マシンが速くなっても対抗できる

### レインボーテーブル攻撃 と ソルト
- **レインボーテーブル**: 「よくあるパスワード → そのハッシュ」の一覧表を事前に作り、盗んだハッシュと照合する攻撃
  - ソルトなしの SHA-256 はこれに弱い（admin123 → いつでも同じハッシュ）
- **ソルト（salt）**: パスワードにユーザーごとのランダム文字列を混ぜてからハッシュ化
  - 同じ admin123 でも、人ごとに違うハッシュになる → 一覧表が無力化される
  - 「事前計算」ができなくなるのがポイント
- **bcrypt はソルトを自動で付けてくれる**（$2b$12$<ソルト>... と、種類・コスト・ソルトがハッシュ内に書いてある）

### ハッシュの種類がバレても安全（重要な原理）
- 「種類を隠して守る」= security by obscurity = 弱い（パストラバーサル等で学んだのと同じ）
- 本物の対策は「バレても破れない仕組み」。bcrypt は種類を自分で公開しているくらい
- **ケルクホフスの原理**: 安全性は「仕組みの秘密」ではなく「鍵（パスワード）の秘密」だけに依存すべき
- 隠すのはパスワード本体だけ。仕組み（アルゴリズム）は公開でいい

### bcrypt + ソルトでも、まだ残る穴（多層防御）
ハッシュを正面から破るのは無理でも、攻撃は終わらない:
- 弱いパスワードの狙い撃ち（ユーザー側の問題 → パスワードポリシーも要る）
- ハッシュを破らない攻撃（フィッシング、総当たり、パスワード使い回し）
- ログイン以外の経路（パスワードリセット、セッション、2FA）
- 実装ミス（設定ミス、生パスワードをログ出力、等）

→ **1つの対策を完璧にしても、システム全体は守れない。攻撃者は一番弱いところを突く。**

---

## 次にやりたいこと（TODO）
- [ ] SHA-256 → bcrypt + ソルト にアップグレードして、違いを体感
- [ ] ログイン試行回数制限なし → Intruder で総当たりを実演
- [ ] 他の脆弱性（コマンドインジェクション, XSS など）も同じ箱庭で再現
