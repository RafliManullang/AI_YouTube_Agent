import React from "react";
import { Composition } from "remotion";
import { ShortsComp, ShortsProps } from "./ShortsComp";

const FPS = 30;

const defaultProps: ShortsProps = {
  audioUrl: "",
  images: [],
  words: [],
  durationInSeconds: 40,
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
