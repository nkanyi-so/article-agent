// Drives a real Chrome through what a stranger does, at desktop and phone width, and
// prints a table. No key, nothing installed but Chrome and Node 22 or later.
//
//   node scripts/browser-check.mjs                          # the public address
//   BASE=http://localhost:3000 node scripts/browser-check.mjs
//   SHOTS=/tmp/shots node scripts/browser-check.mjs         # also save screenshots
//
// It clicks with real mouse events at the element's position, through the DevTools
// protocol. It starts two runs per width (one run, one re-run) and reads everything else.
// Eighteen steps: nine at each width.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE = (process.env.BASE ?? "https://article-agent-web.vercel.app").replace(/\/+$/, "");
const SHOTS = process.env.SHOTS;
const CHROME = process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// The script talks to Chrome over the WebSocket that Node itself provides, from Node 22 on.
// Without it the connection fails in a way that reads as "Chrome did not start".
if (typeof globalThis.WebSocket !== "function") {
  console.error(`browser-check needs Node 22 or later (it uses Node's own WebSocket). This is Node ${process.versions.node}. The project's version is in frontend/.nvmrc.`);
  process.exit(2);
}

const chrome = spawn(CHROME, [
  "--headless=new", "--disable-gpu", "--no-first-run", `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "browser-check-"))}`, "about:blank",
], { stdio: "ignore" });
// The Chrome started here never outlives the script: not when a step throws, not when
// Chrome cannot be reached, not when the script is interrupted.
const stopChrome = () => { if (chrome.exitCode === null && !chrome.killed) chrome.kill(); };
process.on("exit", stopChrome);
for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(signal, () => process.exit(1));
process.on("uncaughtException", (error) => { console.error(error); process.exit(1); });
process.on("unhandledRejection", (error) => { console.error(error); process.exit(1); });
chrome.on("error", (error) => { console.error(`Chrome could not be started (${CHROME}): ${error.message}`); process.exit(1); });

async function connect() {
  // Up to 30 seconds: a cold Chrome on a CI runner takes about 6 to answer, sometimes more.
  for (let attempt = 0; attempt < 150; attempt++) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
      const page = pages.find((p) => p.type === "page");
      if (page) return new WebSocket(page.webSocketDebuggerUrl);
    } catch { /* not up yet */ }
    await sleep(200);
  }
  throw new Error("Chrome did not start");
}

const socket = await connect();
await new Promise((resolve) => socket.addEventListener("open", resolve));
let nextId = 0;
const waiting = new Map();
socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && waiting.has(message.id)) {
    waiting.get(message.id)(message);
    waiting.delete(message.id);
  }
});
function send(method, params = {}) {
  const id = ++nextId;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) =>
    waiting.set(id, (m) => (m.error ? reject(new Error(`${method}: ${m.error.message}`)) : resolve(m.result)))
  );
}
async function js(expression) {
  const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}
// The body is briefly absent while a page is being replaced.
const text = () => js(`document.body ? document.body.innerText : ""`);
async function until(what, test, timeout = 30000) {
  const end = Date.now() + timeout;
  for (;;) {
    const value = await test();
    if (value) return value;
    if (Date.now() > end) throw new Error(`timed out waiting for: ${what}`);
    await sleep(150);
  }
}
/** Clicks the first element matching `find` (a JS expression) with real mouse events. */
async function click(what, find) {
  const box = await js(`(() => { const el = ${find}; if (!el) return null;
    el.scrollIntoView({ block: "center" });
    // The first line box: a sentence wraps, and the middle of its bounding box can be
    // another sentence's text.
    const r = [...el.getClientRects()].find((box) => box.width > 0 && box.height > 0);
    if (!r) return null;
    return { x: r.left + Math.min(r.width / 2, 40), y: r.top + r.height / 2 }; })()`);
  if (!box) throw new Error(`nothing to click: ${what}`);
  await sleep(150);
  for (const type of ["mousePressed", "mouseReleased"]) {
    await send("Input.dispatchMouseEvent", { type, x: box.x, y: box.y, button: "left", clickCount: 1 });
  }
}
const byText = (selector, needle) =>
  `[...document.querySelectorAll(${JSON.stringify(selector)})].find((el) => el.innerText.includes(${JSON.stringify(needle)}))`;
