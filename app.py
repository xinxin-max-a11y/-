import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3

# 初始化Flask
app = Flask(__name__)
CORS(app)  # 支持跨域请求
app.config['UPLOAD_FOLDER'] = 'uploads'
@app.route('/')
def index():
    return jsonify({"message": "服务运行正常", "available_routes": ["/works", "/login", "/submit"]})
if not os.path.exists('uploads'):
    os.makedirs('uploads')


# ------------------ 数据库操作 ------------------
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')
    # 作品表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            image TEXT,
            category TEXT,
            reviewed INTEGER DEFAULT 0,
            score INTEGER,
            comment TEXT,
            recommended INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ------------------ 接口 ------------------

# 登录
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (username, password, role))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({'success': True, 'user': {'id': user['id'], 'username': user['username'], 'role': user['role']}})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'})

# 获取作品列表
@app.route('/works', methods=['GET'])
def get_works():
    recommended = request.args.get('recommended', 'true').lower() == 'true'
    conn = get_db()
    cursor = conn.cursor()
    if recommended:
        cursor.execute('SELECT * FROM works WHERE recommended=1')
    else:
        cursor.execute('SELECT * FROM works')
    works = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(works)

# 获取作品详情
@app.route('/work/<int:work_id>', methods=['GET'])
def get_work_detail(work_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM works WHERE id=?', (work_id,))
    work = cursor.fetchone()
    conn.close()
    if work:
        return jsonify(dict(work))
    else:
        return jsonify({'message': '作品不存在'}), 404

# 学生提交作品（新增 year）
@app.route('/submit', methods=['POST'])
def submit_work():
    user_id = request.form.get('userId')
    name = request.form.get('name')
    category = request.form.get('category')
    year = request.form.get('year')
    file = request.files.get('file')

    if not all([user_id, name, category, year, file]):
        return jsonify({'success': False, 'message': '参数缺失'})

    # 转整数
    try:
        year = int(year)
    except:
        return jsonify({'success': False, 'message': '年份必须为整数'})

    # 保存图片
    filename = f"{user_id}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 保存数据库（插入 year）
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO works (user_id, name, image, category, year) VALUES (?, ?, ?, ?, ?)
    ''', (user_id, name, filename, category, year))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# 老师评分
@app.route('/review/<int:work_id>', methods=['POST'])
def review_work(work_id):
    data = request.json
    score = data.get('score')
    comment = data.get('comment')
    recommended = 1 if data.get('recommended') else 0

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE works SET reviewed=1, score=?, comment=?, recommended=? WHERE id=?
    ''', (score, comment, recommended, work_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# 获取作品图片
@app.route('/uploads/<filename>')
def get_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ------------------ 启动 ------------------
if __name__ == '__main__':
    app.run(debug=True)