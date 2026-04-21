import type { BroadcastMeta, BroadcastState, ProjectsFile } from "./types";
import {
  loadBroadcastPackage,
  primarySegment,
  resolveBroadcastAsset,
  type LoadedBroadcastPackage,
} from "./broadcastPackage";
import { receiverSay } from "./receiverSay";
import { Starfield } from "./starfield";
import { Satellite, type Keys } from "./satellite";

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

function formatStateLine(state: BroadcastState): string {
  const parts: string[] = [state.signal, state.mode];
  if (state.mood) {
    parts.push(state.mood);
  }
  if (state.transmission) {
    parts.push(state.transmission);
  }
  return parts.join(" · ");
}

function formatMetaLine(meta: BroadcastMeta): string {
  return `generated ${meta.generatedAt} · v${meta.packageVersion} · ${meta.audioFormat}`;
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

function applyPackageToUi(pkg: LoadedBroadcastPackage, metaEl: HTMLElement, stateEl: HTMLElement): void {
  stateEl.textContent = formatStateLine(pkg.state);
  metaEl.textContent = formatMetaLine(pkg.meta);
}

/**
 * Try autoplay; on browser block, show light gate — user taps once to `play()` and wire starfield.
 */
async function setupBroadcastPlayback(
  baseUrl: string,
  pkg: LoadedBroadcastPackage,
  starfield: Starfield,
  signalStatusEl: HTMLElement,
  gateEl: HTMLElement,
  resumeBtn: HTMLButtonElement
): Promise<void> {
  if (pkg.isMock) {
    starfield.setBroadcastAudio(null);
    signalStatusEl.textContent = "preview · no broadcast audio";
    gateEl.hidden = true;
    return;
  }

  const seg = primarySegment(pkg.playlist);
  const audio = new Audio(resolveBroadcastAsset(baseUrl, seg.audio));
  audio.loop = true;
  audio.preload = "auto";

  signalStatusEl.textContent = "signal acquired";

  const wirePlaying = (): void => {
    starfield.setBroadcastAudio(audio, seg.startOffset);
    signalStatusEl.textContent = "receiving";
    gateEl.hidden = true;
  };

  audio.addEventListener(
    "error",
    () => {
      starfield.setBroadcastAudio(null);
      signalStatusEl.textContent = "signal acquired · audio unavailable";
      gateEl.hidden = true;
      console.warn("[Sputnik] audio load error");
    },
    { once: true }
  );

  try {
    await audio.play();
    wirePlaying();
  } catch (err) {
    if (audio.error) {
      return;
    }
    console.warn("[Sputnik] autoplay blocked, awaiting gesture:", err);
    starfield.setBroadcastAudio(null);
    gateEl.hidden = false;
    signalStatusEl.textContent = "signal acquired";
    resumeBtn.addEventListener(
      "click",
      () => {
        void audio
          .play()
          .then(wirePlaying)
          .catch((e) => {
            console.warn("[Sputnik] play after gesture failed:", e);
          });
      },
      { once: true }
    );
  }
}

async function main(): Promise<void> {
  const [pkg, projectsFile] = await Promise.all([
    loadBroadcastPackage(base),
    loadJson<ProjectsFile>("config/projects.json"),
  ]);

  const sinceEl = document.querySelector<HTMLElement>("#since-launch");
  const orbitEl = document.querySelector<HTMLElement>("#orbit-day");
  const stateLineEl = document.querySelector<HTMLElement>("#receiver-state-line");
  const metaLineEl = document.querySelector<HTMLElement>("#receiver-meta-line");
  const signalStatusEl = document.querySelector<HTMLElement>("#receiver-signal-status");
  const audioGateEl = document.querySelector<HTMLElement>("#receiver-audio-gate");
  const audioResumeBtn = document.querySelector<HTMLButtonElement>("#receiver-audio-resume");
  const canvas = document.querySelector<HTMLCanvasElement>("#starfield");
  const sayInput = document.querySelector<HTMLInputElement>("#say-anything-input");
  const echoEl = document.querySelector<HTMLElement>("#transmit-echo");
  const projectLabelEl = document.querySelector<HTMLElement>("#project-hover-label");
  const satCanvas = document.querySelector<HTMLCanvasElement>("#satellite-canvas");
  const satTipEl = document.querySelector<HTMLElement>("#sat-tip");
  const satTipLabelEl = document.querySelector<HTMLElement>("#sat-tip-label");

  if (
    !sinceEl ||
    !orbitEl ||
    !stateLineEl ||
    !metaLineEl ||
    !signalStatusEl ||
    !audioGateEl ||
    !audioResumeBtn ||
    !canvas ||
    !sayInput ||
    !echoEl ||
    !projectLabelEl ||
    !satCanvas ||
    !satTipEl ||
    !satTipLabelEl
  ) {
    throw new Error("Missing DOM nodes");
  }

  receiverSay.init(sayInput);
  orbitEl.textContent = pad3(pkg.meta.orbitDay);
  runSinceLaunchTimer(pkg.meta.launchAt, sinceEl);
  applyPackageToUi(pkg, metaLineEl, stateLineEl);

  const starfield = new Starfield(canvas, pkg.score, projectsFile.projects);
  await setupBroadcastPlayback(base, pkg, starfield, signalStatusEl, audioGateEl, audioResumeBtn);

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
    if (hit?.url) {
      window.open(hit.url, "_blank", "noopener,noreferrer");
    }
  });

  // Satellite canvas setup
  const satCtx = satCanvas.getContext("2d");
  if (!satCtx) throw new Error("Satellite canvas 2D context unavailable");
  let satLogicalW = 0;
  let satLogicalH = 0;

  const satParent = satCanvas.parentElement!;
  const satellite = new Satellite(satParent.clientWidth, satParent.clientHeight);

  const resizeSatCanvas = (): void => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = satParent.clientWidth;
    const h = satParent.clientHeight;
    satLogicalW = w;
    satLogicalH = h;
    satCanvas.width = Math.floor(w * dpr);
    satCanvas.height = Math.floor(h * dpr);
    satCanvas.style.width = `${w}px`;
    satCanvas.style.height = `${h}px`;
    satCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    satCtx.imageSmoothingEnabled = false;
    satellite.resize(w, h);
  };
  resizeSatCanvas();
  window.addEventListener("resize", resizeSatCanvas);

  // WASD keys
  const keys: Keys = { up: false, down: false, left: false, right: false };
  window.addEventListener("keydown", (e) => {
    if (e.key === "w" || e.key === "W") keys.up = true;
    if (e.key === "s" || e.key === "S") keys.down = true;
    if (e.key === "a" || e.key === "A") keys.left = true;
    if (e.key === "d" || e.key === "D") keys.right = true;
  });
  window.addEventListener("keyup", (e) => {
    if (e.key === "w" || e.key === "W") keys.up = false;
    if (e.key === "s" || e.key === "S") keys.down = false;
    if (e.key === "a" || e.key === "A") keys.left = false;
    if (e.key === "d" || e.key === "D") keys.right = false;
  });

  // Satellite tip click
  let satTipAction: (() => void) | null = null;
  satTipEl.addEventListener("click", () => { satTipAction?.(); });

  const PROX_PX = 55;
  const DOM_PROX_PX = 70;

  type ProjPos = ReturnType<typeof starfield.getProjectPositions>;

  const updateSatTip = (projPositions: ProjPos): void => {
    const { x: sx, y: sy } = satellite.getPosition();
    const cRect = satCanvas.getBoundingClientRect();
    const ratioX = satLogicalW > 0 ? cRect.width / satLogicalW : 1;
    const ratioY = satLogicalH > 0 ? cRect.height / satLogicalH : 1;
    const vx = cRect.left + sx * ratioX;
    const vy = cRect.top + sy * ratioY;

    let label = "";
    let action: (() => void) | null = null;
    let best = Infinity;

    for (const pp of projPositions) {
      const d = Math.sqrt((sx - pp.x) ** 2 + (sy - pp.y) ** 2);
      if (d < PROX_PX && d < best) {
        best = d;
        label = pp.label;
        action = pp.url ? () => window.open(pp.url, "_blank", "noopener,noreferrer") : null;
      }
    }

    if (best === Infinity) {
      const domTargets = [
        { el: audioResumeBtn as HTMLElement, gate: audioGateEl as HTMLElement, text: "tap to receive signal", act: () => audioResumeBtn.click() },
        { el: sayInput as HTMLElement, gate: null as HTMLElement | null, text: "say anything", act: () => sayInput.focus() },
      ];
      for (const t of domTargets) {
        if (t.gate?.hidden) continue;
        const r = t.el.getBoundingClientRect();
        const d = Math.sqrt((vx - (r.left + r.width / 2)) ** 2 + (vy - (r.top + r.height / 2)) ** 2);
        if (d < DOM_PROX_PX && d < best) {
          best = d;
          label = t.text;
          action = t.act;
        }
      }
    }

    if (label) {
      satTipLabelEl.textContent = label;
      satTipAction = action;
      satTipEl.style.left = `${vx}px`;
      satTipEl.style.top = `${vy}px`;
      satTipEl.hidden = false;
    } else {
      satTipEl.hidden = true;
      satTipAction = null;
    }
  };

  let lastLoopTime = performance.now();
  const loop = (): void => {
    const now = performance.now();
    const dt = Math.min(0.05, (now - lastLoopTime) / 1000);
    lastLoopTime = now;

    starfield.frame();

    const projPositions = starfield.getProjectPositions();
    satellite.update(dt, keys, projPositions);
    satCtx.clearRect(0, 0, satLogicalW, satLogicalH);
    satellite.draw(satCtx);
    updateSatTip(projPositions);

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
