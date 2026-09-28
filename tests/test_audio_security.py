import importlib
import json
import sys
import threading
from contextlib import contextmanager
from functools import partial
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).parents[1] / 'vendor/skills/audio-production-pipeline/scripts'
sys.path.insert(0, str(SCRIPTS))


@contextmanager
def running(handler):
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    server.session_token = 'test-session'
    server.ai_jobs = {}
    server.args = SimpleNamespace(sheet_name='demo')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_credentials_are_scoped_and_stripped_on_cross_origin_redirect():
    api = importlib.import_module('company_audio_api')
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append((self.path, self.headers.get('Authorization')))
            if self.path == '/redirect':
                self.send_response(302)
                self.send_header('Location', redirect)
            else:
                self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')

        def log_message(self, *args):
            pass

    with running(Handler) as untrusted, running(Handler) as trusted:
        base = f'http://127.0.0.1:{trusted.server_port}'
        redirect = f'http://127.0.0.1:{untrusted.server_port}/external'
        api.download_bytes(base + '/trusted', 'secret', trusted_origins=[base])
        api.download_bytes(redirect, 'secret', trusted_origins=[base])
        api.download_bytes(base + '/redirect', 'secret', trusted_origins=[base])
    assert seen == [('/trusted', 'Bearer secret'), ('/external', None), ('/redirect', 'Bearer secret'), ('/external', None)]


def test_download_rejects_non_http(tmp_path):
    api = importlib.import_module('company_audio_api')
    secret = tmp_path / 'secret.txt'
    secret.write_text('secret')
    with pytest.raises(ValueError):
        api.download_bytes(secret.as_uri())


@pytest.fixture
def review_server(tmp_path):
    module = importlib.import_module('serve_review')
    prod = tmp_path / '.gdconfig_tmp/output/audio/production/demo'
    prod.mkdir(parents=True)
    (prod / 'company_library_review.html').write_text('review')
    (tmp_path / 'config.json').write_text('{"api_key":"secret"}')
    with running(partial(module.ReviewHandler, directory=str(tmp_path), workspace=tmp_path)) as server:
        yield server


def request(server, method, path, headers=None, body=None):
    connection = HTTPConnection('127.0.0.1', server.server_port)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


def test_review_static_scope_and_host(review_server):
    assert request(review_server, 'GET', '/.gdconfig_tmp/output/audio/production/demo/company_library_review.html')[0] == 200
    assert request(review_server, 'GET', '/config.json')[0] == 403
    assert request(review_server, 'HEAD', '/config.json')[0] == 403
    assert request(review_server, 'GET', '/')[0] == 403
    assert request(review_server, 'GET', '/api/session', {'Host': 'evil.example'})[0] == 403


def test_review_post_requires_origin_and_session(review_server):
    origin = f'http://127.0.0.1:{review_server.server_port}'
    for headers in [{}, {'Origin': origin}, {'Origin': 'https://evil.example', 'X-Review-Token': 'test-session'}]:
        assert request(review_server, 'POST', '/unknown', headers, '{}')[0] == 403
    status, headers, data = request(review_server, 'GET', '/api/session')
    assert status == 200
    assert json.loads(data)['token'] == 'test-session'
    assert 'Access-Control-Allow-Origin' not in headers
    headers = {'Origin': origin, 'X-Review-Token': 'test-session', 'Content-Type': 'application/json'}
    assert request(review_server, 'POST', '/unknown', headers, '{}')[0] == 404
    assert request(review_server, 'POST', '/api/production-package/build', headers, '{"sheet_name":"other"}')[0] == 400
