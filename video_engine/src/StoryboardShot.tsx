import React from "react";
import { Img, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Satu adegan storyboard ala channel edukasi: ilustrasi cel-shaded layar penuh yang
 * dianimasikan berlapis - kamera Ken Burns + pukulan zoom di kata pemicu, panah gaya
 * yang mengalir terus selama adegan berdampak, judul adegan besar di atas, dan badge
 * angka kunci yang meletup tepat di frame kata pemicu. Semua teks digambar di sini -
 * gambar AI-nya sendiri bebas teks. Transisi whip antar-adegan diatur ShortsComp.
 */
export const StoryboardShot: React.FC<{
  src: string;
  title: string;
  hud?: { load?: string; force?: string };
  forceLevel?: number;
  index: number;
  startFrame: number;
  endFrame: number;
  triggerFrame: number;
  clean?: boolean;
}> = ({ src, title, hud, forceLevel = 1, index, startFrame, endFrame, triggerFrame, clean }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = Math.max(1, endFrame - startFrame);
  const age = Math.min(len, Math.max(0, frame - startFrame));
  const p = age / len;
  // Ken Burns: zoom masuk pelan + drift menyamping bergantian arah tiap adegan agar tidak monoton.
  const dir = index % 2 === 0 ? 1 : -1;
  // Pukulan kamera di kata pemicu: zoom membesar cepat lalu mengendap (terasa "menghantam" bersamaan narasi).
  const sinceTrig = frame - triggerFrame;
  const punch = sinceTrig >= 0 && sinceTrig < 14 ? 1 + 0.035 * Math.sin((sinceTrig / 14) * Math.PI) : 1;
  const scale = (1.07 + 0.09 * p) * punch;
  const x = dir * (p - 0.5) * 34;
  const y = -12 * p;
  const titleIn = spring({ frame: age, fps, config: { damping: 15, stiffness: 130 } });
  const badgeIn = spring({ frame: Math.max(0, frame - triggerFrame), fps, config: { damping: 11, stiffness: 160 } });
  const badgeText = hud?.load || hud?.force || "";
  // Panah gaya mengalir: hidup setelah kata pemicu pada adegan berdampak (angka/gaya disebut narator).
  const flowOn = !clean && sinceTrig >= 0 && (!!badgeText || forceLevel >= 2);
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", background: "#0b2235" }}>
      <Img
        src={staticFile(src)}
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: `translate(${x}px, ${y}px) scale(${scale})` }}
      />
      {/* Panah gaya bergerak naik berulang (chevron mengalir) - motion graphics di atas gambar diam. */}
      {flowOn ? (
        <svg width="100%" height="100%" viewBox="0 0 1080 1920" style={{ position: "absolute", inset: 0 }}>
          {[0, 1, 2].map((i) => {
            const rise = ((frame * 3.2 + i * 90) % 270) / 270; // 0..1 naik berulang
            return (
              <path
                key={i}
                d={`M470 ${1180 - rise * 240} L540 ${1110 - rise * 240} L610 ${1180 - rise * 240}`}
                fill="none"
                stroke={hud?.force ? "#fb923c" : "#2dd4bf"}
                strokeWidth="20"
                strokeLinecap="round"
                opacity={0.25 + 0.65 * Math.sin(rise * Math.PI)}
              />
            );
          })}
        </svg>
      ) : null}
      {/* Judul adegan besar di atas, gaya teks hook channel edukasi. */}
      {!clean && title ? (
        <div
          style={{
            position: "absolute", left: 54, right: 54, top: 150,
            opacity: Math.min(1, titleIn * 2),
            transform: `translateY(${(1 - titleIn) * -26}px)`,
            fontFamily: "Impact, 'Arial Black', sans-serif", fontSize: 72, lineHeight: 1.04,
            letterSpacing: 1, color: "#ffffff", textTransform: "uppercase",
            textShadow: "0 5px 0 #000, 3px 3px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000",
          }}
        >
          {title}
          <div style={{ width: 150, height: 12, background: "#f97316", marginTop: 14, borderRadius: 6 }} />
        </div>
      ) : null}
      {/* Badge angka kunci: meletup di kata pemicu, bukan dari awal adegan. */}
      {!clean && badgeText ? (
        <div
          style={{
            position: "absolute", right: 48, top: "36%",
            transform: `scale(${0.6 + 0.4 * badgeIn})`, opacity: badgeIn,
            background: "rgba(6,24,32,0.88)", border: "3px solid #2dd4bf", borderRadius: 18,
            padding: "16px 24px", color: "#ffffff", fontFamily: "Arial, sans-serif", textAlign: "center",
          }}
        >
          <div style={{ color: "#2dd4bf", fontSize: 34, lineHeight: 1 }}>▲</div>
          <div style={{ fontSize: 46, fontWeight: 800, lineHeight: 1.1 }}>{badgeText}</div>
        </div>
      ) : null}
      {/* Vignette bawah tipis agar subtitle tetap terbaca di atas gambar terang. */}
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to top, rgba(0,0,0,0.42) 0%, rgba(0,0,0,0) 26%)" }} />
    </div>
  );
};
