import React from "react";
import { Composition } from "remotion";
import { ShortsComp } from "./ShortsComp";
import { Thumbnail } from "./Thumbnail";
import { ShortsProps, ThumbnailProps } from "./types";

const FPS = 30;

// Contoh isi untuk pratinjau di Remotion Studio (npm run studio)
const defaultProps: ShortsProps = {
  audioUrl: "",
  themeIndex: 0,
  sfx: true,
  scenes: [
    {
      type: "flow",
      title: "Cara kerja lift",
      points: ["Motor menarik kabel", "Beban penyeimbang", "Rem pengaman"],
      start: 0,
      end: 6,
    },
    {
      type: "timeline",
      title: "Sejarah lift",
      points: [],
      items: [
        { label: "236 SM", value: "Archimedes membuat katrol" },
        { label: "1853", value: "Otis memasang rem pengaman" },
        { label: "1889", value: "Lift listrik pertama" },
        { label: "Kini", value: "Lift tercepat dunia" },
      ],
      start: 6,
      end: 13,
    },
    {
      type: "barchart",
      title: "Kecepatan lift",
      points: [],
      items: [
        { label: "Gedung kantor", value: 5 },
        { label: "Mal besar", value: 8 },
        { label: "Pencakar langit", value: 20 },
      ],
      unit: "m/detik",
      start: 13,
      end: 19,
    },
    {
      type: "compare",
      title: "Rem pengaman",
      points: [],
      items: [
        { label: "Tanpa rem", value: "Kabel putus, lift jatuh bebas" },
        { label: "Dengan rem", value: "Penjepit mengunci rel seketika" },
      ],
      start: 19,
      end: 25,
    },
    {
      type: "mindmap",
      title: "Rem aman",
      points: ["Sensor kecepatan", "Penjepit rel", "Pegas kuat", "Otomatis"],
      start: 25,
      end: 31,
    },
    {
      type: "counter",
      title: "Kecepatan lift",
      points: ["Super cepat", "Tetap aman"],
      number: 60,
      unit: "kilometer per jam",
      start: 31,
      end: 37,
    },
  ],
  words: [],
  durationInSeconds: 37,
};

const thumbnailDefaults: ThumbnailProps = {
  text: "LIFT JATUH BEBAS?",
  category: "Cara Kerja",
  themeIndex: 0,
};

export const Root: React.FC = () => {
  return (
    <>
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
      <Composition
        id="Thumbnail"
        component={Thumbnail}
        durationInFrames={60}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={thumbnailDefaults}
      />
    </>
  );
};
