"""Password-protected loopback gateway for a separately managed HTTPS tunnel."""
import argparse
from collections import defaultdict, deque
import hashlib
import hmac
import http.client
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.parse import parse_qs, urlsplit

COOKIE = 'fba_remote_session'
LOGIN = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>林鸟标注 · 登录</title>
<style>body{margin:0;background:#121820;color:#e5edf4;font:16px/1.6 system-ui;display:grid;min-height:100dvh;place-items:center}
main{box-sizing:border-box;width:min(420px,100%);padding:28px}h1{font-size:25px}label{display:block;margin:24px 0 8px}
input,button{box-sizing:border-box;width:100%;font:inherit;padding:14px;border-radius:9px;border:1px solid #526678}
input{background:#1b2733;color:white}button{margin-top:18px;background:#9bd9c8;color:#102e29;font-weight:bold}
p{color:#a8bac8}.error{color:#ffb3a2}</style></head><body><main><h1>林鸟标注</h1>
<p>输入访问密码，继续审核 Z8 初标。<br>Enter the access password to review annotations.</p>
ERROR_MESSAGE<form method="post" action="/login"><label for="password">访问密码 / Password</label>
<input id="password" name="password" type="password" autocomplete="current-password" required maxlength="160">
<button type="submit">进入标注 / Sign in</button></form></main></body></html>'''


def create_gateway(config_path, port=8767, upstream_port=8765):
    config_path = Path(config_path)
    conf = json.loads(config_path.read_text(encoding='utf-8'))
    secret_hash = conf['password_sha256']
    sessions, attempts = {}, defaultdict(deque)
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = 'ForestBirdAccess/1.0'

        def log_message(self, fmt, *args):
            # No passwords, cookies, query strings or photo identifiers in access logs.
            pass

        def reply(self, status, body=b'', mime='text/html; charset=utf-8', extra=()):
            if isinstance(body, str):
                body = body.encode('utf-8')
            self.send_response(status)
            for key, value in extra:
                self.send_header(key, value)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'")
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        def error(self, status, message):
            self.reply(status, json.dumps({'error': message}), 'application/json; charset=utf-8')

        def host(self):
            value = self.headers.get('Host', '')
            current = json.loads(config_path.read_text(encoding='utf-8'))
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            allowed.update(current.get('public_hosts', []))
            return value if value in allowed else None

        def origin_ok(self, host):
            scheme = 'http' if host.startswith(('127.0.0.1:', 'localhost:')) else 'https'
            return self.headers.get('Origin') == f'{scheme}://{host}'

        def session(self):
            try:
                cookie = SimpleCookie(self.headers.get('Cookie', ''))
                token = cookie[COOKIE].value if COOKIE in cookie else ''
            except Exception:
                return None
            now = time.monotonic()
            with lock:
                for key in list(sessions):
                    if sessions[key] <= now:
                        del sessions[key]
                return token if sessions.get(token, 0) > now else None

        def payload(self, limit):
            if self.headers.get('Transfer-Encoding'):
                raise ValueError('Unsupported transfer encoding')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 <= size <= limit:
                raise ValueError('Request is too large')
            return self.rfile.read(size)

        def cookie(self, token, host, age=43200):
            return f'{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={age}' + (
                '' if host.startswith(('127.0.0.1:', 'localhost:')) else '; Secure')

        def do_GET(self): self.dispatch()
        def do_POST(self): self.dispatch()
        def do_PUT(self): self.dispatch()
        def do_HEAD(self): self.dispatch()

        def dispatch(self):
            try:
                host = self.host()
                if host is None:
                    return self.error(403, 'Unrecognized host')
                target = urlsplit(self.path)
                if target.scheme or target.netloc or self.path.startswith('//'):
                    return self.error(400, 'Invalid request path')
                path = target.path
                mutating = self.command in ('POST', 'PUT')
                if mutating and not self.origin_ok(host):
                    return self.error(403, 'Same-origin request required')
                if path == '/login':
                    if self.command in ('GET', 'HEAD'):
                        return self.reply(200, LOGIN.replace('ERROR_MESSAGE', ''))
                    if self.command != 'POST':
                        return self.error(405, 'Method not allowed')
                    if self.headers.get('Content-Type', '').split(';')[0] != 'application/x-www-form-urlencoded':
                        return self.error(415, 'Use the login form')
                    body = self.payload(4096)
                    now = time.monotonic()
                    # One gateway/one small review group. Global throttling cannot be bypassed by spoofing IP headers.
                    with lock:
                        recent = attempts['login']
                        while recent and recent[0] < now - 60:
                            recent.popleft()
                        if len(recent) >= 10:
                            return self.reply(429, 'Too many attempts. Please retry in one minute.', extra=[('Retry-After', '60')])
                    password = parse_qs(body.decode('utf-8')).get('password', [''])[0]
                    valid = hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), secret_hash)
                    if not valid:
                        with lock:
                            attempts['login'].append(now)
                        return self.reply(401, LOGIN.replace('ERROR_MESSAGE', '<p class="error">密码不正确 / Incorrect password</p>'))
                    token = secrets.token_urlsafe(32)
                    with lock:
                        if len(sessions) >= 100:
                            return self.error(429, 'Session limit reached')
                        sessions[token] = now + 43200
                    return self.reply(303, extra=[('Location', '/'), ('Set-Cookie', self.cookie(token, host))])
                token = self.session()
                if not token:
                    if path.startswith('/api/'):
                        return self.error(401, '登录已过期，请刷新页面重新登录。Your session expired; reload to sign in.')
                    return self.reply(303, extra=[('Location', '/login')])
                if path == '/logout' and self.command == 'POST':
                    with lock:
                        sessions.pop(token, None)
                    return self.reply(303, extra=[('Location', '/login'), ('Set-Cookie', self.cookie('', host, 0))])
                # Explicit route allowlist: no arbitrary file/proxy target, source paths or administrative shell.
                static = {'/', '/index.html', '/z8-review.html', '/z8-review.js', '/z8-review.css'}
                reads = (path in static or path in {'/api/health', '/api/z8-review/dataset', '/api/z8-review/schema', '/api/z8-review/export'}
                         or re.fullmatch(r'/api/z8-review/fb_\d{4,}(?:/history)?', path)
                         or re.fullmatch(r'/api/images/fb_\d{4,}(?:/(?:png|reference))?', path))
                writes = (self.command == 'PUT' and re.fullmatch(r'/api/z8-review/fb_\d{4,}', path)
                          or self.command == 'POST' and path == '/api/backup')
                if not ((self.command in ('GET', 'HEAD') and reads) or writes):
                    return self.error(404, 'Route not available through remote review access')
                body = self.payload(2 * 1024 * 1024) if mutating else None
                headers = {'Host': f'127.0.0.1:{upstream_port}'}
                if mutating:
                    headers['Content-Type'] = self.headers.get('Content-Type', '')
                connection = http.client.HTTPConnection('127.0.0.1', upstream_port, timeout=30)
                try:
                    connection.request('GET' if self.command == 'HEAD' else self.command, self.path, body=body, headers=headers)
                    response = connection.getresponse()
                    data = response.read()
                    if path == '/api/health' and response.status == 200:
                        health = json.loads(data)
                        health['remote_access'] = True
                        data = json.dumps(health).encode('utf-8')
                    extra = [(k, v) for k, v in response.getheaders() if k.lower() == 'content-disposition']
                    return self.reply(response.status, data, response.getheader('Content-Type', 'application/octet-stream'), extra)
                finally:
                    connection.close()
            except (ValueError, UnicodeError):
                self.error(400, 'Invalid request')
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self.error(502, '本机标注服务暂时不可用，请稍后重试。Annotation service unavailable.')

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--upstream-port', type=int, default=8765)
    args = parser.parse_args()
    create_gateway(args.config, args.port, args.upstream_port).serve_forever()


if __name__ == '__main__':
    main()
