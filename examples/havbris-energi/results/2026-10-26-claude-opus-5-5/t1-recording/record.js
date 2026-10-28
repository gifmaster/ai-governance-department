const { chromium } = require('playwright');
(async () => {
  const dir = process.argv[2];
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir, size: { width: 1280, height: 720 } } });
  const p = await ctx.newPage();
  await p.goto('file://' + dir + '/replay.html');
  await p.waitForTimeout(500);
  const t0 = Date.now();
  await p.evaluate(() => window.__start());
  await p.waitForFunction(() => window.__done === true, null, { timeout: 200000, polling: 500 });
  console.log('scene seconds', (Date.now() - t0) / 1000);
  await ctx.close(); await b.close();
})();
