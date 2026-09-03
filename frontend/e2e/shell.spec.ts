import { expect, test } from "@playwright/test";

test("shows the analytics workspace", async ({ page }) => {
  await page.route("**/api/sessions", async (route) => route.fulfill({ json: { id: "demo-session" } }));
  await page.route("**/api/settings", async (route) => route.fulfill({ json: {
    database: null,
    default_provider: "openai",
    providers: [
      { provider: "openai", base_url: "https://api.openai.com/v1", model: "gpt-5-mini", timeout_seconds: 60, api_key_configured: false },
      { provider: "deepseek", base_url: "https://api.deepseek.com", model: "deepseek-chat", timeout_seconds: 60, api_key_configured: false },
      { provider: "qwen", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus", timeout_seconds: 60, api_key_configured: false }
    ]
  }}));
  await page.goto("/");
  await expect(page.getByText("DataPilot")).toBeVisible();
  await expect(page.getByRole("dialog", { name: "连接设置" })).toBeVisible();
});
