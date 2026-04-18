import type { Note } from "./types";
import { SCORE_PITCH_MAX, SCORE_PITCH_MIN } from "./types";

export type MappedBroadcastStar = {
  x: number;
  y: number;
  noteIndex: number;
};

function hash01(key: string, salt: number): number {
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const x = Math.sin(h * 0.0001 + salt * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * Fixed plane mapping (scheme B): track bands, time flows within band, pitch sets depth.
 * Deterministic; swap-in friendly for future note-json.
 */
export function mapNotesToStarPositions(
  notes: Note[],
  beats: number,
  width: number,
  height: number,
  pad = 0.07
): MappedBroadcastStar[] {
  if (notes.length === 0 || width <= 0 || height <= 0) return [];

  const padX = width * pad;
  const padY = height * pad;
  const innerW = width - 2 * padX;
  const innerH = height - 2 * padY;

  const maxTrack = Math.max(...notes.map((n) => n.track), 0);
  const trackSpan = maxTrack + 1;
  const pSpan = SCORE_PITCH_MAX - SCORE_PITCH_MIN;

  return notes.map((n, i) => {
    const id = n.id ?? `n${i}`;
    const pitchNorm = Math.min(
      1,
      Math.max(0, (n.p - SCORE_PITCH_MIN) / pSpan)
    );
    const bandW = innerW / trackSpan;
    const u = beats > 0 ? Math.min(1, Math.max(0, n.t / beats)) : 0;
    const jitterX = (hash01(id, 1) - 0.5) * bandW * 0.14;
    const jitterY = (hash01(id, 2) - 0.5) * innerH * 0.07;
    const flow = (hash01(id, 3) - 0.5) * bandW * 0.04;

    const x = padX + n.track * bandW + u * bandW * 0.92 + bandW * 0.04 + jitterX + flow;
    const y = padY + (1 - pitchNorm) * innerH * 0.9 + innerH * 0.05 + jitterY;

    return { x, y, noteIndex: i };
  });
}
