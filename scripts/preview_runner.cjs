// 无界面回放交互预演的全部场景，输出每个场景结束时的界面、弹窗与命中规则。
// 由 scripts/check_preview.py 调用：node scripts/preview_runner.cjs <预演.html>
'use strict';
const fs = require('fs');
const vm = require('vm');

function block(html, id) {
  const m = html.match(new RegExp('<script[^>]*\\bid="' + id + '"[^>]*>([\\s\\S]*?)</script>'));
  if (!m) throw new Error('缺少 <script id="' + id + '">');
  return m[1];
}

try {
  const html = fs.readFileSync(process.argv[2], 'utf8');
  const sandbox = {PREVIEW_DATA: JSON.parse(block(html, 'preview-data'))};
  if (/<script[^>]*\bid="preview-ui"/.test(html)) sandbox.PREVIEW_UI = JSON.parse(block(html, 'preview-ui'));
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(block(html, 'preview-engine'), sandbox, {filename: 'preview-engine'});
  vm.runInContext(block(html, 'preview-flow'), sandbox, {filename: 'preview-flow'});
  const out = {};
  for (const sc of sandbox.PREVIEW_DATA.scenarios || []) {
    try {
      out[sc.id] = sandbox.Preview.runScenario(sc.id);
    } catch (err) {
      out[sc.id] = {error: String(err && err.message || err)};
    }
  }
  // 每个界面与弹窗在默认状态下都能渲染，避免演示时才发现脚本错误或引用了未导出的图层。
  const rendered = sandbox.Preview._renderAll();
  const renderErrors = rendered.errors;
  process.stdout.write(JSON.stringify({scenarios: out, renderErrors, initial: rendered.initial,
    screens: rendered.screens, modals: rendered.modals}));
} catch (err) {
  process.stdout.write(JSON.stringify({fatal: String(err && err.message || err)}));
  process.exit(1);
}
