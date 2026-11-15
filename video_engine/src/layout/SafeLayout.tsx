import React from "react";
import { AbsoluteFill } from "remotion";

// Pembagian layar tegas untuk video vertikal 1080x1920:
//  - Zona visual (0% sampai 72% tinggi): hanya untuk animasi atau objek 3D utama.
//  - Zona subtitle (72% sampai bawah): hanya untuk teks kata demi kata dalam bantalan gelap semi-transparan.
export const SAFE = {
  visualBottom: 0.8, // batas bawah zona visual
  visualScale: 0.8, // isi adegan dikecilkan supaya muat di zona visual (tinggi 1920 x 0,8)
  captionBottomPx: 120, // jarak subtitle dari tepi bawah (di atas tombol dan judul Shorts)
  captionMaxHeightPx: 150, // tinggi maksimal zona subtitle
} as const;

// Latar (Background) tetap penuh layar di luar komponen ini; hanya isi adegan yang dimasukkan ke zona visual.
export const SafeVisual: React.FC<{ children: React.ReactNode; fullBleed?: boolean }> = ({ children, fullBleed }) => {
  if (fullBleed) return <AbsoluteFill>{children}</AbsoluteFill>; // video latar / gambar utuh tetap penuh layar
  return (
    <AbsoluteFill
      style={{
        transform: `scale(${SAFE.visualScale})`,
        transformOrigin: "50% 0%",
        // tepi kiri-kanan dan bawah memudar halus supaya zona visual tidak tampak seperti kotak bertepi keras
        WebkitMaskImage: "linear-gradient(to right, transparent 0%, #000 7%, #000 93%, transparent 100%), linear-gradient(to bottom, #000 0%, #000 88%, transparent 100%)",
        maskImage: "linear-gradient(to right, transparent 0%, #000 7%, #000 93%, transparent 100%), linear-gradient(to bottom, #000 0%, #000 88%, transparent 100%)",
        WebkitMaskComposite: "source-in",
        maskComposite: "intersect",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

// Wadah subtitle: selalu di zona bawah, rata bawah, dengan bantalan gelap tipis supaya kontras di latar terang.
export const CaptionZone: React.FC<{ children: React.ReactNode; show: boolean }> = ({ children, show }) => (
  <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingLeft: 60, paddingRight: 60, paddingBottom: SAFE.captionBottomPx }}>
    <div
      style={{
        maxHeight: SAFE.captionMaxHeightPx,
        maxWidth: 940,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "flex-end",
        gap: "6px 24px",
        minHeight: 64,
        ...(show ? { backgroundColor: "rgba(5,10,25,0.42)", borderRadius: 40, padding: "12px 30px" } : {}),
      }}
    >
      {children}
    </div>
  </AbsoluteFill>
);
