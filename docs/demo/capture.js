// Captures pr-comment.png and the frames of pr-scroll.gif from the public
// demo PR, signed out. Usage: npm i playwright-core && node capture.js [dir]
// See README.md in this folder for turning the frames into the GIF.
const fs = require('fs');
const { chromium } = require('playwright-core');

const out = process.argv[2] || '.';
const SCROLL_STEPS = 10;

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 760 },
    deviceScaleFactor: 2,
    colorScheme: 'light',
  });
  await page.goto('https://github.com/EnXan/vipi-action-demo/pull/1', { waitUntil: 'networkidle' });
  const comment = page.locator('.timeline-comment', { hasText: 'VIPI scan:' });
  await comment.screenshot({ path: `${out}/pr-comment.png` });

  // Scroll from the top of the PR to the VIPI comment with ease-in-out steps.
  await page.evaluate(() => window.scrollTo(0, 0));
  const end = await comment.evaluate((element) => Math.min(
    element.getBoundingClientRect().top + window.scrollY - 70,
    document.documentElement.scrollHeight - window.innerHeight,
  ));
  fs.mkdirSync(`${out}/frames`, { recursive: true });
  for (let i = 0; i <= SCROLL_STEPS; i++) {
    const t = i / SCROLL_STEPS;
    const eased = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
    await page.evaluate((y) => window.scrollTo(0, y), Math.round(end * eased));
    await page.waitForTimeout(60);
    await page.screenshot({ path: `${out}/frames/f${String(i).padStart(3, '0')}.png` });
  }
  await browser.close();
})();
