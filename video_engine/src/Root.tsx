import React from "react";
import { Composition } from "remotion";
import { ShortsComp } from "./ShortsComp";
import { ShortsProps } from "./types";

const FPS = 30;

// Contoh isi untuk pratinjau di Remotion Studio (npm run studio)
const defaultProps: ShortsProps = {
  audioUrl: "",
  scenes: [
    {
      type: "flow",
      title: "Cara kerja lift",
      points: ["Motor menarik kabel", "Beban penyeimbang", "Rem pengaman"],
      start: 0,
      end: 8,
    },
    {
      type: "mindmap",
      title: "Rem aman",
      points: ["Sensor kecepatan", "Penjepit rel", "Pegas kuat", "Otomatis"],
      start: 8,
      end: 16,
    },
    {
      type: "counter",
      title: "Kecepatan lift",
      points: ["Super cepat", "Tetap aman"],
      number: 60,
      unit: "kilometer per jam",
      start: 16,
      end: 24,
    },
  ],
  words: [],
  durationInSeconds: 24,
};

export const Root: React.FC = () => {
  return (
    <Composition
      id="ShortsComp"
      component={ShortsComp}
      durationInFrames={FPS * defaultProps.durationInSeconds}
      fps={FPS}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
      // Panjang video mengikuti durasi suara yang dikirim dari main_agent.py,
      // jadi tidak perlu lagi memasukkan angka durasi lewat perintah terminal.
      calculateMetadata={({ props }) => {
        const seconds = Math.max(5, props.durationInSeconds || 40);
        return { durationInFrames: Math.ceil(seconds * FPS) };
      }}
    />
  );
};
