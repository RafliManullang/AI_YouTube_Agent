import React from "react";
import {
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Sfx } from "./Sfx";
import { Palette, SceneData } from "./types";

export const TITLE_FONT = "Impact, 'Arial Black', sans-serif";
export const BODY_FONT = "'Arial Black', Arial, sans-serif";

export type DiagramProps = {
  scene: SceneData;
  palette: Palette;
  lengthFrames: number;
};

const useSpringAt = (delayFrames: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({
    frame: frame - delayFrames,
    fps,
    config: { damping: 13, stiffness: 140, mass: 0.7 },
  });
};

// ------------------------------------------------------------
// Judul adegan (muncul membal + garis bawah memanjang)
// ------------------------------------------------------------
export const SceneTitle: React.FC<{ title: string; palette: Palette }> = ({
  title,
  palette,
}) => {
  const p = useSpringAt(4);
  return (
    <div
      style={{
        position: "absolute",
        top: 170,
        left: 70,
        width: 940,
        textAlign: "center",
        transform: `scale(${0.7 + 0.3 * p})`,
        opacity: Math.min(1, p * 1.5),
      }}
    >
      <div
        style={{
          fontFamily: TITLE_FONT,
          fontSize: 80,
          lineHeight: 1.05,
          textTransform: "uppercase",
          color: "#ffffff",
          textShadow: `0 6px 0 ${palette.bg1}, 0 0 40px ${palette.accent}88`,
        }}
      >
        {title}
      </div>
      <div
        style={{
          margin: "18px auto 0",
          height: 10,
          width: 240 * p,
          borderRadius: 5,
          background: `linear-gradient(90deg, ${palette.accent}, ${palette.accent2})`,
        }}
      />
    </div>
  );
};

