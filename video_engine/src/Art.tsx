import React, { useContext } from "react";
import { AbsoluteFill, Img, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { DiagramProps, HideChrome, SceneTitle, TITLE_FONT } from "./Diagrams";
import { Sfx, climaxSound } from "./Sfx";

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const CLIMAX_FRACTION = 0.62;

// Adegan berbasis ilustrasi AI: gambar potongan benda yang detail + gerak kamera, kilau cahaya,
// partikel, label yang muncul berurutan, serta getar dan kilat di momen klimaks.
export const ArtScene: React.FC<DiagramProps> = ({ scene, palette, lengthFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const urls = scene.artUrls ?? [];
  const len = Math.max(1, lengthFrames);
  const t = frame / fps;
  const dramatic = scene.type === "mechanism" || scene.type === "cutaway";
  const c = Math.round(len * CLIMAX_FRACTION);
  const since = frame - c;

  // gerak kamera: perbesar pelan, lalu dorongan kecil saat klimaks
  const prog = clamp01(frame / len);
  const punch = dramatic && since >= 0 ? 0.045 * Math.max(0, 1 - since / 20) : 0;
  const slow = dramatic && frame >= c - 10 && frame <= c + 25 ? 0.5 : 1;
  const zoom = 1.05 + 0.12 * prog + punch;
  const dir = (scene.start * 7) % 2 > 1 ? 1 : -1;
  const panX = dir * (-30 + 60 * prog);
  const panY = -20 + 40 * prog * (dir > 0 ? 1 : -1);
  const shakeAmp = dramatic && since >= 0 && since < 12 ? (1 - since / 12) * 16 : 0;
  const sx = shakeAmp * Math.sin(frame * 3.1);
  const sy = shakeAmp * Math.cos(frame * 2.3);
  const flash = dramatic && since >= 0 && since < 8 ? 0.7 * (1 - since / 8) : 0;

  // dua gambar: yang kedua muncul (silang pudar) setelah klimaks
  const fade = urls.length > 1 ? clamp01((frame - c) / Math.round(fps * 0.35)) : 0;

  const hidden = useContext(HideChrome);
  const labels = hidden ? [] : (scene.items?.length ? scene.items.map((i) => String(i.label)) : scene.points ?? []).slice(0, 4);
  const step = Math.max(0.55, ((len / fps) * 0.5) / Math.max(1, labels.length));
  void slow;

  // kilau cahaya yang menyapu tiap beberapa detik
  const sweepPhase = (t % 3.2) / 3.2;
  const sweepX = -600 + sweepPhase * 2300;

  return (
    <AbsoluteFill style={{ backgroundColor: "#070b16", overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          transform: `translate(${panX + sx}px, ${panY + sy}px) scale(${zoom})`,
          transformOrigin: "50% 45%",
        }}
      >
        {urls.map((u, i) => (
          <Img
            key={u}
            src={staticFile(u)}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              objectFit: "cover",
              opacity: i === 0 ? 1 : fade,
            }}
          />
        ))}
      </AbsoluteFill>

      {/* setelah klimaks: bagian dalam memerah sebentar, tanda tekanan */}
      {dramatic && since >= 0 ? (
        <AbsoluteFill
          style={{
            background: "radial-gradient(circle at 50% 38%, rgba(255,60,60,0.32), rgba(255,60,60,0) 60%)",
            opacity: clamp01(since / 10) * (0.7 + 0.3 * Math.sin(t * 9)),
            mixBlendMode: "screen",
          }}
        />
      ) : null}

      {/* kilau cahaya */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(105deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.13) 50%, rgba(255,255,255,0) 100%)`,
          width: 420,
          left: sweepX,
          transform: "skewX(-12deg)",
          mixBlendMode: "screen",
        }}
      />

      {/* partikel berkilau */}
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute", left: 0, top: 0 }}>
        {Array.from({ length: 26 }, (_, k) => {
          const ph = (t * (0.05 + (k % 5) * 0.018) + k * 0.137) % 1;
          const x = (k * 197 + Math.sin(t * 0.8 + k) * 40) % 1080;
          const y = 1700 - ph * 1500;
          return <circle key={k} cx={x} cy={y} r={2 + (k % 3)} fill={k % 2 ? palette.accent : "#fff"} opacity={0.18 + 0.22 * Math.sin(t * 2 + k)} />;
        })}
      </svg>

      {/* gelap tipis di atas supaya judul terbaca */}
      <AbsoluteFill style={{ background: "linear-gradient(to bottom, rgba(5,8,18,0.82) 0%, rgba(5,8,18,0) 24%)" }} />

      <SceneTitle title={scene.title} palette={palette} />

      {/* label bagian, muncul berurutan */}
      <div style={{ position: "absolute", left: 36, top: 340, display: "flex", flexDirection: "column", gap: 16 }}>
        {labels.map((label, i) => {
          const delay = Math.round(fps * (0.8 + i * step));
          const p = spring({ frame: frame - delay, fps, config: { damping: 13, stiffness: 150, mass: 0.7 } });
          const color = i % 2 ? palette.accent2 : palette.accent;
          return (
            <React.Fragment key={i}>
              <div
                style={{
                  alignSelf: "flex-start",
                  padding: "6px 24px",
                  borderRadius: 40,
                  backgroundColor: "rgba(8,12,28,0.9)",
                  border: `5px solid ${color}`,
                  boxShadow: `0 0 24px ${color}88`,
                  color: "#fff",
                  fontFamily: TITLE_FONT,
                  fontSize: 40,
                  lineHeight: 1.1,
                  textTransform: "uppercase",
                  transform: `scale(${p})`,
                  transformOrigin: "0% 50%",
                  opacity: clamp01(p * 1.6),
                  maxWidth: 560,
                }}
              >
                {label}
              </div>
            </React.Fragment>
          );
        })}
      </div>

      {dramatic ? <Sfx name={climaxSound(scene)} at={c} volume={0.36} /> : null}
      {flash > 0 ? <AbsoluteFill style={{ backgroundColor: "#fff", opacity: flash }} /> : null}
    </AbsoluteFill>
  );
};
