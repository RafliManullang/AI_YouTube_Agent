export type WordItem = {
  word: string;
  start: number;
  end: number;
  who?: "shela" | "flay"; // siapa yang bicara (mode obrolan)
  emphasis?: boolean; // kata kunci yang ditonjolkan di subtitle
};

export type SceneType =
  | "flow"
  | "mindmap"
  | "counter"
  | "timeline"
  | "barchart"
  | "compare"
  | "gauge"
  | "footage"
  | "cutaway" // potongan melintang / tembus pandang
  | "microscale" // zoom dari benda utuh ke tingkat mikro
  | "story" // ilustrasi buku cerita dengan karakter berekspresi
  | "question" // tanda tanya besar berdenyut (hook yang melawan akal sehat)
  | "mechanism"; // animasi cara kerja benda (lift, roda gigi, piston, ...)

export type MechanismName =
  | "katrol_lift"
  | "roda_gigi"
  | "piston"
  | "tuas"
  | "aliran"
  | "panas"
  | "rangkaian"
  | "tekanan"
  | "nozel_bensin"
  | "roda_kerucut";

export type ClipData = {
  file: string; // nama file video di folder public
  start: number; // detik, relatif terhadap awal adegan
  end: number;
  seconds: number; // panjang klip asli
};

// Suara latar tiap adegan (angin, deru mesin, dan seterusnya)
export type AmbienceName = "angin" | "gesekan" | "benturan" | "mesin" | "air" | "hening";

// Dipakai oleh timeline (label = tahun, value = kejadian), barchart (label = nama, value = angka),
// dan compare (label = judul sisi, value = isi)
export type SceneItem = {
  label: string;
  value: string | number;
};

export type Vec3 = [number, number, number];
export type SimObject = {
  id: string;
  shape: "box" | "cylinder" | "sphere" | "cone" | "torus" | "tube" | "gear" | "plate" | "rope" | "text";
  text?: string; // shape text: tulisan 3D (size: tinggi huruf, ketebalan)
  pivot?: Vec3; // titik putar terhadap pusat benda (untuk rotate)
  pos: Vec3;
  size: Vec3; // box/plate: lebar,tinggi,tebal; cylinder/tube/cone: radius,tinggi,-; sphere: radius; torus: radius besar,radius kecil; gear: radius,tebal,jumlah gigi
  rot?: Vec3; // derajat
  color?: string;
  material?: "metal" | "glass" | "liquid" | "rubber" | "glow" | "plastic" | "rust";
  opacity?: number;
  label?: string;
  link?: [string, string]; // rope: dihubungkan dari benda pertama ke benda kedua
  linkOff?: [Vec3, Vec3]; // rope: pergeseran titik ujung terhadap pusat tiap benda
};
export type SimMotion = {
  target: string;
  kind: "move" | "spin" | "pulse" | "color" | "rotate" | "grow" | "appear" | "count";
  to?: Vec3; // untuk move: posisi akhir
  axis?: "x" | "y" | "z"; // untuk spin
  speed?: number; // putaran per detik (spin) atau denyut per detik (pulse)
  t0?: number; // mulai (0 sampai 1 dari panjang adegan)
  t1?: number; // selesai
  value?: number; // untuk count: angka akhir yang dihitung naik
  suffix?: string; // untuk count: satuan di belakang angka
  angle?: number; // untuk rotate: sudut akhir (derajat) pada sumbu axis
  color?: string; // untuk color: warna akhir
  loop?: boolean; // move bolak-balik
  ease?: "spring"; // grow dengan hentakan pegas
};
export type SimFlow = {
  path: Vec3[];
  color?: string;
  count?: number;
  size?: number;
  speed?: number; // siklus per detik
  kind?: "water" | "mud" | "oil" | "light"; // jenis aliran (kalau kosong dibaca dari warna)
  t0?: number;
  t1?: number;
};
export type SimSpec = {
  objects: SimObject[];
  motions?: SimMotion[];
  flows?: SimFlow[];
  floor?: number; // tinggi lantai (y) bila ingin ada alas bergaris
  cutaway?: boolean; // belah benda: sisi depan dibuang supaya bagian dalam terlihat
  cam?: { dist?: number; height?: number; orbit?: number; target?: Vec3; fov?: number };
};

export type SceneData = {
  sim?: SimSpec | null; // spesifikasi animasi 3D (opsional)
  type: SceneType;
  title: string;
  points: string[];
  items?: SceneItem[];
  number?: number;
  unit?: string;
  start: number; // detik
  end: number; // detik
  video?: string; // nama file video latar di folder public (opsional)
  videoSeconds?: number; // panjang klip video latar (detik)
  artUrls?: string[];
  model?: string; // berkas model 3D (.glb) di folder public
  sfx?: string; // bunyi momen puncak (clank, hiss, zap, ...)
  clips?: ClipData[]; // beberapa klip bergantian dalam satu adegan (satu per kalimat)
  variant?: "device" | "ground"; // untuk cutaway
  mechanism?: MechanismName | ""; // untuk mechanism
  mood?: "senang" | "takut" | "kaget" | "sedih" | "tegang" | "bangga"; // untuk story
  weather?: "cerah" | "hujan" | "salju" | "badai" | "malam" | "kabut"; // untuk story
  sound?: AmbienceName;
};

export type ShortsProps = {
  clean?: boolean; // tanpa judul, label, dan subtitle (untuk latar thumbnail)
  thumbBg?: string;
  audioUrl: string;
  bgmUrl?: string;
  scenes: SceneData[];
  words: WordItem[];
  durationInSeconds: number;
  themeIndex?: number; // pilihan tema warna (lihat THEMES)
  sfx?: boolean; // efek suara, bawaan menyala
  bgSeed?: number; // angka acak supaya gaya latar beda tiap video
  sfxMap?: Record<string, number>; // pilihan variasi bunyi per jenis efek (beda dari video sebelumnya)
};

export type ThumbnailProps = {
  text: string;
  category: string;
  themeIndex?: number;
  video?: string;
  bg?: string; // gambar latar dari videonya sendiri (di folder public)
  layout?: number; // 0 sampai 4: tata letak berbeda tiap video
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
  {
    // nuansa foto tua dan kertas kuno, untuk cerita sejarah
    name: "sepia",
    palettes: [
      { bg1: "#2b1d10", bg2: "#8a5a2b", accent: "#f4d58d", accent2: "#d97757" },
      { bg1: "#241a12", bg2: "#6b4a2e", accent: "#f2c94c", accent2: "#c9a66b" },
      { bg1: "#33210f", bg2: "#a1662f", accent: "#ffe3a3", accent2: "#e08e45" },
    ],
  },
];

export const paletteFor = (index: number, themeIndex = 0): Palette => {
  // adegan bernomor ganjil memakai tema pendamping yang warnanya berbeda, supaya video tidak satu warna dari awal sampai akhir
  const shift = index % 2 === 1 ? 3 : 0;
  const safeTheme = THEMES[(((themeIndex + shift) % THEMES.length) + THEMES.length) % THEMES.length];
  const list = safeTheme.palettes;
  return list[((index % list.length) + list.length) % list.length];
};
