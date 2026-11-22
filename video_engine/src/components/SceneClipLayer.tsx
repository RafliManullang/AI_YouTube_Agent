import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import type { SceneData } from "../types";

const VIDEO_EXT = /\.(mp4|webm|mov)$/i;
const FADE = 6; // bingkai pudar antar adegan (potong cepat, bukan dissolve panjang)

// Klip adegan aktif saja yang dihitung geraknya; dipisah supaya useCurrentFrame membaca frame lokal Sequence.
const ClipVisual: React.FC<{ scene: SceneData }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const dur = Math.max(1, scene.durationInFrames);
  const fadeIn = interpolate(frame, [0, FADE], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [dur - FADE, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  // Gerak dorong sangat pelan supaya gambar statis tidak terasa mati; klip video tidak diskalakan berlebihan.
  const scale = interpolate(frame, [0, dur], [1.02, 1.07], { extrapolateRight: "clamp" });
  const style: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    transform: `scale(${scale})`,
  };
  return (
    <AbsoluteFill style={{ opacity: Math.min(fadeIn, fadeOut), backgroundColor: "#0b0f19" }}>
      {!scene.clipPath ? (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 70 }}>
          <div style={{ color: "#94a3b8", fontFamily: "Arial, sans-serif", fontSize: 34, textAlign: "center", lineHeight: 1.4 }}>
            Klip {scene.id} belum disediakan
            <div style={{ fontSize: 24, marginTop: 16 }}>{scene.visualPrompt}</div>
          </div>
        </AbsoluteFill>
      ) : VIDEO_EXT.test(scene.clipPath) ? (
        <OffthreadVideo src={staticFile(scene.clipPath)} muted style={style} />
      ) : (
        <Img src={staticFile(scene.clipPath)} style={style} />
      )}
    </AbsoluteFill>
  );
};

// Lapisan latar utama: memutar klip/gambar per adegan sesuai startFrame + durationInFrames dari timing TTS.
export const SceneClipLayer: React.FC<{ scenes: SceneData[] }> = ({ scenes }) => (
  <>
    {scenes.map((scene) => (
      <Sequence key={scene.id} from={scene.startFrame} durationInFrames={Math.max(1, scene.durationInFrames)} premountFor={30}>
        <ClipVisual scene={scene} />
      </Sequence>
    ))}
  </>
);
