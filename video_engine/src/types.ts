export type WordItem = {
  word: string;
  start: number;
  end: number;
};

export type SceneType =
  | "flow"
  | "mindmap"
  | "counter"
  | "timeline"
  | "barchart"
  | "compare";

// Dipakai oleh timeline (label = tahun, value = kejadian), barchart (label = nama, value = angka),
// dan compare (label = judul sisi, value = isi)
export type SceneItem = {
  label: string;
  value: string | number;
};

export type SceneData = {
  type: SceneType;
  title: string;
  points: string[];
  items?: SceneItem[];
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
  themeIndex?: number; // pilihan tema warna (lihat THEMES)
  sfx?: boolean; // efek suara, bawaan menyala
};

export type ThumbnailProps = {
  text: string;
  category: string;
  themeIndex?: number;
  video?: string;
};

export type Palette = {
  bg1: string;
  bg2: string;
  accent: string;
  accent2: string;
};

export type Theme = {
  name: string;
  palettes: Palette[];
};

// Urutan tema HARUS sama dengan THEME_NAMES di main_agent.py
export const THEMES: Theme[] = [
  {
    name: "pelangi",
    palettes: [
      { bg1: "#0f172a", bg2: "#1e3a8a", accent: "#22d3ee", accent2: "#a78bfa" },
      { bg1: "#1a0b2e", bg2: "#6d28d9", accent: "#fbbf24", accent2: "#f472b6" },
      { bg1: "#022c22", bg2: "#047857", accent: "#facc15", accent2: "#34d399" },
      { bg1: "#2a0a0a", bg2: "#b91c1c", accent: "#fde047", accent2: "#fb923c" },
      { bg1: "#0c1a3a", bg2: "#0e7490", accent: "#fb7185", accent2: "#67e8f9" },
      { bg1: "#1e1b4b", bg2: "#be185d", accent: "#5eead4", accent2: "#fcd34d" },
    ],
  },
  {
    name: "neon",
    palettes: [
      { bg1: "#0f172a", bg2: "#1e3a8a", accent: "#22d3ee", accent2: "#a78bfa" },
      { bg1: "#0b1020", bg2: "#312e81", accent: "#67e8f9", accent2: "#f0abfc" },
      { bg1: "#101a33", bg2: "#155e75", accent: "#a5f3fc", accent2: "#c4b5fd" },
    ],
  },
  {
    name: "senja",
    palettes: [
      { bg1: "#2b0a1f", bg2: "#9a3412", accent: "#fdba74", accent2: "#f472b6" },
      { bg1: "#1f0a2e", bg2: "#be185d", accent: "#fcd34d", accent2: "#fb923c" },
      { bg1: "#3b0d0d", bg2: "#c2410c", accent: "#fde68a", accent2: "#fda4af" },
    ],
  },
  {
    name: "hutan",
    palettes: [
      { bg1: "#052e16", bg2: "#15803d", accent: "#bef264", accent2: "#5eead4" },
      { bg1: "#0a2a1f", bg2: "#0f766e", accent: "#fde047", accent2: "#86efac" },
      { bg1: "#14210f", bg2: "#4d7c0f", accent: "#fbbf24", accent2: "#a7f3d0" },
    ],
  },
  {
    name: "samudra",
    palettes: [
      { bg1: "#041a33", bg2: "#0369a1", accent: "#7dd3fc", accent2: "#5eead4" },
      { bg1: "#06223a", bg2: "#0e7490", accent: "#fcd34d", accent2: "#67e8f9" },
      { bg1: "#0b1f4a", bg2: "#1d4ed8", accent: "#a5f3fc", accent2: "#fda4af" },
    ],
  },
  {
    name: "emas",
    palettes: [
      { bg1: "#1c1209", bg2: "#78350f", accent: "#fcd34d", accent2: "#fdba74" },
      { bg1: "#22150b", bg2: "#92400e", accent: "#fde68a", accent2: "#f59e0b" },
      { bg1: "#1a1410", bg2: "#57534e", accent: "#fbbf24", accent2: "#e7e5e4" },
    ],
  },
  {
    name: "kosmik",
    palettes: [
      { bg1: "#0b0620", bg2: "#4c1d95", accent: "#c4b5fd", accent2: "#67e8f9" },
      { bg1: "#120a2e", bg2: "#7e22ce", accent: "#f0abfc", accent2: "#fde047" },
      { bg1: "#0a0f2c", bg2: "#3730a3", accent: "#a5b4fc", accent2: "#fb7185" },
    ],
  },
];

export const paletteFor = (index: number, themeIndex = 0): Palette => {
  const safeTheme = THEMES[((themeIndex % THEMES.length) + THEMES.length) % THEMES.length];
  const list = safeTheme.palettes;
  return list[((index % list.length) + list.length) % list.length];
};
