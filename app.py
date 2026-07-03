from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, make_response
import requests
import os
import json
import random
import string
import urllib.parse
from datetime import datetime

app = Flask(__name__)

@app.after_request
def add_ngrok_skip(resp):
    resp.headers['ngrok-skip-browser-warning'] = '1'
    return resp

API_KEY = 'ffc_mr541c7x_sk7uci9jspurahyu091v'
API_BASE = 'https://developers.freefirecommunity.com/api/v1'

REGIONS = ['SG', 'IND', 'BD', 'SG', 'ID', 'TH', 'TW', 'VN', 'BR', 'US']

# ===== TELEGRAM =====
TELEGRAM_BOT_TOKEN = '7668497719:AAGiSMsmqyAEjy-wKKJofk5ZVraluPZGMkg'
TELEGRAM_CHAT_ID = '6873788774'

# ===== BANK INFO =====
BANK_NAME = 'Vietcombank'
BANK_ACCOUNT = '1064516147'
BANK_HOLDER = 'NGUYEN HAI ANH'



ORDERS_FILE = os.path.join(os.path.dirname(__file__), 'orders.json')
BALANCE_FILE = os.path.join(os.path.dirname(__file__), 'balances.json')
NAMES_FILE = os.path.join(os.path.dirname(__file__), 'names.json')

def load_orders():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_orders(orders):
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

def load_balances():
    if os.path.exists(BALANCE_FILE):
        try:
            with open(BALANCE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_balances(balances):
    with open(BALANCE_FILE, 'w', encoding='utf-8') as f:
        json.dump(balances, f, ensure_ascii=False, indent=2)

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

def generate_order_code():
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=6))
    return f'HAFF-{suffix}'

def send_telegram(message):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def detect_region(uid):
    first = int(uid[0]) if uid and uid[0].isdigit() else 0
    return REGIONS[first % len(REGIONS)]

@app.route('/')
def index():
    return send_from_directory(os.path.dirname(__file__), 'login.html')

@app.route('/home')
def home():
    orders = load_orders()
    orders = expire_old_orders(orders)
    return render_template('index.html', orders_json=json.dumps(orders, ensure_ascii=False))

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

def expire_old_orders(orders):
    changed = False
    for o in orders:
        if o.get('status') == 'Chờ thanh toán':
            try:
                created = datetime.strptime(o['created_at'], '%d/%m/%Y %H:%M')
                if (datetime.now() - created).total_seconds() > 600:
                    o['status'] = 'Thất bại'
                    changed = True
            except:
                pass
    if changed:
        save_orders(orders)
    return orders

@app.route('/api/orders')
def api_orders():
    order_type = request.args.get('type', '')
    orders = load_orders()
    orders = expire_old_orders(orders)
    if order_type:
        if order_type == 'topup':
            orders = [o for o in orders if o.get('type') == 'topup' or (o.get('uid') == '000000' and not o.get('type'))]
        else:
            orders = [o for o in orders if o.get('type') == order_type]
    return jsonify({'orders': orders})

@app.route('/api/balance')
def api_balance():
    email = request.args.get('email', '').strip()
    balances = load_balances()
    bal = balances.get(email, 0)
    return jsonify({'balance': bal, 'email': email})


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

@app.route('/api/bank-info')
def api_bank_info():
    return jsonify({
        'bank': BANK_NAME,
        'account': BANK_ACCOUNT,
        'holder': BANK_HOLDER,
        'packages': PACKAGES
    })

@app.route('/api/order', methods=['POST'])
def api_order():
    data = request.get_json(silent=True) or {}
    uid = str(data.get('uid', '')).strip()
    package_id = str(data.get('package', '')).strip()
    nickname = str(data.get('nickname', '')).strip()
    order_type = str(data.get('type', '')).strip()

    if order_type != 'topup':
        if not uid or len(uid) < 6 or not uid.isdigit():
            return jsonify({'error': 'UID không hợp lệ'}), 400

    custom_price = data.get('custom_price')
    pkg = None
    if custom_price and isinstance(custom_price, (int, float)) and custom_price > 0:
        pkg = {'id': 'custom', 'likes': 0, 'price': int(custom_price), 'label': f'Nạp {int(custom_price):,}đ'}
    else:
        for p in PACKAGES:
            if p['id'] == package_id:
                pkg = p
                break
    if not pkg:
        return jsonify({'error': 'Gói không hợp lệ'}), 400

    code = generate_order_code()
    now = datetime.now().strftime('%d/%m/%Y %H:%M')

    order = {
        'code': code,
        'uid': uid,
        'nickname': nickname or 'Chưa rõ',
        'package': pkg['label'],
        'likes': pkg['likes'] if pkg['id'] != 'custom' else 0,
        'price': pkg['price'],
        'status': 'Chờ thanh toán',
        'type': order_type or 'like',
        'created_at': now
    }

    orders = load_orders()
    orders.insert(0, order)
    save_orders(orders)

    if order_type == 'topup' and nickname and '@' in nickname:
        balances = load_balances()
        balances[nickname] = balances.get(nickname, 0) + pkg['price']
        save_balances(balances)

    msg = (
        f'<b>🆕 ĐƠN HÀNG MỚI</b>\n'
        f'━━━━━━━━━━━━━\n'
        f'<b>Mã:</b> {code}\n'
        f'<b>UID:</b> {uid}\n'
        f'<b>Nick:</b> {order["nickname"]}\n'
        f'<b>Gói:</b> {pkg["label"]}\n'
        f'<b>Tiền:</b> {pkg["price"]:,}đ\n'
        f'<b>Lúc:</b> {now}\n'
        f'<b>Trạng thái:</b> ⏳ Chờ thanh toán'
    )
    send_telegram(msg)

    return jsonify({
        'success': True,
        'order': order
    })

@app.route('/<path:filename>')
def static_files(filename):
    if filename in ('login.html', 'register.html', 'dashboard.html', 'firebase.js', 'freefire.html'):
        return send_from_directory(os.path.dirname(__file__), filename)
    return '', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
