export type WordItem = {
  word: string;
  start: number;
  end: number;
};

export type SceneType = "flow" | "mindmap" | "counter";

export type SceneData = {
  type: SceneType;
  title: string;
  points: string[];
  number?: number;
  unit?: string;
  start: number; // detik
  end: number; // detik
  video?: string; // nama file video latar di folder public (opsional)
};

export type ShortsProps = {
  audioUrl: string;
  bgmUrl?: string;
  scenes: SceneData[];
  words: WordItem[];
  durationInSeconds: number;
};

export type Palette = {
  bg1: string;
  bg2: string;
  accent: string;
  accent2: string;
};

// Setiap adegan memakai warna yang berbeda supaya video terasa hidup
export const PALETTES: Palette[] = [
  { bg1: "#0f172a", bg2: "#1e3a8a", accent: "#22d3ee", accent2: "#a78bfa" },
  { bg1: "#1a0b2e", bg2: "#6d28d9", accent: "#fbbf24", accent2: "#f472b6" },
  { bg1: "#022c22", bg2: "#047857", accent: "#facc15", accent2: "#34d399" },
  { bg1: "#2a0a0a", bg2: "#b91c1c", accent: "#fde047", accent2: "#fb923c" },
  { bg1: "#0c1a3a", bg2: "#0e7490", accent: "#fb7185", accent2: "#67e8f9" },
  { bg1: "#1e1b4b", bg2: "#be185d", accent: "#5eead4", accent2: "#fcd34d" },
];

export const paletteFor = (index: number): Palette =>
  PALETTES[((index % PALETTES.length) + PALETTES.length) % PALETTES.length];
