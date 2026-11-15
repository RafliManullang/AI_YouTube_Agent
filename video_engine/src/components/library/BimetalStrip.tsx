import React, { useMemo } from "react";
import * as THREE from "three";
import { heatColor, heatOf, LibProps, num } from "./common";

// Keping bimetal: dua lapis pipih (kuningan di bawah, besi di atas) yang dijepit di ujung kiri.
// Saat panas, kuningan memuai lebih banyak sehingga keping melengkung ke atas; saat dingin kembali lurus.
const LEN = 6.2;
const TH = 0.26;

const stripGeometry = (kappa: number, lo: number, hi: number, width: number) => {
  const N = 44;
  const pos: number[] = [];
  const idx: number[] = [];
  const corners: [number, number][] = [[lo, -width / 2], [hi, -width / 2], [hi, width / 2], [lo, width / 2]];
  for (let i = 0; i <= N; i++) {
    const s = (i / N) * LEN;
    const phi = kappa * s;
    const cx = Math.abs(kappa) < 1e-5 ? s : Math.sin(phi) / kappa;
    const cy = Math.abs(kappa) < 1e-5 ? 0 : (1 - Math.cos(phi)) / kappa;
    const nx = -Math.sin(phi), ny = Math.cos(phi);
    corners.forEach(([off, z]) => pos.push(cx + nx * off, cy + ny * off, z));
  }
  for (let i = 0; i < N; i++) {
    const a = i * 4, b = (i + 1) * 4;
    for (let k = 0; k < 4; k++) {
      const k2 = (k + 1) % 4;
      idx.push(a + k, b + k, b + k2, a + k, b + k2, a + k2);
    }
  }
  // tutup kedua ujung
  idx.push(0, 1, 2, 0, 2, 3);
  const e = N * 4;
  idx.push(e, e + 2, e + 1, e, e + 3, e + 2);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
};

export const BimetalStrip: React.FC<LibProps> = (p) => {
  const heat = heatOf(p);
  const bend = num(p.props, "bend", 1.05); // total sudut lengkung saat paling panas (radian)
  const width = num(p.props, "width", 1.5);
  const q = Math.round(heat * 60) / 60;
  const kappa = (bend / LEN) * q;
  const brass = useMemo(() => stripGeometry(kappa, -TH, 0, width), [kappa, width]);
  const steel = useMemo(() => stripGeometry(kappa, 0, TH, width), [kappa, width]);
  const bc = heatColor("#d8a62e", q * 0.55);
  const sc = heatColor("#9fb0c3", q * 0.55);
  return (
    <group position={[-LEN / 2, 0, 0]}>
      <mesh position={[-0.45, 0, 0]}>
        <boxGeometry args={[0.9, 1.5, width + 0.4]} />
        <meshStandardMaterial color="#59606e" metalness={0.8} roughness={0.35} />
      </mesh>
      <mesh geometry={brass}>
        <meshStandardMaterial color={bc} metalness={0.85} roughness={0.3} emissive={bc} emissiveIntensity={q * 0.8} />
      </mesh>
      <mesh geometry={steel}>
        <meshStandardMaterial color={sc} metalness={0.85} roughness={0.32} emissive={sc} emissiveIntensity={q * 0.8} />
      </mesh>
    </group>
  );
};
