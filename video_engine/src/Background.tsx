import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Palette } from "./types";

type Props = {
  palette: Palette;
  video?: string;
};

// Latar yang selalu bergerak: gradasi berputar, gumpalan cahaya, titik melayang, dan garis kotak
export const Background: React.FC<Props> = ({ palette, video }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;

  const blobs = [0, 1, 2, 3, 4].map((i) => {
    const size = 650 + i * 110;
    const x = width / 2 + Math.sin(t * 0.5 + i * 1.7) * 380 - size / 2;
    const y = height / 2 + Math.cos(t * 0.4 + i * 2.3) * 700 - size / 2;
    const color = i % 2 === 0 ? palette.accent : palette.accent2;
    return (
      <div
        key={i}
        style={{
          position: "absolute",
          left: x,
          top: y,
          width: size,
          height: size,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${color}66 0%, ${color}00 70%)`,
        }}
      />
    );
  });

  const particles = Array.from({ length: 24 }, (_, i) => {
    const speed = 30 + (i % 6) * 14;
    const y = height + 40 - ((t * speed + i * 211) % (height + 80));
    const x = ((i * 197) % width) + Math.sin(t + i) * 24;
    const r = 4 + (i % 4) * 3;
    return (
      <div
        key={i}
        style={{
          position: "absolute",
          left: x,
          top: y,
          width: r * 2,
          height: r * 2,
          borderRadius: "50%",
          backgroundColor: i % 2 === 0 ? palette.accent : "#ffffff",
          opacity: 0.25 + (i % 3) * 0.12,
        }}
      />
    );
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${160 + t * 6}deg, ${palette.bg1}, ${palette.bg2})`,
        overflow: "hidden",
      }}
    >
      {video ? (
        <AbsoluteFill>
          <OffthreadVideo
            src={staticFile(video)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
          <AbsoluteFill
            style={{
              background: `linear-gradient(180deg, ${palette.bg1}d9, ${palette.bg2}a6)`,
            }}
          />
        </AbsoluteFill>
      ) : null}

      {blobs}

      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.05) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.05) 2px, transparent 2px)",
          backgroundSize: "90px 90px",
          backgroundPosition: `${t * 12}px ${t * 24}px`,
        }}
      />

      {particles}
    </AbsoluteFill>
  );
};
