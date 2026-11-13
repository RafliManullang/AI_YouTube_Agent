import React from "react";
import {
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  BODY_FONT,
  DiagramProps,
  SceneTitle,
  TITLE_FONT,
  formatNumber,
} from "./Diagrams";
import { Sfx } from "./Sfx";

const clampOpts = {
  extrapolateLeft: "clamp",
  extrapolateRight: "clamp",
} as const;

// ------------------------------------------------------------
// Garis waktu: garis tumbuh ke bawah, tiap peristiwa muncul bergantian
// ------------------------------------------------------------
export const Timeline: React.FC<DiagramProps> = ({
  scene,
  palette,
  lengthFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const items = (scene.items ?? []).slice(0, 5);
  const n = items.length;
  const topY = 480;
  const bottomY = 1170;
  const gapY = n > 1 ? (bottomY - topY) / (n - 1) : 0;
  const lineX = 290;
  const lengthSec = lengthFrames / fps;
  const step = Math.max(0.7, (lengthSec * 0.6) / Math.max(1, n));
  const delays = items.map((_, i) => Math.round(fps * (0.7 + i * step)));

  const lineEnd =
    n > 1 && delays[n - 1] > delays[0]
      ? interpolate(frame, [delays[0], delays[n - 1]], [topY, bottomY], {
          ...clampOpts,
          easing: Easing.inOut(Easing.quad),
        })
      : topY;

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />

      <svg
        width={1080}
        height={1920}
        viewBox="0 0 1080 1920"
        style={{ position: "absolute", left: 0, top: 0 }}
      >
        <line
          x1={lineX}
          y1={topY}
          x2={lineX}
          y2={bottomY}
          stroke="rgba(255,255,255,0.14)"
          strokeWidth={10}
          strokeLinecap="round"
        />
        <line
          x1={lineX}
          y1={topY}
          x2={lineX}
          y2={lineEnd}
          stroke={palette.accent}
          strokeWidth={10}
          strokeLinecap="round"
        />
      </svg>

      {items.map((item, i) => {
        const p = spring({
          frame: frame - delays[i],
          fps,
          config: { damping: 12, stiffness: 130, mass: 0.7 },
        });
        const y = topY + i * gapY;
        const color = i % 2 === 0 ? palette.accent : palette.accent2;
        const label = String(item.label);
        const text = String(item.value);
        const pulse = 1 + 0.12 * Math.sin((frame - delays[i]) / 6) * Math.max(0, 1 - p * 0.6);

        return (
          <React.Fragment key={i}>

            {/* tahun / waktu di sebelah kiri garis */}
            <div
              style={{
                position: "absolute",
                left: 30,
                top: y - 40,
                width: 215,
                height: 80,
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                fontFamily: TITLE_FONT,
                fontSize: label.length > 6 ? 46 : 62,
                color,
                textShadow: `0 4px 0 ${palette.bg1}`,
                opacity: Math.min(1, p * 1.5),
                transform: `translateX(${(1 - p) * -120}px)`,
              }}
            >
              {label}
            </div>

            {/* titik di garis */}
            <div
              style={{
                position: "absolute",
                left: lineX - 30,
                top: y - 30,
                width: 60,
                height: 60,
                borderRadius: "50%",
                backgroundColor: color,
                border: `8px solid ${palette.bg1}`,
                boxShadow: `0 0 34px ${color}`,
                transform: `scale(${p * pulse})`,
              }}
            />

            {/* kartu keterangan */}
            <div
              style={{
                position: "absolute",
                left: 365,
                top: y,
                width: 660,
                minHeight: 118,
                transform: `translate(${(1 - p) * 320}px, -50%)`,
                opacity: Math.min(1, p * 1.6),
                boxSizing: "border-box",
                padding: "16px 28px",
                borderRadius: 32,
                display: "flex",
                alignItems: "center",
                background: "rgba(8, 12, 28, 0.78)",
                border: `5px solid ${color}`,
                boxShadow: `0 0 30px ${color}66`,
                fontFamily: BODY_FONT,
                fontSize: 38,
                lineHeight: 1.12,
                color: "#ffffff",
                textTransform: "uppercase",
              }}
            >
              {text}
            </div>
          </React.Fragment>
        );
      })}
    </>
  );
};

