import importlib.util
import json
import os
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest
from test_audio_security import review_server

ROOT = Path(__file__).parents[1]


def make_page(tmp_path):
    path = ROOT / 'vendor/skills/audio-production-pipeline/scripts/build_company_library_review_page.py'
    spec = importlib.util.spec_from_file_location('review_page', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = '</script><img src=x onerror="window.injected=1"><script>window.injected=2</script>'
    item = dict(request_id='test', event_name=payload, asset_name='safe', resource_bank=payload,
                candidates=[dict(candidate_id='candidate', filename=payload, match_score=90, duration_sec=1,
                                 download_url='javascript:window.injected=3', local_preview_url='', match_reasons=payload)],
                candidate_count=1, qualified_candidate_count=1, short_candidate_count=1, demand_tag='新增')
    output = tmp_path / 'review.html'
    module.write_page(output, [item], tmp_path / 'manifest.json', state_key='test-review')
    return output, payload


def test_manifest_cannot_close_script_element(tmp_path):
    output, payload = make_page(tmp_path)
    tags = []

    class Parser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            tags.append(tag)

    Parser().feed(output.read_text(encoding='utf-8'))
    assert tags.count('script') == 1
    assert 'img' not in tags
    assert json.loads((tmp_path / 'manifest.json').read_text(encoding='utf-8'))[0]['event_name'] == payload


@pytest.mark.skipif(not os.environ.get('AUDIO_REVIEW_NODE'), reason='Browser integration requires AUDIO_REVIEW_NODE and PLAYWRIGHT_MODULE')
def test_review_browser_escapes_data_and_keeps_controls_working(tmp_path):
    output, _ = make_page(tmp_path)
    result = subprocess.run([os.environ['AUDIO_REVIEW_NODE'], str(ROOT / 'tests/browser_audio_review.cjs'), str(output)], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(not os.environ.get('AUDIO_REVIEW_NODE'), reason='Browser integration requires AUDIO_REVIEW_NODE and PLAYWRIGHT_MODULE')
def test_browser_obtains_session_and_posts_to_configured_port(review_server):
    workspace = review_server.RequestHandlerClass.keywords['workspace']
    prod = workspace / '.gdconfig_tmp/output/audio/production/demo'
    make_page(prod)
    url = f'http://127.0.0.1:{review_server.server_port}/.gdconfig_tmp/output/audio/production/demo/review.html'
    result = subprocess.run([os.environ['AUDIO_REVIEW_NODE'], str(ROOT / 'tests/browser_audio_review.cjs'), url, 'http'], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
