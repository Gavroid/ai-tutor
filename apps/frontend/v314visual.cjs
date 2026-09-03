const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: true, args: ["--ignore-certificate-errors"] });
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  await page.setViewportSize({ width: 1280, height: 800 });

  // Login как qwe
  await page.goto("https://192.168.1.86/");
  await page.evaluate(async () => {
    await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "demo-center@example.com", password: "DemoCenter!2026" }),
    });
  });

  // Открываем /student/badges (qwe сейчас с 0 бейджами).
  await page.goto("https://192.168.1.86/student/badges");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2000);

  // Триггерим evaluate — выдаст несколько бейджей если есть attempts.
  // У qwe 87 attempts → должно выдать кучу бейджей.
  const evalBtn = page.getByRole("button", { name: /Проверить новые/i });
  await evalBtn.click();

  // Ждём toast
  const toast = page.locator('[data-testid="badge-toast"]');
  await toast.waitFor({ timeout: 10_000 });
  await page.waitForTimeout(400);

  // Screenshot toast в центре
  await page.screenshot({ path: "/tmp/v314_toast_center.png" });
  console.log("Toast captured");

  // Проверяем CTA ссылку
  const cta = page.locator('[data-testid="badge-toast-cta"]');
  const ctaHref = await cta.getAttribute("href");
  const ctaText = await cta.innerText();
  console.log("CTA href:", ctaHref);
  console.log("CTA text:", ctaText);

  // Проверяем что CTA кликабельная и ведёт на /student/badges
  // Кликаем и проверяем URL
  const urlBefore = page.url();
  await cta.click();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1500);
  const urlAfter = page.url();
  console.log("URL before click:", urlBefore);
  console.log("URL after click:", urlAfter);
  console.log("CTA WORKS:", urlAfter.includes("/student/badges"));

  await browser.close();
})();
