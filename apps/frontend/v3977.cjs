const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ["--ignore-certificate-errors", "--ignore-certificate-errors-spki-list"],
  });
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await ctx.newPage();

  await page.goto("https://192.168.1.86/login");
  await page.waitForTimeout(1500);
  await page.fill("#email", "admin@example.com");
  await page.fill("#password", "TmpAdmin!33ca0d07");
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2500);

  await page.goto("https://192.168.1.86/subjects");
  await page.waitForTimeout(3000);

  // Verify the review cards are in one row.
  const reviewInfo = await page.evaluate(() => {
    const grid = document.querySelector(".prism-review-row")?.parentElement;
    if (!grid) return { found: false };
    const cards = Array.from(grid.children);
    const cs = getComputedStyle(grid);
    const rows = {};
    cards.forEach((c) => {
      const top = Math.round(c.getBoundingClientRect().top);
      rows[top] = (rows[top] || 0) + 1;
    });
    return {
      found: true,
      gridTemplateColumns: cs.gridTemplateColumns,
      cardCount: cards.length,
      rowDistribution: rows,
    };
  });
  console.log("Review grid:", JSON.stringify(reviewInfo, null, 2));

  await page.screenshot({ path: "/tmp/v3977.png", fullPage: false });
  await browser.close();
})();
