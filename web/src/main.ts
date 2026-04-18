import type { BroadcastMeta, BroadcastState, ProjectsFile, Score } from "./types";
import { receiverSay } from "./receiverSay";
import { Starfield } from "./starfield";

const base = import.meta.env.BASE_URL;

async function loadJson<T>(path: string): Promise<T> {
  const res = await fetch(`${base}${path}`);
  if (!res.ok) {
    throw new Error(`Failed to load ${path}: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

function pad3(n: number): string {
  return n.toString().padStart(3, "0");
}

function formatSinceLaunch(iso: string): string {
  const launch = new Date(iso).getTime();
  const now = Date.now();
  let diff = Math.max(0, now - launch);
  const days = Math.floor(diff / 86_400_000);
  diff %= 86_400_000;
  const hours = Math.floor(diff / 3_600_000);
  diff %= 3_600_000;
  const minutes = Math.floor(diff / 60_000);
  diff %= 60_000;
  const seconds = Math.floor(diff / 1000);
  return `${pad3(days)}d ${pad2(hours)}h ${pad2(minutes)}m ${pad2(seconds)}s`;
}

function runSinceLaunchTimer(launchAt: string, sinceEl: HTMLElement): void {
  const tick = (): void => {
    sinceEl.textContent = formatSinceLaunch(launchAt);
  };
  tick();
  window.setInterval(tick, 1000);
}

function bindTransmit(input: HTMLInputElement, echoEl: HTMLElement): void {
  let clearTimer = 0;
  const show = (lines: string[]): void => {
    echoEl.innerHTML = lines.map((l) => `<span>${escapeHtml(l)}</span>`).join("<br />");
    echoEl.hidden = false;
    window.clearTimeout(clearTimer);
    clearTimer = window.setTimeout(() => {
      echoEl.hidden = true;
      echoEl.textContent = "";
    }, 4200);
  };

  input.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    const raw = input.value.trim();
    input.value = "";
    if (!raw) {
      show(["no confirmation returned"]);
      return;
    }
    show(["fragment received", "signal absorbed", "no confirmation returned"]);
  });
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function main(): Promise<void> {
  const [, score, projectsFile, meta] = await Promise.all([
    loadJson<BroadcastState>("broadcast/state.json"),
    loadJson<Score>("broadcast/score.json"),
    loadJson<ProjectsFile>("config/projects.json"),
    loadJson<BroadcastMeta>("broadcast/meta.json"),
  ]);

  const sinceEl = document.querySelector<HTMLElement>("#since-launch");
  const orbitEl = document.querySelector<HTMLElement>("#orbit-day");
  const canvas = document.querySelector<HTMLCanvasElement>("#starfield");
  const sayInput = document.querySelector<HTMLInputElement>("#say-anything-input");
  const echoEl = document.querySelector<HTMLElement>("#transmit-echo");
  const projectLabelEl = document.querySelector<HTMLElement>("#project-hover-label");

  if (!sinceEl || !orbitEl || !canvas || !sayInput || !echoEl || !projectLabelEl) {
    throw new Error("Missing DOM nodes");
  }

  receiverSay.init(sayInput);
  orbitEl.textContent = pad3(meta.orbitDay);
  runSinceLaunchTimer(meta.launchAt, sinceEl);

  const starfield = new Starfield(canvas, score, projectsFile.projects);
  starfield.resize();
  window.addEventListener("resize", () => starfield.resize());

  const updateHover = (clientX: number, clientY: number): void => {
    const hit = starfield.hitTest(clientX, clientY);
    starfield.setHoveredProject(hit?.id ?? null);
    if (hit) {
      projectLabelEl.textContent = hit.label;
      projectLabelEl.hidden = false;
      const anchor = starfield.getProjectLabelAnchor(hit);
      projectLabelEl.style.left = `${anchor.left}px`;
      projectLabelEl.style.top = `${anchor.top - 6}px`;
      canvas.style.cursor = "crosshair";
    } else {
      projectLabelEl.hidden = true;
      canvas.style.cursor = "default";
    }
  };

  canvas.addEventListener("mousemove", (e) => {
    updateHover(e.clientX, e.clientY);
  });
  canvas.addEventListener("mouseleave", () => {
    starfield.setHoveredProject(null);
    projectLabelEl.hidden = true;
    canvas.style.cursor = "default";
  });
  canvas.addEventListener("click", (e) => {
    const hit = starfield.hitTest(e.clientX, e.clientY);
    if (hit) {
      console.info("[Sputnik] project star:", hit.id, hit.label);
    }
  });

  const loop = (): void => {
    starfield.frame();
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);

  bindTransmit(sayInput, echoEl);
}

main().catch((err) => {
  console.error(err);
  const app = document.getElementById("app");
  if (app) {
    app.innerHTML = `<p class="receiver__error">receiver fault: ${escapeHtml(String(err))}</p>`;
  }
});
