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
  | "glitch";

export const SfxEnabled = createContext<boolean>(true);

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
  hiss: 0.3,
  tock: 0.22,
  glitch: 0.3,
};

type Props = {
  name: SfxName;
  at: number; // frame, dihitung dari awal adegan
  volume?: number;
};

export const Sfx: React.FC<Props> = ({ name, at, volume }) => {
  const enabled = useContext(SfxEnabled);
  if (!enabled) return null;
  return (
    <Sequence from={Math.max(0, Math.round(at))} durationInFrames={75}>
      <Audio src={staticFile(`sfx/${name}.wav`)} volume={volume ?? DEFAULT_VOLUME[name]} />
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
