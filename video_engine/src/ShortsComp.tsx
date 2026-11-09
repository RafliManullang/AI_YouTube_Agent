import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface WordItem {
  word: string;
  start: number;
  end: number;
}

interface ShortsProps {
  audioUrl: string;
  images: string[];
  words: WordItem[];
  durationInSeconds: number;
}

export const ShortsComp: React.FC<ShortsProps> = ({
  audioUrl,
  images,
  words,
  durationInSeconds,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Ganti scene visual berkala
  const imageIndex = Math.min(
    Math.floor((currentTime / (durationInSeconds || 40)) * (images?.length || 1)),
    (images?.length || 1) - 1
  );

  // Efek zoom dinamis
  const scale = interpolate(frame % (fps * 7), [0, fps * 7], [1, 1.15], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0b0f19" }}>
      {/* Visual Aset Diagram 3D */}
      {images && images.length > 0 && (
        <AbsoluteFill style={{ overflow: "hidden" }}>
          <Img
            src={staticFile(images[imageIndex])}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: `scale(${scale})`,
            }}
          />
          <AbsoluteFill
            style={{
              background:
                "linear-gradient(to top, rgba(0,0,0,0.85) 15%, transparent 60%, rgba(0,0,0,0.6) 100%)",
            }}
          />
        </AbsoluteFill>
      )}

      {/* Audio Narasi */}
      {audioUrl && <Audio src={staticFile(audioUrl)} />}

      {/* Subtitle Teks Kinetik Menyala */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: "0 60px",
          bottom: -450,
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: "14px",
          }}
        >
          {words &&
            words.map((item, index) => {
              const isActive =
                currentTime >= item.start && currentTime <= item.end;
              const isVisible =
                currentTime >= item.start - 0.4 && currentTime <= item.end + 1.1;

              if (!isVisible) return null;

              return (
                <span
                  key={index}
                  style={{
                    fontFamily: "Impact, Arial Black, sans-serif",
                    fontSize: isActive ? "68px" : "56px",
                    fontWeight: 900,
                    color: isActive ? "#FFE600" : "#FFFFFF",
                    textTransform: "uppercase",
                    transform: isActive ? "scale(1.15)" : "scale(1.0)",
                    transition: "transform 0.08s ease",
                    textShadow: "4px 4px 0px #000, -2px -2px 0px #000",
                  }}
                >
                  {item.word}
                </span>
              );
            })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};