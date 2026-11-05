import { expect, test } from "@playwright/test";

const ANSWER =
  "I owned the backend for CampusRide. I designed the FastAPI service, modelled the data in PostgreSQL and added Redis caching. That cut p95 latency from 420 ms to 260 ms. I tested the Redis failure path and checked cache hit rate in staging. The trade-off was consistency versus latency, so I invalidated on writes.";

test("student signs in, completes a three-round text interview and sees rubric feedback", async ({
  page,
}) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.getByRole("button", { name: "Continue as student" }).click();
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 60_000 });
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Hey");

  await page.goto("/dashboard/interviews");
  await expect(page.getByRole("heading", { name: "Mock interviews" })).toBeVisible();
  await expect(page.getByText("The rubric you will be scored on")).toBeVisible();

  await page.getByRole("button", { name: "Start a new interview" }).click();
  await page.getByRole("button", { name: "Enter the interview room" }).click();
  await expect(page).toHaveURL(/\/interview\/[a-f0-9-]+/, { timeout: 30_000 });

  await expect(page.getByTestId("question-bubble").first()).toBeVisible({ timeout: 45_000 });

  for (let index = 0; index < 14; index += 1) {
    const finish = page.getByTestId("finish-interview");
    if (await finish.isVisible().catch(() => false)) break;
    const input = page.getByTestId("answer-input");
    await expect(input).toBeEnabled({ timeout: 45_000 });
    await input.fill(`${ANSWER} Practice answer ${index + 1}.`);
    await page.getByTestId("send-answer").click();
    await page.waitForTimeout(500);
  }

  const finish = page.getByTestId("finish-interview");
  await expect(finish).toBeVisible({ timeout: 45_000 });
  await finish.click();

  await expect(page.getByTestId("scored-overlay")).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: "See my feedback" }).click();
  await expect(page).toHaveURL(/\/feedback$/, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Interview feedback" })).toBeVisible();
  await expect(page.getByText("Rubric feedback")).toBeVisible();
  await expect(page.getByText("Clarity").first()).toBeVisible();
  await expect(page.getByText(/median of three samples/i)).toBeVisible();
});
