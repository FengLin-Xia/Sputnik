/** Sputnik Score v0.1 — see Sputnik_Score_Spec_PrV01.md */
export const SCORE_PITCH_MIN = 48;
export const SCORE_PITCH_MAX = 84;

export type Note = {
  id?: string;
  /** Start on fixed grid (same units as d). */
  t: number;
  /** Duration in grid units; v0.1 suggests [0.25, 4]. */
  d: number;
  /** MIDI-style pitch; v0.1 suggests [48, 84]. */
  p: number;
  /** Velocity / volume (0, 1]. */
  v: number;
  /** 0–3: beacon, drone, static, relay. */
  track: number;
};

export type Score = {
  /** v0.1 suggests 50–100. */
  bpm: number;
  /** v0.1: 4 or 8 bars. */
  bars: number;
  notes: Note[];
};

/** Weak status copy for the receiver (v0.1 package). */
export type BroadcastState = {
  signal: string;
  mode: string;
  mood?: string;
  transmission?: string;
};

/** Time anchor for since-launch / orbit day (v0.1 package). */
export type BroadcastMeta = {
  launchAt: string;
  generatedAt: string;
  orbitDay: number;
  packageVersion: string;
  audioFormat: string;
};

export type ProjectStar = {
  id: string;
  label: string;
  x: number;
  y: number;
  url?: string;
};

export type ProjectsFile = {
  projects: ProjectStar[];
};

/** broadcast/playlist.json (v0.1 single segment) */
export type PlaylistSegment = {
  id: string;
  /** Path relative to broadcast/ root, e.g. audio/segment_001.wav */
  audio: string;
  /** Score filename within package (v0.1: score.json) */
  score: string;
  /** Offset in beats on the score timeline where this segment starts */
  startOffset: number;
};

export type Playlist = {
  segments: PlaylistSegment[];
};
