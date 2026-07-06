from flask import Flask, render_template, jsonify, request, send_from_directory
import requests
import os
import json
import re
import subprocess
import sys

os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', os.path.join(os.path.dirname(__file__), '.browsers'))

app = Flask(__name__)

@app.after_request
def add_common_headers(resp):
    resp.headers['ngrok-skip-browser-warning'] = '1'
    return resp

API_KEY = 'ffc_mr541c7x_sk7uci9jspurahyu091v'
API_BASE = 'https://developers.freefirecommunity.com/api/v1'

REGIONS = ['SG', 'IND', 'BD', 'SG', 'ID', 'TH', 'TW', 'VN', 'BR', 'US']
NAMES_FILE = os.path.join(os.path.dirname(__file__), 'names.json')

def load_names():
    if os.path.exists(NAMES_FILE):
        try:
            with open(NAMES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_names(names):
    with open(NAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(names, f, ensure_ascii=False, indent=2)

def detect_region(uid):
    first = int(uid[0]) if uid and uid[0].isdigit() else 0
    return REGIONS[first % len(REGIONS)]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return send_from_directory(os.path.dirname(__file__), 'login.html')

@app.route('/api/lookup')
def api_lookup():
    uid = request.args.get('uid', '').strip()
    if not uid or len(uid) < 6 or not uid.isdigit():
        return jsonify({'error': 'UID không hợp lệ'}), 400
    first = detect_region(uid)
    for region in [first] + [r for r in REGIONS if r != first]:
        url = f'{API_BASE}/info?region={region}&uid={uid}&key={API_KEY}'
        try:
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'HaianhFFTool/1.0 (+https://haianh-ff-tool.onrender.com)'})
            if resp.status_code != 200:
                try:
                    err = resp.json()
                    if 'QUOTA' in err.get('code', ''):
                        return jsonify({'error': 'API Free Fire đã hết lượt trong tháng. Sẽ reset vào 1/8/2026.'}), 429
                except: pass
                continue
            try:
                data = resp.json()
            except ValueError:
                continue
            if data and 'basicInfo' in data:
                info = data['basicInfo']
                clan = data.get('clanBasicInfo', {}) or {}
                return jsonify({
                    'nickname': info.get('nickname', 'Không rõ'),
                    'level': info.get('level', 0),
                    'liked': info.get('liked', 0),
                    'guild': clan.get('clanName', 'Không có'),
                    'region': info.get('region', region),
                    'createAt': info.get('createAt', 0),
                    'lastLoginAt': info.get('lastLoginAt', 0)
                })
        except requests.exceptions.RequestException:
            continue
    return jsonify({'error': f'Không tìm thấy UID {uid} ở bất kỳ khu vực nào. Kiểm tra lại UID.'}), 404

@app.route('/api/check-name')
def api_check_name():
    name = request.args.get('name', '').strip().lower()
    if not name:
        return jsonify({'available': False, 'error': 'Thiếu tên'}), 400
    names = load_names()
    available = name not in [v.lower() for v in names.values()]
    return jsonify({'available': available})

@app.route('/api/get-name')
def api_get_name():
    email = request.args.get('email', '').strip().lower()
    names = load_names()
    name = names.get(email, '')
    return jsonify({'name': name})

@app.route('/api/set-name', methods=['POST'])
def api_set_name():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    name = str(data.get('name', '')).strip()
    if not email or '@' not in email:
        return jsonify({'error': 'Email không hợp lệ'}), 400
    if not name or len(name) < 2:
        return jsonify({'error': 'Tên phải có ít nhất 2 ký tự'}), 400
    names = load_names()
    for e, n in names.items():
        if n.lower() == name.lower() and e != email:
            return jsonify({'error': 'Tên đã được sử dụng'}), 400
    names[email] = name
    save_names(names)
    return jsonify({'success': True, 'name': name})

@app.route('/api/tiktok')
def api_tiktok():
    username = request.args.get('username', '').strip().replace('@', '')
    if not username:
        return jsonify({'error': 'Thiếu username'}), 400
    script = os.path.join(os.path.dirname(__file__), 'tiktok_scraper.py')
    try:
        result = subprocess.run(
            [sys.executable, script, username],
            capture_output=True, text=True, timeout=65,
            env={**os.environ, 'PLAYWRIGHT_BROWSERS_PATH': os.path.join(os.path.dirname(__file__), '.browsers')}
        )
        if result.returncode != 0:
            return jsonify({'error': f'Lỗi kết nối TikTok: {result.stderr.strip()[:100]}'}), 502
        data = json.loads(result.stdout)
        return jsonify(data)
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Lỗi kết nối TikTok: timeout'}), 502
    except json.JSONDecodeError:
        return jsonify({'error': 'Lỗi kết nối TikTok: response parse error'}), 502
    except Exception as e:
        return jsonify({'error': f'Lỗi kết nối TikTok: {str(e)[:100]}'}), 502

@app.route('/<path:filename>')
def static_files(filename):
    if filename in ('login.html', 'register.html', 'dashboard.html', 'firebase.js', 'freefire.html'):
        return send_from_directory(os.path.dirname(__file__), filename)
    return '', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
