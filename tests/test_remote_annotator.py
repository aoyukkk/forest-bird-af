"""Remote access authenticates every image/API request and enforces browser origin."""
import hashlib
from http.client import HTTPConnection
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlencode

import test_annotator as helpers
from forest_bird_annotator.remote import create_gateway
from forest_bird_annotator.server import create_server


class RemoteAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        helpers.fixture(self.root / 'workspace')
        self.config = self.root / 'access.json'
        self.config.write_text(json.dumps({'password_sha256': hashlib.sha256(b'test-password').hexdigest(),
                                           'public_hosts': ['review-test.trycloudflare.com']}))
        self.origin = create_server(self.root / 'workspace', 0)
        self.gateway = create_gateway(self.config, 0, self.origin.server_port)
        for server in (self.origin, self.gateway):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
        self.port = self.gateway.server_port
        self.host = f'127.0.0.1:{self.port}'
        self.cookie = ''

    def tearDown(self):
        for server in (self.gateway, self.origin):
            server.shutdown()
            server.server_close()
        self.temp.cleanup()

    def request(self, path, method='GET', body=None, origin=None, host=None, cookie=True, mime='application/json'):
        headers = {'Host': host or self.host, 'Content-Type': mime}
        if cookie and self.cookie:
            headers['Cookie'] = self.cookie
        if origin:
            headers['Origin'] = origin
        conn = HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            conn.request(method, path, body, headers)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def login(self, host=None, origin=None):
        status, headers, body = self.request('/login', 'POST', urlencode({'password': 'test-password'}),
            origin or f'http://{self.host}', host, mime='application/x-www-form-urlencoded')
        self.assertEqual(status, 303)
        self.cookie = headers['Set-Cookie'].split(';')[0]
        return headers

    def test_unauthenticated_images_exports_and_api_never_reach_origin(self):
        for path in ('/api/images/fb_0001/png', '/api/images/fb_0001/reference',
                     '/api/z8-review/export?scope=all', '/api/z8-review/dataset'):
            self.assertEqual(self.request(path)[0], 401)
        self.assertEqual(self.request('/')[0], 303)
        self.assertEqual(self.request('/login')[0], 200)

    def test_login_cookie_host_origin_and_protected_reads(self):
        headers = self.login()
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        self.assertEqual(self.request('/api/health')[0], 200)
        self.assertTrue(json.loads(self.request('/api/health')[2])['remote_access'])
        self.assertEqual(self.request('/api/images/fb_0001/png')[0], 200)
        self.assertEqual(self.request('/api/health', host='attacker.example')[0], 403)
        for origin in (None, 'https://attacker.example'):
            self.assertEqual(self.request('/api/backup', 'POST', '{}', origin=origin)[0], 403)
        self.assertEqual(self.request('/api/import', 'POST', '{}', origin=f'http://{self.host}')[0], 404)

    def test_public_session_requires_secure_cookie_and_matching_https_origin(self):
        host = 'review-test.trycloudflare.com'
        headers = self.login(host, 'https://' + host)
        self.assertIn('; Secure', headers['Set-Cookie'])
        self.assertEqual(self.request('/api/health', host=host)[0], 200)
        self.assertEqual(self.request('/api/backup', 'POST', '{}', origin='http://' + host, host=host)[0], 403)

    def test_revisioned_draft_write_and_logout(self):
        self.login()
        status, _, raw = self.request('/api/z8-review/fb_0001')
        self.assertEqual(status, 200)
        current = json.loads(raw)
        current['review']['notes'] = 'Remote test draft'
        payload = json.dumps({'base_revision': current['revision'], 'review': current['review'],
                              'actor': {'id': 'remote-test', 'kind': 'ai'}, 'action': 'draft'})
        status, _, raw = self.request('/api/z8-review/fb_0001', 'PUT', payload, f'http://{self.host}')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['review']['status'], 'draft')
        self.assertEqual(self.request('/api/z8-review/fb_0001', 'PUT', payload, f'http://{self.host}')[0], 409)
        self.assertEqual(self.request('/logout', 'POST', '', f'http://{self.host}')[0], 303)
        self.assertEqual(self.request('/api/health')[0], 401)

    def test_bad_password_and_throttling(self):
        for _ in range(10):
            self.assertEqual(self.request('/login', 'POST', 'password=wrong', f'http://{self.host}',
                                         mime='application/x-www-form-urlencoded')[0], 401)
        self.assertEqual(self.request('/login', 'POST', 'password=wrong', f'http://{self.host}',
                                     mime='application/x-www-form-urlencoded')[0], 429)


if __name__ == '__main__':
    unittest.main()
