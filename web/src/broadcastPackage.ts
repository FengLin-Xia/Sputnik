/**
 * Broadcast Package v0.1 — load meta, state, playlist, score from static broadcast/.
 * Falls back to embedded mock when fetches fail (offline / missing files).
 */

import type { BroadcastMeta, BroadcastState, Playlist, Score } from "./types";

export type LoadedBroadcastPackage = {
  meta: BroadcastMeta;
  state: BroadcastState;
  playlist: Playlist;
  score: Score;
  /** True when fetches failed and mock data was used */
  isMock: boolean;
};

async function fetchJson<T>(base: string, path: string): Promise<T> {
  const res = await fetch(`${base}${path}`);
  if (!res.ok) {
    throw new Error(`${path}: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/** Path relative to broadcast/ root, e.g. playlist segment `audio/segment_001.wav` */
export function resolveBroadcastAsset(base: string, relativePath: string): string {
  const p = relativePath.replace(/^\/+/, "");
  return `${base}broadcast/${p}`;
}

const MOCK_META: BroadcastMeta = {
  launchAt: "2026-04-18T00:00:00Z",
  generatedAt: "2026-04-18T00:00:00Z",
  orbitDay: 1,
  packageVersion: "0.1.0-mock",
  audioFormat: "wav",
};

const MOCK_STATE: BroadcastState = {
  signal: "stable",
  mode: "beacon",
  mood: "cold",
  transmission: "active",
};

const MOCK_PLAYLIST: Playlist = {
  segments: [
    {
      id: "segment_001",
      audio: "audio/segment_001.wav",
      score: "score.json",
      startOffset: 0,
    },
  ],
};

const MOCK_SCORE: Score = {
  bpm: 72,
  bars: 4,
  notes: [
    { t: 0, d: 1, p: 60, v: 0.8, track: 0 },
    { t: 2, d: 1, p: 64, v: 0.6, track: 1 },
    { t: 4, d: 2, p: 67, v: 0.5, track: 0 },
    { t: 6, d: 0.5, p: 72, v: 0.45, track: 0 },
  ],
};

function mockPackage(): LoadedBroadcastPackage {
  return {
    meta: MOCK_META,
    state: MOCK_STATE,
    playlist: MOCK_PLAYLIST,
    score: MOCK_SCORE,
    isMock: true,
  };
}

/**
 * Load the full v0.1 package (parallel fetch). On any failure, returns mock data
 * so local development without assets still runs.
 */
export async function loadBroadcastPackage(base: string): Promise<LoadedBroadcastPackage> {
  try {
    const [meta, state, playlist, score] = await Promise.all([
      fetchJson<BroadcastMeta>(base, "broadcast/meta.json"),
      fetchJson<BroadcastState>(base, "broadcast/state.json"),
      fetchJson<Playlist>(base, "broadcast/playlist.json"),
      fetchJson<Score>(base, "broadcast/score.json"),
    ]);
    if (!playlist.segments?.length) {
      throw new Error("playlist.json: segments must be non-empty");
    }
    return { meta, state, playlist, score, isMock: false };
  } catch (e) {
    console.warn("[Sputnik] broadcast package load failed, using mock:", e);
    return mockPackage();
  }
}

/** v0.1: single segment entry point */
export function primarySegment(playlist: Playlist): Playlist["segments"][0] {
  const s = playlist.segments[0];
  if (!s) {
    throw new Error("playlist has no segments");
  }
  return s;
}