async function shot(width, name) {
  if (!SHOTS) return;
  mkdirSync(SHOTS, { recursive: true });
  const { data } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(SHOTS, `${name}-${width}.png`), Buffer.from(data, "base64"));
}

/** On a phone the lines come up as a sheet over the article: close it before the next choice. */
async function closeSheet() {
  const open = await js(`(() => { const b = document.querySelector(".evidence-close");
    return !!b && getComputedStyle(b).display !== "none"; })()`);
  if (open) await click("close", `document.querySelector(".evidence-close")`);
  await sleep(150);
}

const rows = [];
async function step(width, name, action) {
  const started = Date.now();
  try {
    const detail = await action();
    rows.push([width, name, "pass", detail ?? "", Date.now() - started]);
  } catch (error) {
    rows.push([width, name, "FAIL", String(error.message).slice(0, 420), Date.now() - started]);
  }
}

async function journey(width, metrics) {
  await send("Emulation.setDeviceMetricsOverride", metrics);
  await send("Page.navigate", { url: `${BASE}/` });

  await step(width, "the first page loads with no key", async () => {
    await until("the transcripts", async () => (await text()).includes("Read the checked article"));
    const page = await text();
    if (!page.includes("replays recordings")) throw new Error("no line about recordings");
    await shot(width, "1-entry");
    return `${(page.match(/Read the checked article/g) ?? []).length} transcripts offered`;
  });

  await step(width, "open a checked article", async () => {
    await click("the Sallowfield article", `(${byText(".panel", "Sallowfield Dental Group")})?.querySelector("a button")`);
    await until("the article", async () => (await text()).includes("SENTENCES KEPT") || (await text()).includes("Sentences kept"));
    await until("its sentences", () => js(`document.querySelectorAll("article .sentence").length > 5`));
    return await js(`location.pathname`);
  });

  await step(width, "choose a normal sentence: its cited line and the code-added question", async () => {
    await click("a sentence", byText("article p .sentence", "before the switch, 14 percent"));
    await until("the cited line", async () => (await text()).includes("Before the switch, 14 percent of appointments were missed"));
    const page = (await text()).toLowerCase();
    if (!page.includes("cited by the model")) throw new Error("no 'cited by the model'");
    if (!page.includes("added by code, not cited by the model")) throw new Error("question not marked as added by code");
    if (!page.includes("what has that done to missed appointments?")) throw new Error("the question is missing");
    await shot(width, "2-sentence");
    return "line 14 cited; line 13 shown as added by code";
  });

  await step(width, "choose a flagged sentence: the judge's reason", async () => {
    await closeSheet();
    await click("the flagged sentence", `document.querySelector("article p .sentence.flagged")`);
    await until("the flag", async () => (await text()).toLowerCase().includes("flagged by the judge model"));
    await shot(width, "3-flagged");
    return await js(`document.querySelector(".evidence .note-flag")?.innerText.split("\\n").pop()`);
  });

  await step(width, "choose the headline", async () => {
    await closeSheet();
    await click("the headline", `document.querySelector("article h1 .sentence")`);
    await until("the headline note", async () => (await text()).includes("A headline cites no lines of its own"));
    await shot(width, "4-headline");
    return "explains that a headline cites no lines, with the judge's verdict";
  });

  await step(width, "the removed sentence, with its reason", async () => {
    const page = await text();
    if (!page.toLowerCase().includes("removed by code")) throw new Error("no removed list");
    const reason = await js(`document.querySelector(".note-removed")?.innerText`);
    if (!reason || !reason.includes("Code:")) throw new Error("no reason shown");
    return reason.split("\n").pop();
  });

  let runPath = null;
  await step(width, "start a run and watch it finish", async () => {
    await send("Page.navigate", { url: `${BASE}/` });
    await until("the transcripts", async () => (await text()).includes("Run it now"));
    await click("Run it now", `(${byText(".panel", "Quillmoor Books")})?.querySelector("button:not([tabindex='-1'])")`);
    const seen = [];
    const started = Date.now();
    await until("the stages to appear", async () => (await text()).includes("The stages arrive over a live stream"), 10000);
    await until("the run to finish and its page to open", async () => {
      const state = await js(`[...document.querySelectorAll("ol[aria-live] li")].map((li) => li.innerText.split("\\n").pop().trim().split(" ")[0]).join(",")`);
      if (state && seen.at(-1) !== state) {
        seen.push(state);
        if (seen.length === 3) await shot(width, "5-running");
      }
      const path = await js(`location.pathname`);
      return path.startsWith("/runs/") && !path.includes("seed-") && (await text()).toLowerCase().includes("sentences kept");
    }, 60000).catch(async (error) => {
      // Say what the page was showing, so a failure here can be told apart from a slow run.
      const page = (await text()).replace(/\s+/g, " ");
      throw new Error(`${error.message}; stages seen: ${seen.join(" | ") || "none"}; at ${await js("location.pathname")}; page: ${page.slice(-160)}`);
    });
    runPath = await js(`location.pathname`);
    await shot(width, "6-finished");
    return `${seen.length} distinct stage states seen over ${((Date.now() - started) / 1000).toFixed(1)}s; opened ${runPath}`;
  });

  await step(width, "re-run from the draft stage", async () => {
    if (!runPath) throw new Error("no run to re-run");
    await click("Re-run from here (draft)", `[...document.querySelectorAll("button")].filter((b) => b.innerText.includes("Re-run from here"))[2]`);
    // Headings are shown in capitals, and the page's text comes back as shown.
    await until("the re-run to start", async () => (await text()).toLowerCase().includes("re-running from the draft stage"), 15000);
    await shot(width, "7-rerun");
    await until("the new run's page", async () => {
      const path = await js(`location.pathname`);
      return path !== runPath && (await text()).includes("Re-run of");
    }, 60000);
    return `opened ${await js("location.pathname")}, marked as a re-run of ${runPath.split("/").pop()}`;
  });

  await step(width, "the list of runs is the seeded ones plus this browser's", async () => {
    await send("Page.navigate", { url: `${BASE}/` });
    await until("this browser's runs", async () => (await text()).toLowerCase().includes("runs you started in this browser"));
    const mine = await js(`[...document.querySelectorAll('section[aria-label="Runs you started"] a')].map((a) => a.innerText)`);
    if (!mine.some((label) => label.includes("re-run")) || !mine.some((label) => label.endsWith("run") && !label.includes("re-run"))) {
      throw new Error(`expected a run and a re-run, got ${JSON.stringify(mine)}`);
    }
    let where = "the first page";
    if (width === "desktop") {
      // The sidebar is only shown on a wide screen. It must hold the same runs, and stay
      // the same when asked again (on the host, another instance may answer).
      const read = () => js(`[...document.querySelectorAll("nav.sidebar a[href^='/runs/']")].map((a) => a.getAttribute("href")).sort().join(" ")`);
      const first = await until("the sidebar", async () => { const v = await read(); return v.includes("seed-") && v.includes("--r-draft--") ? v : null; });
      for (let again = 0; again < 3; again++) {
        await send("Page.navigate", { url: `${BASE}/` });
        const next = await until("the sidebar again", async () => { const v = await read(); return v.includes("seed-") ? v : null; });
        if (next !== first) throw new Error("the sidebar's list changed between loads");
      }
      if ((first.match(/seed-/g) ?? []).length !== 4) throw new Error(`expected 4 seeded runs in the sidebar: ${first}`);
      where = "the sidebar (same on four loads) and the first page";
    }
    await click("one of this browser's runs", `document.querySelector('section[aria-label="Runs you started"] a')`);
    await until("that run's page", async () => (await js("location.pathname")).includes("--") && (await text()).toLowerCase().includes("sentences kept"));
    await shot(width, "8-my-runs");
    return `${mine.length} of this browser's runs listed in ${where}; opened ${await js("location.pathname")}`;
  });
}

try {
  await send("Page.enable");
  await send("Runtime.enable");
  await journey("desktop", { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await journey("phone", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
} finally {
  stopChrome();
}
console.log(`Checked ${BASE} in Chrome\n`);
for (const [width, name, result, detail, ms] of rows) {
  console.log(`${result.padEnd(4)} ${width.padEnd(7)} ${name}\n        ${detail} (${(ms / 1000).toFixed(1)}s)`);
}
process.exit(rows.some((row) => row[2] === "FAIL") ? 1 : 0);
