import { expect, test, type Page } from "@playwright/test";

const STUDENT = {
  email: "kirill@example.com",
  password: "Kirill2026!",
};

async function loginAsStudent(page: Page): Promise<void> {
  await page.goto("/login");
  await page.locator("input[type='email'], input[name='email']").first().fill(STUDENT.email);
  await page.locator("input[type='password']").first().fill(STUDENT.password);
  await page.getByRole("button", { name: /войти|вход|логин/i }).first().click();
  await page.waitForLoadState("networkidle", { timeout: 15_000 });
}

test("session timer warning fits inside narrow lesson rail", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await loginAsStudent(page);

  await page.addInitScript(() => {
    const nativeSetInterval = window.setInterval.bind(window);
    const start = Date.now();
    let calls = 0;
    Date.now = () => {
      calls += 1;
      return calls === 1 ? start : start + 21 * 60_000;
    };
    window.setInterval = ((handler: TimerHandler, timeout?: number, ...args: unknown[]) => {
      return nativeSetInterval(handler, Math.min(Number(timeout) || 10, 10), ...args);
    }) as typeof window.setInterval;
  });

  await page.goto("/topics/187?timerMinutes=21");
  const warning = page.locator("[data-warning-level='1']");
  await expect(warning).toBeVisible({ timeout: 10_000 });

  const layout = await warning.evaluate((element) => {
    const panel = element.closest(".split-lesson") as HTMLElement | null;
    const warningRect = element.getBoundingClientRect();
    const panelRect = panel?.getBoundingClientRect();
    const overflowingDescendants = [...element.querySelectorAll<HTMLElement>("*")].filter(
      (node) => node.scrollWidth > node.clientWidth + 1,
    );
    const primary = element.querySelector("button") as HTMLElement | null;
    const primaryRect = primary?.getBoundingClientRect();
    return {
      withinPanel: panelRect
        ? warningRect.left >= panelRect.left - 1 && warningRect.right <= panelRect.right + 1
        : false,
      descendantOverflowCount: overflowingDescendants.length,
      primaryButtonHeight: primaryRect?.height ?? 0,
    };
  });

  expect(layout.withinPanel).toBe(true);
  expect(layout.descendantOverflowCount).toBe(0);
  expect(layout.primaryButtonHeight).toBeLessThanOrEqual(56);
});
