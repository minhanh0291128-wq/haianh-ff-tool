import sys, json, re, os
from playwright.sync_api import sync_playwright

username = sys.argv[1].replace('@', '')
pw = sync_playwright().start()
browser = pw.chromium.launch(
    headless=True,
    args=[
        '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--disable-setuid-sandbox', '--no-first-run', '--disable-extensions',
        '--disable-background-networking', '--disable-sync', '--mute-audio',
        '--js-flags=--max_old_space_size=256',
    ]
)
page = browser.new_page()
try:
    page.goto(f'https://www.tiktok.com/@{username}', wait_until='networkidle', timeout=30000)
    content = page.content()
    match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>', content)
    if not match:
        print(json.dumps({'error': 'Không thể lấy dữ liệu TikTok'}))
        sys.exit(1)
    data = json.loads(match.group(1))
    scope = data.get('__DEFAULT_SCOPE__', {})
    user_detail = scope.get('webapp.user-detail', {})
    if not user_detail or 'userInfo' not in user_detail:
        print(json.dumps({'error': 'Không tìm thấy user'}))
        sys.exit(1)
    info = user_detail['userInfo']
    user = info.get('user', {})
    stats = info.get('stats', {})
    print(json.dumps({
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
    }))
except Exception as e:
    print(json.dumps({'error': str(e)[:200]}))
    sys.exit(1)
finally:
    page.close()
    browser.close()
    pw.stop()
