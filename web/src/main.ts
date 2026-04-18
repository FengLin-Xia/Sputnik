import type { BroadcastMeta, BroadcastState, ProjectsFile } from "./types";
import {
  loadBroadcastPackage,
  primarySegment,
  resolveBroadcastAsset,
  type LoadedBroadcastPackage,
} from "./broadcastPackage";
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
    !projectLabelEl
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
