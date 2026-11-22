import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { SceneClipLayer } from "./components/SceneClipLayer";
import { Sfx, SfxEnabled, SfxMap, SfxSeed } from "./Sfx";
import { springIn } from "./utils/animation";
import { ShortsProps, WordItem } from "./types";

export type { ShortsProps, WordItem } from "./types";

const MAX_PHRASE_WORDS = 4;
const HOOK_SECONDS = 5;
const SUBTITLE_LEAD = 0.04;

const buildPhrases = (words: WordItem[], sceneStarts: number[]): WordItem[][] => {
  const phrases: WordItem[][] = [];
  let current: WordItem[] = [];
  const sceneOf = (t: number) => {
    let idx = 0;
    sceneStarts.forEach((st, i) => {
      if (t >= st - 0.01) idx = i;
    });
    return idx;
  };
  words.forEach((w, i) => {
    const prev = current[current.length - 1];
    if (
      prev &&
      (prev.who !== w.who ||
        sceneOf(prev.start) !== sceneOf(w.start) ||
        current.length >= MAX_PHRASE_WORDS ||
        /[.,!?;:]$/.test(prev.word) ||
        (current.length >= 2 && current.map((x) => x.word).join("").length > 22))
    ) {
      phrases.push(current);
      current = [];
    }
    current.push(w);
    if (i === words.length - 1) phrases.push(current);
  });
  return phrases.filter((p) => p.length > 0);
};

export const ShortsComp: React.FC<ShortsProps> = ({
  audioUrl,
  bgmUrl,
  scenes,
  words,
  durationInSeconds,
  sfx = true,
  bgSeed = 0,
  sfxMap = {},
  clean = false,
  hookQuestion = "",
  hookHighlight = "",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps;
  const safeScenes = scenes ?? [];
  const safeWords = words ?? [];
  const total = Math.max(1, durationInSeconds || 40);

  const phrases = buildPhrases(
    safeWords,
    safeScenes.map((sc) => sc.startFrame / fps),
  );
  let activeIdx = -1;
  phrases.forEach((ph, i) => {
    if (time >= ph[0].start - SUBTITLE_LEAD) activeIdx = i;
  });
  let activePhrase = activeIdx >= 0 ? phrases[activeIdx] : undefined;
  if (activePhrase && time > activePhrase[activePhrase.length - 1].end + 0.3) activePhrase = undefined;
  let activeWord = -1;
  activePhrase?.forEach((w, i) => {
    if (time >= w.start - SUBTITLE_LEAD) activeWord = i;
  });

  const hookWords = hookQuestion.split(/\s+/).filter(Boolean);
  const hl = hookHighlight
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((x) => x.replace(/[^a-z0-9]/g, ""));
  const isHl = (w: string, i: number) => {
    const n = w.toLowerCase().replace(/[^a-z0-9]/g, "");
    return hl.length ? hl.includes(n) : i >= hookWords.length - 2 && i < hookWords.length;
  };
  const hookIn = spring({ frame, fps, config: { damping: 14, stiffness: 110 } });
  const hookOpacity = interpolate(frame, [HOOK_SECONDS * fps - 12, HOOK_SECONDS * fps], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <SfxEnabled.Provider value={sfx}>
      <SfxSeed.Provider value={bgSeed}>
        <SfxMap.Provider value={sfxMap}>
          <AbsoluteFill style={{ backgroundColor: "#0b0f19" }}>
            {/* Latar utama: klip/gambar per adegan, sinkron dengan durasi TTS */}
            <SceneClipLayer scenes={safeScenes} />

            {/* Lapisan gelap tipis di bawah supaya subtitle mudah dibaca */}
            <AbsoluteFill style={{ background: "linear-gradient(to top, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0) 28%)" }} />

            {/* Transisi SFX: hentakan pembuka + whoosh tiap pergantian adegan + sfx puncak per adegan */}
            <Sfx name="whoosh" at={0} volume={0.34} />
            <Sfx name="impact" at={10} volume={0.5} />
            {safeScenes.slice(1).map((sc) => (
              <Sfx key={`w-${sc.id}`} name="whoosh" at={sc.startFrame} volume={0.22} />
            ))}
            {safeScenes.map((sc) =>
              sc.sfx ? (
                <Sequence key={`s-${sc.id}`} from={sc.startFrame} durationInFrames={Math.max(1, sc.durationInFrames)}>
                  <Sfx name={sc.sfx as never} at={Math.min(12, Math.max(0, sc.durationInFrames - 15))} volume={0.5} />
                </Sequence>
              ) : null,
            )}

            {audioUrl ? <Audio src={staticFile(audioUrl)} /> : null}
            {bgmUrl ? (
              <Audio
                src={staticFile(bgmUrl)}
                loop
                volume={(f) => {
                  const sec = f / fps;
                  const fadeIn = Math.min(1, sec / 1.5);
                  const fadeOut = Math.min(1, Math.max(0, (total - sec) / 1.5));
                  return 0.1 * Math.min(fadeIn, fadeOut);
                }}
              />
            ) : null}

            {/* Judul pembuka bersih (5 detik pertama) */}
            {clean || !hookWords.length || time >= HOOK_SECONDS ? null : (
              <div
                style={{
                  position: "absolute",
                  left: 60,
                  top: 170,
                  maxWidth: 760,
                  opacity: hookOpacity * Math.min(1, hookIn * 2),
                  transform: `translateX(${(1 - Math.min(1, hookIn)) * -60}px)`,
                  fontFamily: "Impact, 'Arial Black', sans-serif",
                  fontSize: 84,
                  lineHeight: 1.02,
                  letterSpacing: 1,
                  color: "#ffffff",
                  textTransform: "uppercase",
                  textShadow: "0 6px 0 #000, 4px 4px 0 #000, -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000",
                }}
              >
                {hookWords.map((w, i) => (
                  <React.Fragment key={i}>
                    <span style={{ color: isHl(w, i) ? "#f97316" : "#ffffff" }}>{w}</span>{" "}
                  </React.Fragment>
                ))}
              </div>
            )}

            {/* Subtitle per kata: frasa pendek, kata aktif dalam kotak oranye */}
            {clean || !activePhrase ? null : (
              <div
                style={{
                  position: "absolute",
                  top: "68%",
                  left: 50,
                  right: 50,
                  display: "flex",
                  flexWrap: "wrap",
                  justifyContent: "center",
                  gap: "10px 14px",
                }}
              >
                {activePhrase.map((item, index) => {
                  if (time < item.start - SUBTITLE_LEAD) return null;
                  const pop = springIn(frame, fps, item.start, "snappy");
                  const isActive = index === activeWord;
                  const emph = !!item.emphasis;
                  return (
                    <span
                      key={`${item.start}-${index}`}
                      style={{
                        fontFamily: "Impact, 'Arial Black', sans-serif",
                        fontSize: emph ? 62 : 56,
                        fontWeight: 900,
                        lineHeight: 1.1,
                        letterSpacing: 1,
                        color: "#FFFFFF",
                        textTransform: "uppercase",
                        padding: "4px 12px",
                        borderRadius: 10,
                        background: isActive ? "#ea580c" : "transparent",
                        transform: `scale(${0.88 + 0.12 * pop})`,
                        textShadow: "0 5px 0 #000, 3px 3px 0 #000, -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000",
                      }}
                    >
                      {item.word}
                    </span>
                  );
                })}
              </div>
            )}
          </AbsoluteFill>
        </SfxMap.Provider>
      </SfxSeed.Provider>
    </SfxEnabled.Provider>
  );
};