// ------------------------------------------------------------
// Diagram alur: kartu langkah muncul satu per satu, dihubungkan panah
// ------------------------------------------------------------
export const FlowDiagram: React.FC<DiagramProps> = ({
  scene,
  palette,
  lengthFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const points = scene.points.slice(0, 4);
  const n = points.length;
  const cardH = n >= 4 ? 140 : 170;
  const gap = n >= 4 ? 50 : 60;
  const top = 420;
  const lengthSec = lengthFrames / fps;
  const step = Math.max(0.8, (lengthSec * 0.55) / Math.max(1, n));
  const delays = points.map((_, i) => Math.round(fps * (0.7 + i * step)));

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      {points.map((label, i) => {
        const p = spring({
          frame: frame - delays[i],
          fps,
          config: { damping: 13, stiffness: 120, mass: 0.8 },
        });
        const color = i % 2 === 0 ? palette.accent : palette.accent2;
        const fromX = i % 2 === 0 ? -760 : 760;
        const float = Math.sin((frame + i * 12) / 18) * 6 * Math.min(1, p);
        const cardTop = top + i * (cardH + gap);

        return (
          <React.Fragment key={i}>
            <Sfx name="pop" at={delays[i]} />
            <div
              style={{
                position: "absolute",
                left: 110,
                top: cardTop,
                width: 860,
                height: cardH,
                borderRadius: 40,
                display: "flex",
                alignItems: "center",
                padding: "0 34px",
                gap: 30,
                boxSizing: "border-box",
                background: "rgba(8, 12, 28, 0.72)",
                border: `5px solid ${color}`,
                boxShadow: `0 0 36px ${color}66`,
                transform: `translate(${(1 - p) * fromX}px, ${float}px)`,
                opacity: Math.min(1, p * 1.6),
              }}
            >
              <div
                style={{
                  flex: "0 0 auto",
                  width: 92,
                  height: 92,
                  borderRadius: "50%",
                  backgroundColor: color,
                  color: palette.bg1,
                  fontFamily: TITLE_FONT,
                  fontSize: 58,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {i + 1}
              </div>
              <div
                style={{
                  fontFamily: BODY_FONT,
                  fontSize: n >= 4 ? 46 : 52,
                  lineHeight: 1.1,
                  color: "#ffffff",
                  textTransform: "uppercase",
                }}
              >
                {label}
              </div>
            </div>

            {i < n - 1
              ? (() => {
                  const appear = delays[i + 1] - 9;
                  const a = interpolate(frame, [appear, appear + 9], [0, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  });
                  const lineTop = cardTop + cardH;
                  return (
                    <>
                      <div
                        style={{
                          position: "absolute",
                          left: 534,
                          top: lineTop,
                          width: 12,
                          height: gap - 14,
                          borderRadius: 6,
                          backgroundColor: color,
                          transformOrigin: "top",
                          transform: `scaleY(${a})`,
                        }}
                      />
                      <div
                        style={{
                          position: "absolute",
                          left: 540 - 20,
                          top: lineTop + gap - 24,
                          width: 0,
                          height: 0,
                          borderLeft: "20px solid transparent",
                          borderRight: "20px solid transparent",
                          borderTop: `26px solid ${color}`,
                          opacity: a,
                        }}
                      />
                    </>
                  );
                })()
              : null}
          </React.Fragment>
        );
      })}
    </>
  );
};

// ------------------------------------------------------------
// Peta pikiran: lingkaran tengah, cabang tumbuh ke segala arah
// ------------------------------------------------------------
export const MindMap: React.FC<DiagramProps> = ({
  scene,
  palette,
  lengthFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const points = scene.points.slice(0, 5);
  const n = points.length;
  const cx = width / 2;
  const cy = 720;
  const rx = 330;
  const ry = 430;
  const lengthSec = lengthFrames / fps;
  const step = Math.max(0.6, (lengthSec * 0.5) / Math.max(1, n));

  const centerP = spring({
    frame: frame - 3,
    fps,
    config: { damping: 11, stiffness: 120, mass: 0.8 },
  });
  const pulse = 1 + 0.03 * Math.sin(frame / 8);

  const nodes = points.map((label, i) => {
    const angle = (-90 + (360 / Math.max(1, n)) * i) * (Math.PI / 180);
    return {
      label,
      x: cx + rx * Math.cos(angle),
      y: cy + ry * Math.sin(angle),
      delay: Math.round(fps * (0.8 + i * step)),
      color: i % 2 === 0 ? palette.accent : palette.accent2,
    };
  });

  return (
    <>
      <Sfx name="pop" at={3} />
      <svg
        width={1080}
        height={1920}
        viewBox="0 0 1080 1920"
        style={{ position: "absolute", left: 0, top: 0 }}
      >
        {nodes.map((node, i) => {
          const len = Math.hypot(node.x - cx, node.y - cy);
          const lp = interpolate(frame, [node.delay - 12, node.delay + 6], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.cubic),
          });
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={node.x}
              y2={node.y}
              stroke={node.color}
              strokeWidth={9}
              strokeLinecap="round"
              strokeDasharray={len}
              strokeDashoffset={len * (1 - lp)}
              opacity={0.9}
            />
          );
        })}
      </svg>

      <div
        style={{
          position: "absolute",
          left: cx - 190,
          top: cy - 190,
          width: 380,
          height: 380,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: 36,
          boxSizing: "border-box",
          background: `linear-gradient(135deg, ${palette.accent}, ${palette.accent2})`,
          boxShadow: `0 0 70px ${palette.accent}99`,
          transform: `scale(${centerP * pulse})`,
          fontFamily: TITLE_FONT,
          fontSize: 58,
          lineHeight: 1.05,
          textTransform: "uppercase",
          color: palette.bg1,
        }}
      >
        {scene.title}
      </div>

      {nodes.map((node) => (
        <Sfx key={`sfx-${node.delay}-${node.label}`} name="pop" at={node.delay} />
      ))}

      {nodes.map((node, i) => {
        const p = spring({
          frame: frame - node.delay,
          fps,
          config: { damping: 11, stiffness: 140, mass: 0.7 },
        });
        const float = Math.sin((frame + i * 15) / 17) * 7 * Math.min(1, p);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: node.x - 170,
              top: node.y - 62,
              width: 340,
              height: 124,
              borderRadius: 62,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "0 26px",
              boxSizing: "border-box",
              background: "rgba(8, 12, 28, 0.78)",
              border: `5px solid ${node.color}`,
              boxShadow: `0 0 32px ${node.color}77`,
              fontFamily: BODY_FONT,
              fontSize: 42,
              lineHeight: 1.1,
              color: "#ffffff",
              textTransform: "uppercase",
              transform: `translateY(${float}px) scale(${p})`,
              opacity: Math.min(1, p * 1.6),
            }}
          >
            {node.label}
          </div>
        );
      })}
    </>
  );
};