// ------------------------------------------------------------
// Grafik batang: batang memanjang bergantian, angka menghitung naik
// ------------------------------------------------------------
export const BarChart: React.FC<DiagramProps> = ({
  scene,
  palette,
  lengthFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const items = (scene.items ?? []).slice(0, 5);
  const n = items.length;
  const values = items.map((it) => Number(it.value) || 0);
  const max = Math.max(...values, 1);
  const decimals = values.every((v) => Number.isInteger(v)) ? 0 : 1;
  const topMax = values.indexOf(Math.max(...values));

  const rowH = Math.min(260, 800 / Math.max(1, n));
  const startY = 450 + Math.max(0, 800 - n * rowH) / 2;
  const barLeft = 110;
  const barW = 860;
  const lengthSec = lengthFrames / fps;
  const step = Math.max(0.5, (lengthSec * 0.5) / Math.max(1, n));

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      {items.map((item, i) => {
        const delay = Math.round(fps * (0.6 + i * step));
        const grow = interpolate(frame, [delay, delay + fps * 1.1], [0, 1], {
          ...clampOpts,
          easing: Easing.out(Easing.cubic),
        });
        const appear = spring({
          frame: frame - delay,
          fps,
          config: { damping: 14, stiffness: 140, mass: 0.7 },
        });
        const y = startY + i * rowH;
        const fill = (values[i] / max) * barW * grow;
        const isTop = i === topMax;
        const color = isTop ? palette.accent : palette.accent2;

        return (
          <React.Fragment key={i}>
            <div
              style={{
                position: "absolute",
                left: barLeft,
                top: y,
                width: barW,
                opacity: Math.min(1, appear * 1.6),
                transform: `translateY(${(1 - appear) * 40}px)`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  marginBottom: 10,
                }}
              >
                <div
                  style={{
                    fontFamily: BODY_FONT,
                    fontSize: 44,
                    color: "#ffffff",
                    textTransform: "uppercase",
                  }}
                >
                  {String(item.label)}
                </div>
                <div
                  style={{
                    fontFamily: TITLE_FONT,
                    fontSize: 64,
                    color,
                    textShadow: `0 4px 0 ${palette.bg1}`,
                  }}
                >
                  {formatNumber(values[i] * grow, decimals)}
                  {scene.unit ? (
                    <span
                      style={{
                        marginLeft: 12,
                        fontFamily: BODY_FONT,
                        fontSize: 30,
                        color: "#ffffff",
                      }}
                    >
                      {scene.unit}
                    </span>
                  ) : null}
                </div>
              </div>
              <div
                style={{
                  height: 74,
                  borderRadius: 37,
                  backgroundColor: "rgba(255,255,255,0.12)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: fill,
                    height: "100%",
                    borderRadius: 37,
                    background: isTop
                      ? `linear-gradient(90deg, ${palette.accent}, ${palette.accent2})`
                      : palette.accent2,
                    boxShadow: isTop ? `0 0 30px ${palette.accent}aa` : "none",
                  }}
                />
              </div>
            </div>
          </React.Fragment>
        );
      })}
    </>
  );
};

// ------------------------------------------------------------
// Sebelum dan sesudah: dua kartu dengan panah di tengah
// ------------------------------------------------------------
export const BeforeAfter: React.FC<DiagramProps> = ({
  scene,
  palette,
  lengthFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const items = (scene.items ?? []).slice(0, 2);
  const lengthSec = lengthFrames / fps;
  const delayA = Math.round(fps * 0.7);
  const delayB = Math.round(fps * Math.max(1.6, lengthSec * 0.45));
  const delayArrow = Math.round((delayA + delayB) / 2);

  const spr = (delay: number) =>
    spring({
      frame: frame - delay,
      fps,
      config: { damping: 13, stiffness: 120, mass: 0.8 },
    });
  const pA = spr(delayA);
  const pB = spr(delayB);
  const pArrow = spr(delayArrow);
  const bounce = Math.sin(frame / 6) * 8 * Math.min(1, pArrow);
  const glow = 26 + 14 * Math.sin(frame / 9);

  const card = (
    item: { label: string | number; value: string | number } | undefined,
    top: number,
    isAfter: boolean,
    p: number,
  ) => {
    if (!item) return null;
    const color = isAfter ? palette.accent : "#9aa7bf";
    return (
      <div
        style={{
          position: "absolute",
          left: 90,
          top,
          width: 900,
          height: 330,
          boxSizing: "border-box",
          padding: "52px 44px 30px",
          borderRadius: 44,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          background: isAfter ? "rgba(8, 12, 28, 0.86)" : "rgba(30, 38, 60, 0.82)",
          border: `6px solid ${color}`,
          boxShadow: isAfter ? `0 0 ${glow}px ${palette.accent}aa` : "none",
          transform: `translateX(${(1 - p) * (isAfter ? 900 : -900)}px) scale(${0.9 + 0.1 * p})`,
          opacity: Math.min(1, p * 1.6),
          fontFamily: BODY_FONT,
          fontSize: 50,
          lineHeight: 1.12,
          color: "#ffffff",
          textTransform: "uppercase",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: -34,
            left: 44,
            padding: "8px 32px",
            borderRadius: 40,
            backgroundColor: color,
            color: palette.bg1,
            fontFamily: TITLE_FONT,
            fontSize: 44,
            letterSpacing: 1,
          }}
        >
          {String(item.label)}
        </div>
        {String(item.value)}
      </div>
    );
  };

  return (
    <>
      <SceneTitle title={scene.title} palette={palette} />
      <Sfx name="whoosh" at={delayArrow - 4} volume={0.2} />
      <Sfx name="ding" at={delayB} />

      {card(items[0], 440, false, pA)}

      {/* panah turun di tengah */}
      <div
        style={{
          position: "absolute",
          left: 540 - 55,
          top: 770 + bounce,
          width: 110,
          height: 110,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: `linear-gradient(135deg, ${palette.accent}, ${palette.accent2})`,
          boxShadow: `0 0 36px ${palette.accent}99`,
          transform: `scale(${pArrow})`,
        }}
      >
        <div
          style={{
            width: 0,
            height: 0,
            borderLeft: "26px solid transparent",
            borderRight: "26px solid transparent",
            borderTop: `36px solid ${palette.bg1}`,
          }}
        />
      </div>

      {card(items[1], 890, true, pB)}
    </>
  );
};
