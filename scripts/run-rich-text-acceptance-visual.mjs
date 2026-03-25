import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");

const baseUrl = process.env.DREAMAXIS_ACCEPTANCE_BASE_URL ?? "http://127.0.0.1:3000";
const acceptancePath = "/acceptance/rich-text-v1";
const baselineDir = path.join(repoRoot, "docs", "acceptance", "rich-text-v1", "screenshots");
const outputRoot = path.join(repoRoot, "artifacts", "acceptance", "rich-text-v1");
const currentDir = path.join(outputRoot, "current");
const diffDir = path.join(outputRoot, "diff");
const summaryPath = path.join(outputRoot, "summary.json");
const maxDiffRatio = Number(process.env.DREAMAXIS_ACCEPTANCE_MAX_DIFF_RATIO ?? "0.02");

const shots = [
  "chat-01-streaming-rich",
  "chat-02-markdown-basics",
  "chat-03-code-highlight",
  "chat-04-math-katex-all-syntax",
  "chat-05-mermaid-success",
  "chat-06-mermaid-fallback-with-src",
  "chat-07-html-escaped",
  "chat-08-narrow-viewport",
  "operator-01-plan-summary-rich",
  "operator-02-failure-summary-rich",
  "runtime-01-execution-summary-rich",
  "runtime-02-approval-summary-rich",
  "runtime-03-raw-logs-monospace",
];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function ensurePageReady(url) {
  let lastError = null;
  for (let attempt = 1; attempt <= 40; attempt += 1) {
    try {
      const response = await fetch(url, { redirect: "follow" });
      if (response.ok) return;
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(1500);
  }
  throw new Error(`Acceptance page did not become ready: ${lastError instanceof Error ? lastError.message : String(lastError)}`);
}

async function ensureDirectories() {
  await fs.mkdir(currentDir, { recursive: true });
  await fs.mkdir(diffDir, { recursive: true });
}

async function compareShot(shot) {
  const baselinePath = path.join(baselineDir, `${shot}.png`);
  const currentPath = path.join(currentDir, `${shot}.png`);
  const diffPath = path.join(diffDir, `${shot}.png`);

  const [baselineBuffer, currentBuffer] = await Promise.all([fs.readFile(baselinePath), fs.readFile(currentPath)]);
  const baseline = PNG.sync.read(baselineBuffer);
  const current = PNG.sync.read(currentBuffer);

  if (baseline.width !== current.width || baseline.height !== current.height) {
    return {
      shot,
      ok: false,
      reason: `dimension mismatch ${baseline.width}x${baseline.height} != ${current.width}x${current.height}`,
      diffRatio: 1,
      diffPixels: baseline.width * baseline.height,
      diffPath,
    };
  }

  const diff = new PNG({ width: baseline.width, height: baseline.height });
  const diffPixels = pixelmatch(baseline.data, current.data, diff.data, baseline.width, baseline.height, {
    threshold: 0.1,
    includeAA: false,
  });
  const diffRatio = diffPixels / (baseline.width * baseline.height);

  if (diffPixels > 0) {
    await fs.writeFile(diffPath, PNG.sync.write(diff));
  } else {
    await fs.rm(diffPath, { force: true }).catch(() => undefined);
  }

  return {
    shot,
    ok: diffRatio <= maxDiffRatio,
    reason: diffRatio <= maxDiffRatio ? "within threshold" : `diff ratio ${diffRatio.toFixed(4)} exceeded ${maxDiffRatio.toFixed(4)}`,
    diffRatio,
    diffPixels,
    diffPath,
  };
}

async function main() {
  const url = `${baseUrl}${acceptancePath}`;
  await ensureDirectories();
  await ensurePageReady(url);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 2200 },
    colorScheme: "dark",
    deviceScaleFactor: 1,
  });

  try {
    await page.emulateMedia({ reducedMotion: "reduce", colorScheme: "dark" });
    await page.goto(url, { waitUntil: "networkidle" });

    const results = [];
    for (const shot of shots) {
      const locator = page.locator(`[data-shot="${shot}"]`);
      await locator.waitFor({ state: "visible" });
      await locator.scrollIntoViewIfNeeded();
      await locator.screenshot({
        path: path.join(currentDir, `${shot}.png`),
        animations: "disabled",
      });
      results.push(await compareShot(shot));
    }

    await fs.writeFile(summaryPath, JSON.stringify({ baseUrl, acceptancePath, maxDiffRatio, results }, null, 2));

    const failed = results.filter((result) => !result.ok);
    if (failed.length) {
      const lines = failed.map(
        (result) => `- ${result.shot}: ${result.reason} (${result.diffPixels} px changed)`,
      );
      throw new Error(`Rich-text acceptance visual diff failed.\n${lines.join("\n")}`);
    }

    console.log(`Rich-text acceptance visual pass: ${results.length}/${shots.length} shots within threshold.`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack ?? error.message : error);
  process.exitCode = 1;
});