// ------------------------------------------------------------
// Penghitung angka: cincin terisi + angka menghitung naik
// ------------------------------------------------------------
export const formatNumber = (value: number, decimals: number): string =>
  value.toLocaleString("id-ID", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

export const Counter: React.FC<DiagramProps> = ({ scene, palette }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const target = typeof scene.number === "number" ? scene.number : 0;
  const decimals = Number.isInteger(target) ? 0 : 1;
  const cx = width / 2;
  const cy = 760;
  const r = 300;
  const circumference = 2 * Math.PI * r;

  const progress = interpolate(frame, [fps * 0.4, fps * 2.2], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const shown = formatNumber(target * progress, decimals);
  const bigP = spring({
    frame: frame - 6,
    fps,
    config: { damping: 12, stiffness: 120, mass: 0.8 },
  });
  const fontSize = formatNumber(target, decimals).length <= 4 ? 230 : formatNumber(target, decimals).length <= 7 ? 170 : 125;
  const spin = frame * 1.2;

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Sfx name="pop" at={6} />
      <Sfx name="ding" at={fps * 2.2} />
      {scene.points.slice(0, 3).map((label, i) => (
        <Sfx key={`chip-${label}-${i}`} name="pop" at={Math.round(fps * (1.8 + i * 0.5))} volume={0.2} />
      ))}
      <svg
        width={1080}
        height={1920}
        viewBox="0 0 1080 1920"
        style={{ position: "absolute", left: 0, top: 0 }}
      >
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="rgba(8,12,28,0.55)"
          stroke="rgba(255,255,255,0.15)"
          strokeWidth={22}
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={palette.accent}
          strokeWidth={22}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress)}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
        {/* titik kecil yang berputar mengelilingi cincin */}
        <circle
          cx={cx + (r + 38) * Math.cos((spin * Math.PI) / 180)}
          cy={cy + (r + 38) * Math.sin((spin * Math.PI) / 180)}
          r={14}
          fill={palette.accent2}
        />
      </svg>

      <div
        style={{
          position: "absolute",
          left: 0,
          top: cy - 200,
          width: 1080,
          height: 380,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${0.6 + 0.4 * bigP})`,
        }}
      >
        <div
          style={{
            fontFamily: TITLE_FONT,
            fontSize,
            lineHeight: 1,
            color: palette.accent,
            textShadow: `0 8px 0 ${palette.bg1}, 0 0 50px ${palette.accent}99`,
          }}
        >
          {shown}
        </div>
        {scene.unit ? (
          <div
            style={{
              marginTop: 10,
              maxWidth: 470,
              textAlign: "center",
              fontFamily: BODY_FONT,
              fontSize: 40,
              lineHeight: 1.1,
              color: "#ffffff",
              textTransform: "uppercase",
            }}
          >
            {scene.unit}
          </div>
        ) : null}
      </div>

      <div
        style={{
          position: "absolute",
          left: 90,
          top: 1110,
          width: 900,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: 18,
        }}
      >
        {scene.points.slice(0, 3).map((label, i) => {
          const p = spring({
            frame: frame - Math.round(fps * (1.8 + i * 0.5)),
            fps,
            config: { damping: 12, stiffness: 140, mass: 0.7 },
          });
          const color = i % 2 === 0 ? palette.accent2 : palette.accent;
          return (
            <div
              key={i}
              style={{
                padding: "16px 34px",
                borderRadius: 50,
                backgroundColor: "rgba(8,12,28,0.78)",
                border: `4px solid ${color}`,
                fontFamily: BODY_FONT,
                fontSize: 38,
                color: "#ffffff",
                textTransform: "uppercase",
                transform: `scale(${p})`,
                opacity: Math.min(1, p * 1.6),
              }}
            >
              {label}
            </div>
          );
        })}
      </div>
    </>
  );
};
