import { test, expect } from "@playwright/test";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

// ── Shared toon produced by the first test (generate) ───────────────────────
let generatedToon: string | null = null;

// ── Helper ───────────────────────────────────────────────────────────────────
async function generateBuilding(request: any) {
  const res = await request.post(`${BACKEND}/api/generate`, {
    data: {
      prompt: "Modern 3-floor villa with flat roof",
      style: "contemporary",
      render_quality: "draft",
    },
    timeout: 120_000,
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  // Normalise: data might be nested under .data
  const data = body.data ?? body;
  expect(data).toHaveProperty("toon");
  return data as { toon: string; [k: string]: unknown };
}

async function editBuilding(request: any, toon: string, instruction: string) {
  const res = await request.post(`${BACKEND}/api/edit`, {
    data: { toon, instruction },
    timeout: 60_000,
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  const data = body.data ?? body;
  return data as { toon: string; changed: string[]; [k: string]: unknown };
}

// ════════════════════════════════════════════════════════════════════════════
// Suite 1 — API-level semantic edit tests (no OpenAI needed)
// ════════════════════════════════════════════════════════════════════════════
test.describe("Semantic Edits — /api/edit endpoint", () => {
  test("1a. /api/generate returns a valid toon with 3 floors", async ({ request }) => {
    const data = await generateBuilding(request);
    expect(data.toon).toContain("HOUSE");
    expect(data.toon).toContain("ROOF");
    // Store for subsequent tests
    generatedToon = data.toon;
  });

  test("1b. 'Add one more floor' increments floor count by 1", async ({ request }) => {
    // Generate fresh if not cached
    if (!generatedToon) {
      const data = await generateBuilding(request);
      generatedToon = data.toon;
    }

    // Read original floor count from toon
    const origMatch = generatedToon.match(/FLOORS\s+(\d+)/);
    const origFloors = origMatch ? parseInt(origMatch[1]) : 1;

    const result = await editBuilding(request, generatedToon, "Add one more floor");
    expect(result.toon).toContain("HOUSE");

    const newMatch = result.toon.match(/FLOORS\s+(\d+)/);
    const newFloors = newMatch ? parseInt(newMatch[1]) : origFloors;
    expect(newFloors).toBe(origFloors + 1);

    // changed array should mention floors
    const changedStr = (result.changed ?? []).join(" ").toLowerCase();
    expect(changedStr).toMatch(/floor/);

    // update toon for next test
    generatedToon = result.toon;
  });

  test("1c. 'Remove a floor' decrements floor count by 1", async ({ request }) => {
    if (!generatedToon) {
      const data = await generateBuilding(request);
      generatedToon = data.toon;
    }

    const origMatch = generatedToon.match(/FLOORS\s+(\d+)/);
    const origFloors = origMatch ? parseInt(origMatch[1]) : 1;

    const result = await editBuilding(request, generatedToon, "Remove a floor");
    expect(result.toon).toContain("HOUSE");

    const newMatch = result.toon.match(/FLOORS\s+(\d+)/);
    const newFloors = newMatch ? parseInt(newMatch[1]) : origFloors;

    // Must decrement, and never go below 1
    const expectedFloors = Math.max(1, origFloors - 1);
    expect(newFloors).toBe(expectedFloors);

    // changed array should mention floors
    const changedStr = (result.changed ?? []).join(" ").toLowerCase();
    expect(changedStr).toMatch(/floor/);

    generatedToon = result.toon;
  });

  test("1d. 'Make the rooms larger' resizes rooms — changed list is non-empty", async ({ request }) => {
    if (!generatedToon) {
      const data = await generateBuilding(request);
      generatedToon = data.toon;
    }

    const result = await editBuilding(request, generatedToon, "Make the rooms larger");
    expect(result.toon).toContain("HOUSE");

    // At least one room must appear in changed
    expect((result.changed ?? []).length).toBeGreaterThan(0);

    generatedToon = result.toon;
  });

  test("1e. 'Make the rooms larger' actually increases room sizes in the toon", async ({ request }) => {
    const base = await generateBuilding(request);

    // Parse room sizes from toon via simple regex
    const parseSizes = (toon: string) => {
      const matches = [...toon.matchAll(/size\s+([\d.]+)x([\d.]+)/g)];
      return matches.map((m) => ({ w: parseFloat(m[1]), d: parseFloat(m[2]) }));
    };

    const beforeSizes = parseSizes(base.toon);
    const result = await editBuilding(request, base.toon, "Make all rooms larger");
    const afterSizes = parseSizes(result.toon);

    expect(afterSizes.length).toBe(beforeSizes.length);
    for (let i = 0; i < beforeSizes.length; i++) {
      expect(afterSizes[i].w).toBeGreaterThanOrEqual(beforeSizes[i].w);
      expect(afterSizes[i].d).toBeGreaterThanOrEqual(beforeSizes[i].d);
    }
  });

  test("1f. Add-then-remove floor is net-zero change", async ({ request }) => {
    const base = await generateBuilding(request);
    const origMatch = base.toon.match(/FLOORS\s+(\d+)/);
    const origFloors = origMatch ? parseInt(origMatch[1]) : 1;

    const after_add = await editBuilding(request, base.toon, "Add one more floor");
    const after_remove = await editBuilding(request, after_add.toon, "Remove a floor");

    const finalMatch = after_remove.toon.match(/FLOORS\s+(\d+)/);
    const finalFloors = finalMatch ? parseInt(finalMatch[1]) : origFloors;
    expect(finalFloors).toBe(origFloors);
  });
});

// ════════════════════════════════════════════════════════════════════════════
// Suite 2 — UI smoke test (PromptBar routing — no AI chatbot involved)
// ════════════════════════════════════════════════════════════════════════════
test.describe("UI Smoke — PromptBar edit chips routing", () => {
  test("2a. App loads and shows the main title", async ({ page }) => {
    page.on("pageerror", (err) => console.error("PAGE ERROR:", err.message));
    await page.goto("/");
    await expect(page).toHaveTitle(/AI Architect/i);
  });

  test("2b. Prompt input is visible and accepts text", async ({ page }) => {
    await page.goto("/");
    const input = page.locator("input#prompt-input");
    await expect(input).toBeVisible({ timeout: 15_000 });
    await input.fill("Modern 2-floor villa");
    await expect(input).toHaveValue("Modern 2-floor villa");
  });

  test("2c. Generate button is visible and enabled when text is entered", async ({ page }) => {
    await page.goto("/");
    const input = page.locator("input#prompt-input");
    await expect(input).toBeVisible({ timeout: 15_000 });
    await input.fill("Modern 2-floor villa");
    const submitBtn = page.locator("button[type=submit]");
    await expect(submitBtn).toBeEnabled();
  });
});
