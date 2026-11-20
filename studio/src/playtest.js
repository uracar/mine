// The QA department's hands and eyes: serve the game, open it in a real
// (headless) browser, press buttons, measure frame rate, catch errors and
// take screenshots the QA AI can look at.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

function loadChromium() {
  try {
    return require("playwright").chromium;
  } catch {
    throw new Error("Playwright is not installed. Run: npm install playwright && npx playwright install chromium");
  }
}

const TYPES = {
  ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".wav": "audio/wav",
};

// Tiny static file server (ES modules don't load from file:// URLs).
export function serve(dir, port = 0) {
  const root = path.resolve(dir);
  const server = http.createServer((req, res) => {
    const urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
    let file = path.resolve(root, "." + urlPath);
    if (file !== root && !file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, "index.html");
    if (!fs.existsSync(file)) { res.writeHead(404).end("not found"); return; }
    res.writeHead(200, { "content-type": TYPES[path.extname(file)] ?? "application/octet-stream" });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((resolve) => server.listen(port, "127.0.0.1", () => resolve(server)));
}

// Default input script: a rough "press everything" session.
const DEFAULT_ACTIONS = [
  { wait: 1200 }, { shot: "title screen" },
  { key: "Enter" }, { key: "Space" }, { click: [640, 360] }, { wait: 800 }, { shot: "after start" },
  { hold: "ArrowRight", ms: 700 }, { hold: "KeyD", ms: 500 }, { key: "Space" }, { hold: "ArrowUp", ms: 400 },
  { hold: "ArrowLeft", ms: 600 }, { hold: "KeyW", ms: 400 }, { key: "Space" }, { click: [900, 300] },
  { wait: 500 }, { shot: "mid play" },
  { hold: "ArrowDown", ms: 500 }, { hold: "KeyA", ms: 500 }, { key: "KeyJ" }, { key: "KeyK" }, { key: "Space" },
  { hold: "ArrowRight", ms: 1500 }, { wait: 1500 }, { shot: "later play" },
  { key: "Escape" }, { wait: 500 }, { shot: "after Escape" },
];

/**
 * @param {string} gameDir folder containing index.html
 * @param {Array} actions steps like {key}, {hold, ms}, {click:[x,y]}, {wait}, {shot}
 */
export async function playtest(gameDir, actions = DEFAULT_ACTIONS) {
  if (!fs.existsSync(path.join(gameDir, "index.html"))) {
    return { report: { fatal: "game/index.html does not exist yet" }, shots: [] };
  }
  const server = await serve(gameDir);
  const { port } = server.address();
  const browser = await loadChromium().launch();
  const errors = [], warnings = [], externalRequests = [];
  const shots = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

    // Count sounds the game plays, without needing speakers.
    await page.addInitScript(() => {
      window.__qa = { soundsStarted: 0, audioContexts: 0 };
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) {
        window.AudioContext = class extends AC {
          constructor(...a) { super(...a); window.__qa.audioContexts++; }
        };
        for (const Node of [window.OscillatorNode, window.AudioBufferSourceNode]) {
          if (!Node) continue;
          const start = Node.prototype.start;
          Node.prototype.start = function (...a) { window.__qa.soundsStarted++; return start.apply(this, a); };
        }
      }
    });
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(`console.error: ${m.text()}`);
      else if (m.type() === "warning") warnings.push(m.text());
    });
    page.on("pageerror", (e) => errors.push(`uncaught: ${e.message}`));
    page.on("request", (r) => {
      const u = new URL(r.url());
      if (u.hostname !== "127.0.0.1" && u.protocol !== "data:" && u.protocol !== "blob:") externalRequests.push(r.url());
    });
    page.on("requestfailed", (r) => errors.push(`failed to load: ${r.url()}`));
    page.on("response", (r) => { if (r.status() >= 400) errors.push(`HTTP ${r.status()}: ${r.url()}`); });

    await page.goto(`http://127.0.0.1:${port}/index.html`, { waitUntil: "load", timeout: 15000 });

    for (const step of actions) {
      if (step.wait) await page.waitForTimeout(Math.min(step.wait, 10000));
      if (step.key) await page.keyboard.press(step.key);
      if (step.hold) {
        await page.keyboard.down(step.hold);
        await page.waitForTimeout(Math.min(step.ms ?? 300, 5000));
        await page.keyboard.up(step.hold);
      }
      if (step.click) await page.mouse.click(step.click[0], step.click[1]);
      if (step.shot && shots.length < 8) {
        const buf = await page.screenshot({ type: "jpeg", quality: 70 });
        shots.push({ label: step.shot, data: buf.toString("base64") });
      }
    }

    // Frame rate over two seconds.
    const fps = await page.evaluate(() => new Promise((done) => {
      let frames = 0; const t0 = performance.now();
      const tick = () => { frames++; performance.now() - t0 < 2000 ? requestAnimationFrame(tick) : done(frames / 2); };
      requestAnimationFrame(tick);
    }));
    const audio = await page.evaluate(() => window.__qa);

    return {
      report: {
        fps_in_headless_browser: Math.round(fps),
        errors: [...new Set(errors)].slice(0, 30),
        warnings: [...new Set(warnings)].slice(0, 10),
        external_requests: [...new Set(externalRequests)], // must be empty: everything is made in-house
        audio,
        screenshots: shots.map((s) => s.label),
      },
      shots,
    };
  } catch (err) {
    return { report: { fatal: err.message, errors }, shots };
  } finally {
    await browser.close();
    server.close();
  }
}
