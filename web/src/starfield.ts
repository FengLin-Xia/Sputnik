import type { ProjectStar, Score } from "./types";
import { mapNotesToStarPositions } from "./mapNotes";

/** Stable hash for per-star phase / frequency (desync twinkle). */
function hashString32(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Per-note scale [min, max]: deterministic; max 激进偏大以拉开与暗态对比。 */
function noteSizeScale(noteId: string | undefined, noteIndex: number): number {
  const h = hashString32(noteId ?? `n${noteIndex}`);
  const t = (h % 10000) / 10000;
  const min = 0.48;
  const max = 1.48;
  return min + t * (max - min);
}

function totalBeats(score: Score): number {
  let max = 0;
  for (const n of score.notes) {
    max = Math.max(max, n.t + n.d);
  }
  return Math.max(max, score.bars * 4, 1);
}

function mulberry32(seed: number): () => number {
  return (): number => {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type NoiseDot = { x: number; y: number; a: number };

export class Starfield {
  private readonly canvas: HTMLCanvasElement;
  private readonly ctx: CanvasRenderingContext2D;
  private readonly score: Score;
  private readonly projects: ProjectStar[];
  private readonly start = performance.now();
  private lastFrame = this.start;
  /** When set, playhead follows HTMLAudioElement.currentTime (broadcast sync). */
  private audioElement: HTMLAudioElement | null = null;
  private audioStartOffsetBeats = 0;
  private logicalW = 0;
  private logicalH = 0;
  private mapped: ReturnType<typeof mapNotesToStarPositions> = [];
  private glow: number[] = [];
  private noise: NoiseDot[] = [];
  private hoveredId: string | null = null;

  constructor(canvas: HTMLCanvasElement, score: Score, projects: ProjectStar[]) {
    this.canvas = canvas;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      throw new Error("Canvas 2D context unavailable");
    }
    this.ctx = ctx;
    this.score = score;
    this.projects = projects;
    this.glow = score.notes.map(() => 0);
  }

  setHoveredProject(id: string | null): void {
    this.hoveredId = id;
  }

  /**
   * Drive note playhead from broadcast audio. Pass null to use internal wall-clock loop
   * (mock / no audio). startOffsetBeats shifts the score timeline for this segment.
   */
  setBroadcastAudio(audio: HTMLAudioElement | null, startOffsetBeats = 0): void {
    this.audioElement = audio;
    this.audioStartOffsetBeats = startOffsetBeats;
  }

  private computePlayheadBeats(): number {
    const bpm = this.score.bpm;
    const beats = totalBeats(this.score);
    const secPerBeat = 60 / bpm;
    const loopSec = beats * secPerBeat;
    if (loopSec <= 0) {
      return 0;
    }
    if (this.audioElement) {
      const t = ((this.audioElement.currentTime % loopSec) + loopSec) % loopSec;
      const ph = (t / secPerBeat + this.audioStartOffsetBeats) % beats;
      return ph < 0 ? ph + beats : ph;
    }
    const elapsed = (performance.now() - this.start) / 1000;
    const t = ((elapsed % loopSec) + loopSec) % loopSec;
    return (t / secPerBeat) % beats;
  }

  /** Viewport pixel position for floating label (above star). */
  getProjectLabelAnchor(p: ProjectStar): { left: number; top: number } {
    const { x, y } = this.projectPixel(p);
    const r = this.canvas.getBoundingClientRect();
    const sx = r.width / this.logicalW;
    const sy = r.height / this.logicalH;
    return {
      left: r.left + x * sx,
      top: r.top + y * sy,
    };
  }

  hitTest(clientX: number, clientY: number): ProjectStar | null {
    const r = this.canvas.getBoundingClientRect();
    const lx = clientX - r.left;
    const ly = clientY - r.top;
    const scaleX = this.logicalW / r.width;
    const scaleY = this.logicalH / r.height;
    const x = lx * scaleX;
    const y = ly * scaleY;
    let best: ProjectStar | null = null;
    let bestD = Infinity;
    for (const p of this.projects) {
      const { x: px, y: py } = this.projectPixel(p);
      const d = (px - x) ** 2 + (py - y) ** 2;
      if (d < bestD) {
        bestD = d;
        best = p;
      }
    }
    return bestD <= 30 * 30 ? best : null;
  }

  resize(): void {
    const parent = this.canvas.parentElement;
    if (!parent) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    this.logicalW = w;
    this.logicalH = h;
    this.canvas.width = Math.floor(w * dpr);
    this.canvas.height = Math.floor(h * dpr);
    this.canvas.style.width = `${w}px`;
    this.canvas.style.height = `${h}px`;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.ctx.imageSmoothingEnabled = false;

    const beats = totalBeats(this.score);
    this.mapped = mapNotesToStarPositions(this.score.notes, beats, w, h);

    const rnd = mulberry32(0x5f3759df);
    const target = Math.min(140, Math.floor((w * h) / 8500) + 40);
    this.noise = [];
    for (let i = 0; i < target; i++) {
      this.noise.push({
        x: rnd() * w,
        y: rnd() * h,
        a: 0.028 + rnd() * 0.055,
      });
    }
  }

  private projectPixel(p: ProjectStar): { x: number; y: number } {
    const pad = 0.07;
    const padX = this.logicalW * pad;
    const padY = this.logicalH * pad;
    const innerW = this.logicalW - 2 * padX;
    const innerH = this.logicalH - 2 * padY;
    const shiftUp = innerH * 0.145;
    const y = Math.max(padY * 0.35, padY + p.y * innerH - shiftUp);
    return { x: padX + p.x * innerW, y };
  }

  private driftOffset(): { dx: number; dy: number } {
    const t = performance.now() * 0.00011;
    return { dx: Math.sin(t) * 0.55, dy: Math.cos(t * 0.83) * 0.38 };
  }

  frame(): void {
    const now = performance.now();
    const dt = Math.min(0.048, (now - this.lastFrame) / 1000);
    this.lastFrame = now;

    const playhead = this.computePlayheadBeats();

    const notes = this.score.notes;
    for (let i = 0; i < notes.length; i++) {
      const n = notes[i];
      const active = playhead >= n.t && playhead < n.t + n.d;
      if (active) this.glow[i] = 1;
      else this.glow[i] = Math.max(0, this.glow[i] - dt * 2.4);
    }

    const { dx, dy } = this.driftOffset();
    const w = this.logicalW;
    const h = this.logicalH;
    const ctx = this.ctx;

    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, w, h);

    for (const dot of this.noise) {
      ctx.fillStyle = `rgba(140, 170, 210, ${dot.a * 0.72})`;
      ctx.fillRect(Math.floor(dot.x), Math.floor(dot.y), 1, 1);
    }

    for (let i = 0; i < this.mapped.length; i++) {
      const m = this.mapped[i];
      const n = notes[i];
      const gx = m.x + dx;
      const gy = m.y + dy;
      const active = playhead >= n.t && playhead < n.t + n.d;
      const g = this.glow[i];
      const baseA = 0.1 + n.v * 0.22;
      const boost = active ? 0.62 : g * 0.42;
      const a = Math.min(1, baseA + boost);
      const cold = 175 + Math.floor(n.v * 40);
      const litStrength = active ? 1 : g;
      const sizeScale = noteSizeScale(n.id, i);
      this.drawBroadcastPixel(gx, gy, a, cold, litStrength, i, now, sizeScale);
    }

    for (const p of this.projects) {
      const { x: px, y: py } = this.projectPixel(p);
      const hover = this.hoveredId === p.id;
      this.drawProjectStar(px, py, hover, now, p.id);
    }
  }

  /**
   * Idle: small dim cross. Lit / afterglow: long cardinal arms + short diagonals — pixel cruciform,
   * larger footprint, outer tips dimmer with shared flicker.
   */
  private drawBroadcastPixel(
    x: number,
    y: number,
    alpha: number,
    cold: number,
    litStrength: number,
    noteIndex: number,
    now: number,
    sizeScale: number
  ): void {
    const ctx = this.ctx;
    const x0 = Math.floor(x);
    const y0 = Math.floor(y);
    const cap = Math.min(1, alpha);
    const R = cold - 20;
    const G = cold - 5;
    const B = cold + 15;

    const NOTE_GLOW_PERIOD_MS = 5000;
    const noteGlowPh = noteIndex * 1.19 + x0 * 0.03 + y0 * 0.027;
    const tGlow = (2 * Math.PI * now) / NOTE_GLOW_PERIOD_MS;
    const flicker = 0.5 + 0.5 * Math.cos(tGlow + noteGlowPh);
    const flickerHi = 0.5 + 0.5 * Math.cos(tGlow + noteGlowPh + 0.95);
    const flickerTip = 0.5 + 0.5 * Math.cos(tGlow + noteGlowPh + 1.85);

    if (litStrength < 0.04) {
      const half = sizeScale < 0.62 ? 2 : 3;
      ctx.fillStyle = `rgba(${R}, ${G}, ${B}, ${cap * 0.55})`;
      ctx.fillRect(x0, y0 - half, 1, 2 * half + 1);
      ctx.fillRect(x0 - half, y0, 2 * half + 1, 1);
      if (cap > 0.32) {
        ctx.fillStyle = `rgba(200, 218, 238, ${cap * 0.16})`;
        ctx.fillRect(x0 - half, y0 - half, 2 * half + 1, 2 * half + 1);
      }
      return;
    }

    const s = litStrength;
    type Cell = [number, number, number];

    const armBase = noteIndex * 0.88 + x0 * 0.021 + y0 * 0.019;
    const tArm = (2 * Math.PI * now) / NOTE_GLOW_PERIOD_MS;
    const armN = 0.8 + 0.2 * Math.sin(tArm + armBase + 0.0);
    const armE = 0.8 + 0.2 * Math.sin(tArm + armBase + 1.4);
    const armS = 0.8 + 0.2 * Math.sin(tArm + armBase + 2.9);
    const armW = 0.8 + 0.2 * Math.sin(tArm + armBase + 4.4);

    const armBrightnessMul = (dx: number, dy: number): number => {
      if (dx === 0 && dy === 0) return 1;
      if (dx !== 0 && dy !== 0) {
        if (Math.abs(dx) === Math.abs(dy)) {
          if (dx < 0 && dy < 0) return (armN + armW) * 0.5;
          if (dx > 0 && dy < 0) return (armN + armE) * 0.5;
          if (dx < 0 && dy > 0) return (armS + armW) * 0.5;
          return (armS + armE) * 0.5;
        }
        if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? armE : armW;
        return dy < 0 ? armN : armS;
      }
      if (dy === 0) return dx > 0 ? armE : armW;
      return dy < 0 ? armN : armS;
    };

    /** Axis distance k≥1; amplitude ↑ 与臂长加倍配套，否则远端过淡。 */
    const axisWeight = (k: number): number => 1.38 * Math.exp(-0.246 * k);

    const R_MAX = 16;
    const armSpan = (R_MAX - 5) * 2;
    const rMax = Math.max(5, Math.round(5 + sizeScale * armSpan));
    const weightBoost = (0.54 + 0.5 * sizeScale) * 1.6;

    const cells: Cell[] = [[0, 0, 1]];
    for (let k = 1; k <= rMax; k++) {
      const w = axisWeight(k) * weightBoost;
      cells.push([-k, 0, w], [k, 0, w], [0, -k, w], [0, k, w]);
    }
    const diag = [0.44, 0.24, 0.12];
    const diagKMax = Math.min(3, rMax);
    for (let k = 1; k <= diagKMax; k++) {
      const w = diag[k - 1] * weightBoost;
      cells.push([-k, -k, w], [k, -k, w], [-k, k, w], [k, k, w]);
    }

    const thicken: Cell[] = [];
    for (let k = 2; k <= rMax; k++) {
      const w = axisWeight(k) * weightBoost;
      const t1 = w * 0.78;
      const t2 = w * 0.54;
      const t3 = w * 0.36;
      thicken.push([-k, -1, t1], [-k, 1, t1], [k, -1, t1], [k, 1, t1]);
      thicken.push([-1, -k, t1], [1, -k, t1], [-1, k, t1], [1, k, t1]);
      if (k >= 3) {
        thicken.push([-k, -2, t2], [-k, 2, t2], [k, -2, t2], [k, 2, t2]);
        thicken.push([-2, -k, t2], [2, -k, t2], [-2, k, t2], [2, k, t2]);
      }
      if (k >= 4) {
        thicken.push([-k, -3, t3], [-k, 3, t3], [k, -3, t3], [k, 3, t3]);
        thicken.push([-3, -k, t3], [3, -k, t3], [-3, k, t3], [3, k, t3]);
      }
    }

    const allCells = [...cells, ...thicken];
    allCells.sort((a, b) => a[2] - b[2]);

    for (const [dx, dy, w] of allCells) {
      const ring = Math.max(Math.abs(dx), Math.abs(dy));
      const onAxis = dx === 0 || dy === 0;
      const axisDist = onAxis ? (dx === 0 ? Math.abs(dy) : Math.abs(dx)) : ring;
      const ringF = !onAxis
        ? flickerHi
        : axisDist >= 12
          ? flickerTip
          : axisDist >= 2
            ? flickerHi
            : flicker;
      const armM = armBrightnessMul(dx, dy);
      let a = cap * s * w * ringF * (ring === 0 ? 0.97 : 0.93) * armM;
      if (a < 0.004) continue;

      const rgbFade = onAxis
        ? Math.max(0.2, 1 - axisDist * 0.078)
        : Math.max(0.32, 1 - ring * 0.11);
      const br0 =
        ring === 0 ? 38 : ring === 1 ? 24 : ring <= 2 ? 16 : ring <= 3 ? 11 : ring <= 4 ? 8 : 5;
      const bg0 =
        ring === 0 ? 30 : ring === 1 ? 18 : ring <= 2 ? 12 : ring <= 3 ? 9 : ring <= 4 ? 7 : 5;
      const bb0 =
        ring === 0 ? 22 : ring === 1 ? 14 : ring <= 2 ? 10 : ring <= 3 ? 7 : ring <= 4 ? 6 : 4;
      const rr = Math.floor((R + br0) * rgbFade);
      const gg = Math.floor((G + bg0) * rgbFade);
      const bb = Math.floor((B + bb0) * rgbFade);
      ctx.fillStyle = `rgba(${rr}, ${gg}, ${bb}, ${Math.min(1, a)})`;
      ctx.fillRect(x0 + dx, y0 + dy, 1, 1);
    }
  }

  /**
   * Named star: thick core + long axis arms.
   * Twinkle: 10s 整周期，亮度约 [0.52, 1]（与音符星对调下限，恒星不全灭）。
   */
  private drawProjectStar(px: number, py: number, hover: boolean, now: number, id: string): void {
    const ctx = this.ctx;
    const x0 = Math.floor(px);
    const y0 = Math.floor(py);
    const h = hashString32(id);
    const h2 = hashString32(`${id}::breath`);

    const TWINKLE_PERIOD_MS = 10000;
    const twPhaseRad =
      ((h % 62832) / 62832) * Math.PI * 2 + ((h >>> 14) % 628) * 0.01 + x0 * 0.019 + y0 * 0.017;
    const twinkle =
      0.76 + 0.24 * Math.cos((2 * Math.PI * now) / TWINKLE_PERIOD_MS + twPhaseRad);

    /** 慢呼吸，与 twinkle 不同频不同相，避免全局 tPulse 同步 */
    const pulseFreq = 0.0001 + (h2 % 65536) * 0.0000000048;
    const pulsePhase = ((h2 >>> 9) % 10000) * 0.0009 + (h % 127) * 0.02;
    const pulse = 0.88 + 0.12 * Math.sin(now * pulseFreq + pulsePhase);
    const base = (0.4 + pulse * 0.14) * (hover ? 1.06 : 1);

    /** 核心十字：分阶亮度，避免线性抹平 */
    const coreTier = (ring: number): number =>
      ring <= 0 ? 1 : ring <= 1 ? 0.78 : ring <= 2 ? 0.55 : 0.36;

    const a = (v: number): number => Math.min(1, v * twinkle);

    ctx.fillStyle = `rgba(205, 222, 245, ${a(base * coreTier(0))})`;
    ctx.fillRect(x0 - 2, y0 - 5, 5, 11);
    ctx.fillRect(x0 - 5, y0 - 2, 11, 5);

    ctx.fillStyle = `rgba(175, 200, 232, ${a(base * coreTier(1) * 0.72)})`;
    ctx.fillRect(x0 - 1, y0 - 6, 3, 1);
    ctx.fillRect(x0 - 1, y0 + 6, 3, 1);
    ctx.fillRect(x0 - 6, y0 - 1, 1, 3);
    ctx.fillRect(x0 + 6, y0 - 1, 1, 3);

    ctx.fillStyle = `rgba(190, 212, 242, ${a(base * coreTier(2) * 0.58)})`;
    ctx.fillRect(x0 - 3, y0 - 3, 1, 1);
    ctx.fillRect(x0 + 3, y0 - 3, 1, 1);
    ctx.fillRect(x0 - 3, y0 + 3, 1, 1);
    ctx.fillRect(x0 + 3, y0 + 3, 1, 1);

    /** 四轴：按距离分带阶跃衰减 + 每带略偏冷色，像素带状渐变 */
    const ARM_MIN = 7;
    const ARM_MAX = 17;
    const bandSkew = (h >>> 3) % 2;
    const armBands: readonly [number, number, number][] = [
      [168, 198, 236],
      [158, 190, 230],
      [148, 182, 224],
      [138, 174, 216],
      [128, 166, 208],
      [118, 158, 200],
    ];
    for (let d = ARM_MIN; d <= ARM_MAX; d++) {
      const step = Math.min(
        armBands.length - 1,
        Math.floor((d - ARM_MIN + bandSkew) / 2)
      );
      const armFade = [0.96, 0.72, 0.5, 0.32, 0.19, 0.1][step];
      const [cr, cg, cb] = armBands[step];
      const f = a(base * armFade * 0.54);
      ctx.fillStyle = `rgba(${cr}, ${cg}, ${cb}, ${f})`;
      ctx.fillRect(x0 - 2, y0 - d, 5, 1);
      ctx.fillRect(x0 - 2, y0 + d, 5, 1);
      ctx.fillRect(x0 - d, y0 - 2, 1, 5);
      ctx.fillRect(x0 + d, y0 - 2, 1, 5);
    }

    if (hover) {
      ctx.strokeStyle = "rgba(150, 190, 225, 0.38)";
      ctx.lineWidth = 1;
      ctx.strokeRect(x0 - 19, y0 - 19, 39, 39);
      ctx.strokeStyle = "rgba(120, 165, 205, 0.18)";
      ctx.strokeRect(x0 - 21, y0 - 21, 43, 43);
    }
  }
}
