import React, { createContext, useContext } from "react";
import { Audio, Sequence, staticFile } from "remotion";
import { AmbienceName } from "./types";

// Efek suara dibuat sendiri oleh tools/buat_sfx.py (bebas hak cipta) dan disimpan di public/sfx
export type SfxName =
  | "pop"
  | "whoosh"
  | "ding"
  | "tick"
  | "screech"
  | "impact"
  | "beep"
  | "riser"
  | "click"
  | "clank"
  | "hiss"
  | "tock"
  | "glitch"
  | "zap"
  | "thud"
  | "sizzle"
  | "bubble"
  | "bell"
  | "chain"
  | "swell"
  | "creak";

export const SfxEnabled = createContext<boolean>(true);
// Angka acak per video: dipakai untuk memilih variasi bunyi supaya tiap video terdengar beda
export const SfxSeed = createContext<number>(0);
// Pilihan variasi bunyi tiap jenis efek untuk video ini (dibuat agen supaya beda dari video sebelumnya)
export const SfxMap = createContext<Record<string, number>>({});

// Bunyi momen puncak yang cocok dengan jenis animasinya
export const KEY_SOUNDS: SfxName[] = ["clank", "hiss", "zap", "thud", "sizzle", "bubble", "ding", "impact", "glitch", "riser", "bell", "chain", "swell", "creak"];
const BY_MECHANISM: Record<string, SfxName> = {
  katrol_lift: "clank",
  roda_gigi: "clank",
  piston: "thud",
  tuas: "thud",
  aliran: "bubble",
  panas: "sizzle",
  rangkaian: "zap",
  tekanan: "hiss",
  nozel_bensin: "hiss",
  roda_kerucut: "clank",
  jangkar_rantai: "chain",
  eskalator: "clank",
  kunci_silinder: "clank",
  sprinkler: "sizzle",
  venturi: "hiss",
  eddy_current: "zap",
  jembatan: "creak",
  airbag: "thud",
  mesin_ice: "thud",
  ball_socket: "click",
  capillary: "bubble",
  pressure_leak: "swell",
  sosrobahu: "swell",
  jembatan_geser: "creak",
  mobil_dongkrak: "clank",
};
export const climaxSound = (scene: { sfx?: string; mechanism?: string; type?: string }): SfxName => {
  if (scene.sfx && (KEY_SOUNDS as string[]).includes(scene.sfx)) return scene.sfx as SfxName;
  if (scene.mechanism && BY_MECHANISM[scene.mechanism]) return BY_MECHANISM[scene.mechanism];
  return scene.type === "story" ? "bell" : "impact";
};

const VARIANTS = ["", "_b", "_c", "_d"];
const hashPick = (seed: number, name: string, at: number) => {
  let h = (seed * 2654435761) >>> 0;
  for (let i = 0; i < name.length; i++) h = Math.imul(h ^ name.charCodeAt(i), 16777619) >>> 0;
  h = Math.imul(h ^ Math.round(at), 2246822519) >>> 0;
  return h;
};

const DEFAULT_VOLUME: Record<SfxName, number> = {
  pop: 0.28,
  whoosh: 0.32,
  ding: 0.3,
  tick: 0.2,
  screech: 0.3,
  impact: 0.5,
  beep: 0.22,
  riser: 0.3,
  click: 0.3,
  clank: 0.34,
  chain: 0.34,
  swell: 0.4,
  creak: 0.3,
  hiss: 0.3,
  tock: 0.22,
  glitch: 0.3,
  zap: 0.3,
  thud: 0.4,
  sizzle: 0.26,
  bubble: 0.3,
  bell: 0.3,
};

type Props = {
  name: SfxName;
  at: number; // frame, dihitung dari awal adegan
  volume?: number;
};

export const Sfx: React.FC<Props> = ({ name, at, volume }) => {
  const enabled = useContext(SfxEnabled);
  const seed = useContext(SfxSeed);
  const map = useContext(SfxMap);
  if (!enabled) return null;
  // variasi dasar ditentukan agen per video (beda dari video sebelumnya); posisi bunyi menggeser satu langkah
  const h = hashPick(seed, name, at);
  const base = map[name] ?? h % VARIANTS.length;
  const variant = VARIANTS[(base + (h % 2)) % VARIANTS.length];
  const gain = 0.88 + ((h >>> 8) % 25) / 100;
  return (
    <Sequence from={Math.max(0, Math.round(at))} durationInFrames={90}>
      <Audio src={staticFile(`sfx/${name}${variant}.wav`)} volume={(volume ?? DEFAULT_VOLUME[name]) * gain} />
    </Sequence>
  );
};

const AMBIENCE_FILE: Record<string, { file: string; volume: number }> = {
  angin: { file: "wind", volume: 0.2 },
  mesin: { file: "rumble", volume: 0.22 },
  air: { file: "water", volume: 0.2 },
};

type AmbienceProps = {
  sound?: AmbienceName;
  lengthFrames: number;
  fps: number;
};

// Suara latar yang diputar berulang selama satu adegan, masuk dan keluar dengan halus.
// "gesekan" dan "benturan" bukan suara berulang, jadi dimainkan sekali di awal adegan.
export const Ambience: React.FC<AmbienceProps> = ({ sound, lengthFrames, fps }) => {
  const enabled = useContext(SfxEnabled);
  if (!enabled || !sound || sound === "hening") return null;

  if (sound === "gesekan") return <Sfx name="screech" at={Math.round(fps * 0.5)} />;
  if (sound === "benturan") return <Sfx name="impact" at={Math.round(fps * 0.35)} />;

  const info = AMBIENCE_FILE[sound];
  if (!info) return null;
  const fade = Math.round(fps * 0.5);
  return (
    <Audio
      src={staticFile(`sfx/${info.file}.wav`)}
      loop
      volume={(f) => {
        const inn = Math.min(1, f / fade);
        const out = Math.min(1, Math.max(0, (lengthFrames - f) / fade));
        return info.volume * Math.min(inn, out);
      }}
    />
  );
};
