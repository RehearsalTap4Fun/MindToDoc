const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.argv[3] === 'http' ? process.argv[2] : pathToFileURL(process.argv[2]).href);
    await page.waitForSelector('.event-item');
    assert.equal(await page.evaluate(() => safeUrl('ai_candidates/door open.wav')), 'ai_candidates/door%20open.wav');
    for (const unsafe of ['javascript:alert(1)', 'java\nscript:alert(1)', 'data:text/html,test', 'https://user:password@example.test/file']) {
      assert.equal(await page.evaluate(value => safeUrl(value), unsafe), '');
    }
    assert.equal(await page.evaluate(() => window.injected), undefined);
    assert.equal(await page.locator('#detail img').count(), 0);
    assert.equal(await page.locator('#detail a[href^="javascript:"]').count(), 0);
    assert.match(await page.locator('#detail h2').textContent(), /<img/);
    await page.locator('[data-candidate="candidate"][data-decision="best"]').click();
    assert.equal(await page.locator('.candidate.best').count(), 1);
    await page.locator('#notes').fill('</textarea><img src=x onerror="window.injected=4">');
    await page.reload();
    assert.equal(await page.evaluate(() => window.injected), undefined);
    assert.equal(await page.locator('#detail img').count(), 0);
    assert.match(await page.locator('#notes').inputValue(), /<img/);
    if (process.argv[3] === 'http') {
      const status = await page.evaluate(async () => {
        const response = await reviewFetch('/unknown', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
        return response.status;
      });
      assert.equal(status, 404, 'Authenticated POST must reach the router, not fail Origin/token validation');
    }
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
