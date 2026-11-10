import React, { createContext, useContext } from "react";
import { Audio, Sequence, staticFile } from "remotion";

// Efek suara dibuat sendiri oleh tools/buat_sfx.py (bebas hak cipta) dan disimpan di public/sfx
export type SfxName = "pop" | "whoosh" | "ding" | "tick";

export const SfxEnabled = createContext<boolean>(true);

const DEFAULT_VOLUME: Record<SfxName, number> = {
  pop: 0.28,
  whoosh: 0.32,
  ding: 0.3,
  tick: 0.2,
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
    <Sequence from={Math.max(0, Math.round(at))} durationInFrames={60}>
      <Audio src={staticFile(`sfx/${name}.wav`)} volume={volume ?? DEFAULT_VOLUME[name]} />
    </Sequence>
  );
};
