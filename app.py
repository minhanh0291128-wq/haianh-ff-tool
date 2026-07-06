from flask import Flask, render_template, jsonify, request, send_from_directory
import requests
import os
import json
import re
import asyncio
from playwright.async_api import async_playwright

# Ensure Playwright browsers path matches build.sh
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', os.path.join(os.path.dirname(__file__), '.browsers'))

app = Flask(__name__)

_pw = None
_browser = None

async def get_browser():
    global _pw, _browser
    if _browser is None:
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--no-first-run',
                '--disable-extensions',
                '--disable-background-networking',
                '--disable-sync',
                '--mute-audio',
                '--js-flags=--max_old_space_size=256',
            ]
        )
    return _browser

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

    tried_regions = set()
    first_region = detect_region(uid)

    for region in [first_region] + [r for r in REGIONS if r != first_region]:
        tried_regions.add(region)
        url = f'{API_BASE}/info?region={region}&uid={uid}&key={API_KEY}'
        try:
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code != 200:
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
    try:
        result = asyncio.run(_lookup_tiktok(username))
        return result
    except Exception as e:
        return jsonify({'error': f'Lỗi kết nối TikTok: {str(e)[:100]}'}), 502

async def _lookup_tiktok(username):
    page = None
    try:
        browser = await get_browser()
        page = await browser.new_page()
        await page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle', timeout=30000)
        content = await page.content()
        match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>', content)
        if not match:
            return jsonify({'error': 'Không thể lấy dữ liệu TikTok'}), 502
        data = json.loads(match.group(1))
        scope = data.get('__DEFAULT_SCOPE__', {})
        user_detail = scope.get('webapp.user-detail', {})
        if not user_detail or 'userInfo' not in user_detail:
            return jsonify({'error': 'Không tìm thấy user'}), 404
        info = user_detail['userInfo']
        user = info.get('user', {})
        stats = info.get('stats', {})
        return jsonify({
            'nickname': user.get('nickname', ''),
            'username': user.get('uniqueId', username),
            'avatar': user.get('avatarMedium', ''),
            'signature': user.get('signature', ''),
            'verified': user.get('verified', False),
            'private': user.get('privateAccount', False),
            'createdAt': user.get('createTime', 0),
            'followers': stats.get('followerCount', 0),
            'following': stats.get('followingCount', 0),
            'hearts': stats.get('heartCount', 0),
            'videos': stats.get('videoCount', 0)
        })
    except Exception as e:
        return jsonify({'error': f'Lỗi kết nối TikTok: {str(e)[:100]}'}), 502
    finally:
        if page:
            try: await page.close()
            except: pass

@app.route('/<path:filename>')
def static_files(filename):
    if filename in ('login.html', 'register.html', 'dashboard.html', 'firebase.js', 'freefire.html'):
        return send_from_directory(os.path.dirname(__file__), filename)
    return '', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
