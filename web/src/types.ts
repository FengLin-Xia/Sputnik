export type Note = {
  id?: string;
  t: number;
  d: number;
  p: number;
  v: number;
  track: number;
};

export type Score = {
  bpm: number;
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
};

export type ProjectsFile = {
  projects: ProjectStar[];
};
