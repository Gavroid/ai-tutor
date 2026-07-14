import { test } from "@playwright/test";

test("debug admin tabs", async ({ page }) => {
  await page.goto("/login");
  await page.locator("input[type='email']").first().fill("admin@example.com");
  await page.locator("input[type='password']").first().fill("strongpass1");
  await page.getByRole("button", { name: /войти|вход/i }).click();
  await page.waitForLoadState("networkidle");
  await page.goto("/admin");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(3000);

  const allButtons = await page.locator("button").allTextContents();
  console.log("BUTTONS:", JSON.stringify(allButtons));

  const allText = await page.locator("body").textContent();
  console.log("BODY LENGTH:", allText?.length);
  console.log("CONTAINS 'Audit log':", allText?.includes("Audit log"));
  console.log("CONTAINS 'Users':", allText?.includes("Users"));
  console.log("CONTAINS 'Stats':", allText?.includes("Stats"));
  console.log("CONTAINS 'Tools':", allText?.includes("Tools"));
  console.log("CONTAINS 'Россия':", allText?.includes("Россия"));
});
