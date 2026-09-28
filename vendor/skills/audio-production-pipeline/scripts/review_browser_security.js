// Data stays text; URL-bearing attributes accept only HTTP(S) and relative paths.
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
}

function safeUrl(value) {
  const raw = String(value ?? '').trim();
  if (!raw || /[\u0000-\u001f\\]/.test(raw)) return '';
  try {
    const url = new URL(raw, 'https://review.invalid/');
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? raw.replace(/ /g, '%20') : '';
  } catch { return ''; }
}

let reviewSession;
async function reviewFetch(url, options = {}) {
  const target = new URL(url, window.location.href);
  if (target.origin !== window.location.origin || !['http:', 'https:'].includes(target.protocol)) {
    throw new Error('请通过 serve_review.py 打开的本地页面提交操作。');
  }
  if ((options.method || 'GET').toUpperCase() === 'POST') {
    reviewSession ||= window.fetch('/api/session').then(async response => {
      if (!response.ok) throw new Error('无法取得本地评审会话，请刷新页面。');
      return (await response.json()).token;
    }).catch(error => { reviewSession = null; throw error; });
    options = {...options, headers: {...options.headers, 'X-Review-Token': await reviewSession}};
  }
  return window.fetch(target, options);
}
