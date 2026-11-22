import React from "react";
import { Composition } from "remotion";
import { ShortsComp } from "./ShortsComp";
import { Thumbnail } from "./Thumbnail";
import { ShortsProps, ThumbnailProps } from "./types";
import { validateShortsProps } from "./schemas/sceneSchema";

const FPS = 30;

// Contoh isi untuk pratinjau di Remotion Studio (npm run studio)
const defaultProps: ShortsProps = {
  audioUrl: "",
  sfx: true,
  hookQuestion: "Kok bisa mati sendiri?",
  hookHighlight: "mati sendiri",
  scenes: [
    { id: "scene_01", narration: "Contoh narasi adegan pertama.", visualPrompt: "Photorealistic vertical 9:16 shot of the object in its real environment, cinematic light", clipPath: "", startFrame: 0, durationInFrames: 180 },
    { id: "scene_02", narration: "Contoh narasi adegan kedua.", visualPrompt: "Photorealistic vertical 9:16 close-up of the key moving part in action", clipPath: "", startFrame: 180, durationInFrames: 180, sfx: "clank" },
  ],
  words: [],
  durationInSeconds: 12,
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
        calculateMetadata={({ props }: { props: ShortsProps }) => {
          // Pagar kedua: data yang tidak lolos skema dihentikan di sini, sebelum satu bingkai pun dirender.
          const report = validateShortsProps(props);
          if (!report.ok) throw new Error("Data video ditolak skema: " + report.errors.slice(0, 5).join("; "));
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
