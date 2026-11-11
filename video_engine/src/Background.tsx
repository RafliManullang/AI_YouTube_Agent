import React from "react";
import {
  AbsoluteFill,
  Loop,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { ClipData, Palette } from "./types";

type Props = {
  palette: Palette;
  video?: string;
  variant?: number; // gaya latar (0 sampai 5), supaya tiap adegan dan tiap video tidak terlihat sama
  seed?: number;
  videoSeconds?: number; // panjang klip asli; kalau diisi, klip diputar ulang sampai adegan selesai
  clips?: ClipData[]; // beberapa klip bergantian (satu per kalimat); menggantikan "video" kalau ada
  footageStrength?: number; // makin besar, video asli makin jelas (0 sampai 1)
};

export const BACKGROUND_VARIANTS = 6;

const alpha = (v: number) =>
  Math.round(Math.min(1, Math.max(0, v)) * 255)
    .toString(16)
    .padStart(2, "0");

// Latar yang selalu bergerak: gradasi berputar, gumpalan cahaya, titik melayang, dan garis kotak
export const Background: React.FC<Props> = ({
  palette,
  video,
  variant = 0,
  seed = 0,
  footageStrength = 0.45,
  videoSeconds,
  clips,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  const phase = (seed % 97) * 0.37; // geser awal gerakan supaya tiap video beda

  const blobs = [0, 1, 2, 3, 4].map((i) => {
    const size = 650 + i * 110;
    const x = width / 2 + Math.sin(t * 0.5 + i * 1.7 + phase) * 380 - size / 2;
    const y = height / 2 + Math.cos(t * 0.4 + i * 2.3 + phase) * 700 - size / 2;
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

  const clip = video ? (
    <OffthreadVideo
      src={staticFile(video)}
      muted
      style={{
        width: "100%",
        height: "100%",
        objectFit: "cover",
        transform: `scale(${1.05 + t * 0.012})`,
      }}
    />
  ) : null;

  // Variasi 1: sinar yang berputar pelan dari tengah
  const rays = (
    <AbsoluteFill
      style={{
        background: `repeating-conic-gradient(from ${t * 8 + phase * 20}deg at 50% 38%, ${palette.accent}22 0deg 9deg, transparent 9deg 24deg)`,
        maskImage: "radial-gradient(circle at 50% 38%, #000 0%, transparent 78%)",
        WebkitMaskImage: "radial-gradient(circle at 50% 38%, #000 0%, transparent 78%)",
      }}
    />
  );

  // Variasi 2: gelombang berlapis yang bergeser
  const waves = (
    <svg width={width} height={height} style={{ position: "absolute", left: 0, top: 0 }}>
      {[0, 1, 2, 3, 4].map((i) => {
        const baseY = 260 + i * 330;
        const amp = 60 + i * 14;
        const pts: string[] = [];
        for (let x = 0; x <= width; x += 30) {
          const y = baseY + Math.sin(x / 150 + t * (0.9 + i * 0.25) + i * 1.3 + phase) * amp;
          pts.push(`${x},${y}`);
        }
        return (
          <polyline
            key={i}
            points={pts.join(" ")}
            fill="none"
            stroke={i % 2 ? palette.accent2 : palette.accent}
            strokeOpacity={0.3}
            strokeWidth={10}
            strokeLinecap="round"
          />
        );
      })}
    </svg>
  );

  // Variasi 3: titik-titik yang bergeser miring
  const dots = (
    <AbsoluteFill
      style={{
        backgroundImage: `radial-gradient(${palette.accent}55 4px, transparent 5px)`,
        backgroundSize: "70px 70px",
        backgroundPosition: `${t * 30}px ${t * -20}px`,
        maskImage: "linear-gradient(180deg, transparent, #000 30%, #000 70%, transparent)",
        WebkitMaskImage: "linear-gradient(180deg, transparent, #000 30%, #000 70%, transparent)",
      }}
    />
  );

  // Variasi 4: garis kecepatan yang melesat ke samping
  const streaks = (
    <>
      {Array.from({ length: 16 }, (_, i) => {
        const speed = 700 + (i % 5) * 260;
        const len = 260 + (i % 4) * 140;
        const x = width + len - ((t * speed + i * 413 + phase * 90) % (width + len * 2));
        const y = 120 + ((i * 197 + seed * 13) % (height - 240));
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: len,
              height: 6 + (i % 3) * 3,
              borderRadius: 6,
              background: `linear-gradient(90deg, transparent, ${i % 2 ? palette.accent2 : palette.accent})`,
              opacity: 0.35,
            }}
          />
        );
      })}
    </>
  );

  // Variasi 5: lingkaran yang memancar dari tengah
  const rings = (
    <>
      {[0, 1, 2, 3].map((i) => {
        const p = ((t * 0.28 + i / 4 + phase * 0.05) % 1 + 1) % 1;
        const size = 200 + p * 1700;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: width / 2 - size / 2,
              top: height * 0.38 - size / 2,
              width: size,
              height: size,
              borderRadius: "50%",
              border: `6px solid ${i % 2 ? palette.accent2 : palette.accent}`,
              opacity: 0.4 * (1 - p),
            }}
          />
        );
      })}
    </>
  );

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${160 + t * 6}deg, ${palette.bg1}, ${palette.bg2})`,
        overflow: "hidden",
      }}
    >
      {video || (clips && clips.length > 0) ? (
        <AbsoluteFill>
          {clips && clips.length > 0
            ? clips.map((c, i) => {
                const from = Math.round(c.start * fps);
                const len = Math.max(1, Math.round((c.end - c.start) * fps));
                const one = (
                  <OffthreadVideo
                    src={staticFile(c.file)}
                    muted
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                      transform: `scale(${1.05 + ((frame - from) / fps) * 0.015})`,
                    }}
                  />
                );
                return (
                  <Sequence key={i} from={from} durationInFrames={len}>
                    {c.seconds && c.seconds >= 1.5 ? (
                      <Loop durationInFrames={Math.max(1, Math.floor((c.seconds - 0.1) * fps))}>{one}</Loop>
                    ) : (
                      one
                    )}
                  </Sequence>
                );
              })
            : videoSeconds && videoSeconds >= 1.5 ? (
                <Loop durationInFrames={Math.max(1, Math.floor((videoSeconds - 0.1) * fps))}>{clip}</Loop>
              ) : (
                clip
              )}
          <AbsoluteFill
            style={{
              background: `linear-gradient(180deg, ${palette.bg1}${alpha(0.88 - footageStrength * 0.6)}, ${palette.bg2}${alpha(0.7 - footageStrength * 0.45)})`,
            }}
          />
        </AbsoluteFill>
      ) : null}

      {variant === 1 ? rays : variant === 2 ? waves : variant === 3 ? dots : variant === 4 ? streaks : variant === 5 ? rings : blobs}

      {variant === 0 || variant === 3 ? (
        <AbsoluteFill
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.05) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.05) 2px, transparent 2px)",
            backgroundSize: "90px 90px",
            backgroundPosition: `${t * 12}px ${t * 24}px`,
          }}
        />
      ) : null}

      {variant === 0 || variant === 5 ? particles : null}
    </AbsoluteFill>
  );
};
