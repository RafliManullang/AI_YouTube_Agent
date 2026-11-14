import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { Background } from "./Background";
import { ThumbnailProps, paletteFor } from "./types";

const TITLE_FONT = "Impact, 'Arial Black', sans-serif";
const OUTLINE = "0 8px 0 #000, 6px 6px 0 #000, -6px -6px 0 #000, 6px -6px 0 #000, -6px 6px 0 #000";
export const THUMB_LAYOUTS = 5;

// Gambar sampul tegak 1080x1920 (9:16). Latarnya adegan 3D dari video itu sendiri, dan tata letaknya
// berganti-ganti (5 gaya) supaya sampul tiap video tidak terlihat sama.
export const Thumbnail: React.FC<ThumbnailProps> = ({ text, category, themeIndex = 0, video, bg, layout = 0 }) => {
  const palette = paletteFor(1, themeIndex);
  const words = (text || "TAHUKAH KAMU").trim().toUpperCase().split(/\s+/).slice(0, 5);
  const longest = Math.max(...words.map((w) => w.length), 4);
  const mark = /\?\s*$/.test(text || "") ? "?" : "!";
  const L = ((layout % THUMB_LAYOUTS) + THUMB_LAYOUTS) % THUMB_LAYOUTS;

  const fit = (boxW: number, boxH: number, max = 250) =>
    Math.max(90, Math.min(max, Math.floor(boxW / (longest * 0.66)), Math.floor(boxH / (words.length * 1.05))));

  const background = bg ? (
    <AbsoluteFill>
      <Img src={staticFile(bg)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    </AbsoluteFill>
  ) : (
    <Background palette={palette} video={video} variant={1} footageStrength={0.7} />
  );

  const chip = (extra: React.CSSProperties = {}) => (
    <div
      style={{
        position: "absolute",
        padding: "12px 48px",
        borderRadius: 60,
        backgroundColor: palette.accent,
        color: palette.bg1,
        fontFamily: TITLE_FONT,
        fontSize: 60,
        letterSpacing: 3,
        textTransform: "uppercase",
        ...extra,
      }}
    >
      {category || "Fakta Sains"}
    </div>
  );

  const stack = (opts: { x: number; y: number; w: number; h: number; align?: "center" | "flex-start"; rotate?: number; max?: number }) => {
    const size = fit(opts.w, opts.h, opts.max);
    return (
      <div
        style={{
          position: "absolute",
          left: opts.x,
          top: opts.y,
          width: opts.w,
          height: opts.h,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: opts.align ?? "center",
          transform: `rotate(${opts.rotate ?? 0}deg)`,
        }}
      >
        {words.map((word, i) => (
          <span
            key={`${word}-${i}`}
            style={{
              fontFamily: TITLE_FONT,
              fontSize: size,
              lineHeight: 1.02,
              textTransform: "uppercase",
              whiteSpace: "nowrap",
              color: i === words.length - 1 ? palette.accent : "#ffffff",
              textShadow: OUTLINE,
            }}
          >
            {word}
          </span>
        ))}
      </div>
    );
  };

  // 0: teks besar di bawah, kategori di atas
  if (L === 0) {
    return (
      <AbsoluteFill>
        {background}
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0.78) 100%)" }} />
        {chip({ top: 170, left: "50%", transform: "translateX(-50%)" })}
        {stack({ x: 70, y: 1010, w: 940, h: 780 })}
      </AbsoluteFill>
    );
  }
  // 1: teks di atas, gambar terlihat bebas di bawah, tanda seru besar di pojok
  if (L === 1) {
    return (
      <AbsoluteFill>
        {background}
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.25) 42%, rgba(0,0,0,0) 62%)" }} />
        {chip({ bottom: 200, left: 70 })}
        {stack({ x: 70, y: 150, w: 940, h: 760, align: "flex-start" })}
        <div
          style={{
            position: "absolute",
            right: 60,
            bottom: 150,
            width: 260,
            height: 260,
            borderRadius: "50%",
            background: `linear-gradient(135deg, ${palette.accent}, ${palette.accent2})`,
            boxShadow: `0 0 90px ${palette.accent}cc`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: TITLE_FONT,
            fontSize: 210,
            color: palette.bg1,
            lineHeight: 1,
          }}
        >
          {mark}
        </div>
      </AbsoluteFill>
    );
  }
  // 2: panel miring berwarna di kiri bawah, teks agak miring
  if (L === 2) {
    return (
      <AbsoluteFill>
        {background}
        <AbsoluteFill style={{ background: "linear-gradient(0deg, rgba(0,0,0,0.35), rgba(0,0,0,0) 50%)" }} />
        <div
          style={{
            position: "absolute",
            left: -120,
            bottom: 150,
            width: 1320,
            height: 760,
            transform: "rotate(-6deg)",
            background: `linear-gradient(100deg, ${palette.accent} 0%, ${palette.accent2} 100%)`,
            boxShadow: "0 0 80px rgba(0,0,0,0.6)",
            opacity: 0.94,
          }}
        />
        {chip({ top: 160, left: 70, backgroundColor: "#ffffff" })}
        <div style={{ position: "absolute", left: 0, top: 0, width: 1080, height: 1920 }}>
          {stack({ x: 80, y: 1010, w: 920, h: 640, rotate: -6, max: 230 })}
        </div>
      </AbsoluteFill>
    );
  }
  // 3: sorotan lingkaran di tengah gambar, teks bertumpuk di kiri atas
  if (L === 3) {
    return (
      <AbsoluteFill>
        {background}
        <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 52%, rgba(0,0,0,0) 22%, rgba(0,0,0,0.72) 62%)" }} />
        <div
          style={{
            position: "absolute",
            left: 540 - 330,
            top: 900 - 330,
            width: 660,
            height: 660,
            borderRadius: "50%",
            border: `16px solid ${palette.accent}`,
            boxShadow: `0 0 70px ${palette.accent}, inset 0 0 70px ${palette.accent}88`,
          }}
        />
        {chip({ bottom: 170, left: "50%", transform: "translateX(-50%)" })}
        {stack({ x: 50, y: 120, w: 700, h: 520, align: "flex-start", max: 200 })}
      </AbsoluteFill>
    );
  }
  // 4: pita warna di belakang tiap kata, ala sorotan stabilo
  const size = fit(920, 700, 200);
  return (
    <AbsoluteFill>
      {background}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.6) 100%)" }} />
      {chip({ top: 160, right: 60 })}
      <div style={{ position: "absolute", left: 60, top: 1000, width: 960, display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 14 }}>
        {words.map((word, i) => (
          <span
            key={`${word}-${i}`}
            style={{
              fontFamily: TITLE_FONT,
              fontSize: size,
              lineHeight: 1.0,
              textTransform: "uppercase",
              whiteSpace: "nowrap",
              padding: "6px 30px",
              color: i % 2 ? palette.bg1 : "#ffffff",
              backgroundColor: i % 2 ? palette.accent : "rgba(0,0,0,0.78)",
              transform: `rotate(${i % 2 ? 1.5 : -1.5}deg)`,
              boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
            }}
          >
            {word}
          </span>
        ))}
      </div>
    </AbsoluteFill>
  );
};
