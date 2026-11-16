import React, { useMemo } from "react";
import * as THREE from "three";
import { LibProps, heatColor, num, str } from "./common";

// Lima komponen primitif fisika yang berlaku untuk topik sains apa pun. Semua gerak dihitung dari waktu (t) dan
// kemajuan adegan (u); tidak ada teks di dalam komponen (label datang dari naskah). Objek spesifik (headphone, jembatan,
// mobil) tidak pernah dibuat di sini.
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const ease = (x: number) => { const k = clamp01(x); return k * k * (3 - 2 * k); };
const hash = (i: number, s = 1) => { const x = Math.sin(i * 127.1 * s + 311.7) * 43758.5453; return x - Math.floor(x); };
const tri = (x: number) => 1 - Math.abs(((x % 2) + 2) % 2 - 1) * 1; // gelombang segitiga 0..1..0 (pantulan)
const bounce = (x: number) => { const m = ((x % 2) + 2) % 2; return m < 1 ? m : 2 - m; };

const Ghost: React.FC<{ kind: string; w: number; h: number; d?: number; color?: string }> = ({ kind, w, h, d = 1.5, color = "#5f7898" }) => {
  if (kind === "none") return null;
  // Lapisan 1 (cangkang): siluet tembus pandang opacity 0,25. Lapisan 2 (isi) digambar oleh komponen pemanggil.
  return kind === "disc" ? (
    <mesh position={[0, 0, -d]} rotation={[Math.PI / 2, 0, 0]}>
      <cylinderGeometry args={[w / 2, w / 2, 1.0, 48]} />
      <meshStandardMaterial color={color} transparent opacity={0.06} metalness={0.3} roughness={0.6} depthWrite={false} />
    </mesh>
  ) : (
    <mesh position={[0, 0, -d]}>
      <boxGeometry args={[w, h, 0.5]} />
      <meshStandardMaterial color={color} transparent opacity={0.1} metalness={0.3} roughness={0.6} depthWrite={false} />
    </mesh>
  );
};

const Glow: React.FC<{ color: string; r: number; at: [number, number, number]; i?: number }> = ({ color, r, at, i = 1.8 }) => (
  <group position={at}>
    <mesh><sphereGeometry args={[r, 12, 12]} /><meshStandardMaterial color={color} emissive={color} emissiveIntensity={i} /></mesh>
    <mesh><sphereGeometry args={[r * 2.4, 12, 12]} /><meshBasicMaterial color={color} transparent opacity={0.14} depthWrite={false} /></mesh>
  </group>
);

// 1. ParticleFlow: partikel mengalir dari pelat A ke pelat B (ionisasi, arus listrik, gas, cairan, radiasi)
export const ParticleFlow: React.FC<LibProps> = ({ u, t, props }) => {
  const n = Math.round(num(props, "count", 36));
  const shell = str(props, "shell", "box");
  const ca = str(props, "colorA", "#ff7a45");
  const cb = str(props, "colorB", "#4fd7ff");
  const speed = num(props, "speed", 0.35);
  return (
    <group>
      <Ghost kind={shell} w={10.4} h={5.2} />
      <mesh position={[-4.4, 0, 0]}><boxGeometry args={[0.35, 4, 1.4]} /><meshStandardMaterial color={ca} emissive={ca} emissiveIntensity={0.7} /></mesh>
      <mesh position={[4.4, 0, 0]}><boxGeometry args={[0.35, 4, 1.4]} /><meshStandardMaterial color={cb} emissive={cb} emissiveIntensity={0.7} /></mesh>
      {Array.from({ length: n }).map((_, i) => {
        const ph = (t * speed * (0.7 + hash(i) * 0.6) + hash(i, 2)) % 1;
        const x = -4.2 + 8.4 * ph;
        const y = (hash(i, 3) - 0.5) * 3.4 + Math.sin(ph * 9 + i) * 0.18;
        const z = (hash(i, 4) - 0.5) * 0.9;
        const col = new THREE.Color(ca).lerp(new THREE.Color(cb), ph).getStyle();
        const vis = (ph < 0.04 ? ph / 0.04 : ph > 0.96 ? (1 - ph) / 0.04 : 1);
        return <mesh key={i} position={[x, y, z]} scale={0.14 + 0.1 * vis}><sphereGeometry args={[1, 10, 10]} /><meshStandardMaterial color={col} emissive={col} emissiveIntensity={1.5} transparent opacity={vis} /></mesh>;
      })}
    </group>
  );
};

// 2. PressureChamber: ruang tertutup dengan partikel memantul; makin lama makin cepat dan padat (tekanan naik)
export const PressureChamber: React.FC<LibProps> = ({ u, t, props }) => {
  const n = Math.round(num(props, "count", 34));
  const squeeze = num(props, "squeeze", 0.35); // seberapa banyak ruang menyempit di akhir
  const w = 6.4, h0 = 5.0;
  const h = h0 * (1 - squeeze * ease(u));
  const heat = clamp01(u * 1.1);
  const col = heatColor("#7fd0ff", heat).getStyle();
  return (
    <group>
      <mesh position={[0, 0, -0.1]}>
        <boxGeometry args={[w, h, 1.6]} />
        <meshStandardMaterial color="#9fb4cc" transparent opacity={0.25} metalness={0.3} roughness={0.5} depthWrite={false} />
      </mesh>
      <mesh position={[0, h / 2 + 0.15, 0]}><boxGeometry args={[w + 0.4, 0.3, 1.8]} /><meshStandardMaterial color="#cfd6e2" metalness={0.6} roughness={0.35} /></mesh>
      {Array.from({ length: n }).map((_, i) => {
        const sp = (0.6 + hash(i) * 0.9) * (0.7 + 1.4 * u);
        const x = (bounce(t * sp * 0.45 + hash(i, 2) * 2) - 0.5) * (w - 0.6);
        const y = (bounce(t * sp * 0.37 + hash(i, 3) * 2) - 0.5) * (h - 0.6);
        const z = (hash(i, 4) - 0.5) * 0.8;
        return <mesh key={i} position={[x, y, z]} scale={0.13}><sphereGeometry args={[1, 10, 10]} /><meshStandardMaterial color={col} emissive={col} emissiveIntensity={1.3} /></mesh>;
      })}
    </group>
  );
};

// 3. HeatTransfer: dua bidang bersuhu berbeda, panas merambat, dan keping dua lapis melengkung karena panas
export const HeatTransfer: React.FC<LibProps> = ({ u, t, props }) => {
  const heat = typeof props.heat === "number" ? clamp01(props.heat as number) : ease(u * 1.2);
  const hot = heatColor("#8a94a6", heat).getStyle();
  const cold = heatColor("#5b7fb0", heat * 0.25).getStyle();
  const bend = 1.3 * heat;
  const geo = (off: number, color: string) => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 24; i++) {
      const x = -3 + (6 * i) / 24;
      pts.push(new THREE.Vector3(x, off + bend * (1 - Math.pow((x / 3), 2)) * 0.9 - 0.6, 0));
    }
    return { g: new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 48, 0.2, 6, false), color };
  };
  const strips = useMemo(() => [geo(0.2, "#ff9d3c"), geo(-0.2, "#a9b4c4")], [bend]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <group>
      <mesh position={[-5.0, 0, 0]}><boxGeometry args={[1.4, 4.4, 1.4]} /><meshStandardMaterial color={hot} emissive={hot} emissiveIntensity={0.6 + heat} /></mesh>
      <mesh position={[5.0, 0, 0]}><boxGeometry args={[1.4, 4.4, 1.4]} /><meshStandardMaterial color={cold} emissive={cold} emissiveIntensity={0.3} /></mesh>
      {strips.map((s, i) => (
        <mesh key={i} geometry={s.g}><meshStandardMaterial color={s.color} emissive={s.color} emissiveIntensity={0.5 + heat * 0.6} metalness={0.5} roughness={0.4} /></mesh>
      ))}
      {Array.from({ length: 12 }).map((_, i) => {
        const ph = (t * 0.4 + hash(i)) % 1;
        const x = -4.2 + 3.0 * ph;
        const y = (hash(i, 2) - 0.5) * 3.4 + Math.sin(ph * 12 + i) * 0.15;
        return <mesh key={i} position={[x, y, 0.5]} scale={0.11 * (0.35 + 0.65 * ease(u * 5))}><sphereGeometry args={[1, 8, 8]} /><meshBasicMaterial color="#ff9d3c" transparent opacity={0.8 * (1 - ph)} /></mesh>;
      })}
    </group>
  );
};

// 4. MechanicalTrigger: pegas menekan, pelepasan, palu memukul sasaran, percikan menyebar
export const MechanicalTrigger: React.FC<LibProps> = ({ u, t, props }) => {
  const shell = str(props, "shell", "box");
  const hit = 0.62; // saat benturan
  const press = ease(u / 0.35);
  const fall = ease((u - 0.5) / (hit - 0.5));
  const rebound = ease((u - hit) / 0.25);
  const hammerY = 2.6 - 0.55 * press - 3.3 * fall * (1 - 0.15 * rebound) + 0.6 * rebound;
  const springTop = 3.4 - 1.2 * press;
  const coils = 6;
  const sparkT = clamp01((u - hit) / 0.3);
  return (
    <group>
      <Ghost kind={shell} w={5.2} h={9.2} d={1.2} />
      {Array.from({ length: coils }).map((_, i) => (
        <mesh key={i} position={[0, springTop + 1.3 - (i * (springTop + 0.4)) / (coils * 1.55), 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.7, 0.11, 8, 28]} /><meshStandardMaterial color="#dfe6f2" metalness={0.7} roughness={0.3} />
        </mesh>
      ))}
      <mesh position={[0, hammerY, 0]}><boxGeometry args={[1.5, 1.0, 1.2]} /><meshStandardMaterial color="#ffb020" metalness={0.6} roughness={0.35} emissive="#ff8a00" emissiveIntensity={0.25 + 0.7 * (u > hit ? 1 - sparkT : 0)} /></mesh>
      <mesh position={[0, -2.9, 0]}><boxGeometry args={[2.2, 0.9, 1.4]} /><meshStandardMaterial color="#6fd6ff" transparent opacity={0.8} emissive="#6fd6ff" emissiveIntensity={u > hit ? 1.2 * (1 - sparkT) + 0.2 : 0.15} /></mesh>
      {u > hit
        ? Array.from({ length: 14 }).map((_, i) => {
            const a = (i / 14) * Math.PI * 2 + hash(i);
            const r = 0.4 + 2.6 * sparkT * (0.6 + hash(i, 2));
            return <Glow key={i} color="#ffe27a" r={0.07 * (1 - sparkT)} at={[Math.cos(a) * r, -2.3 + Math.sin(a) * r * 0.8, 0.5]} i={2.2} />;
          })
        : null}
    </group>
  );
};

export const PRIMITIVE_IDS = ["ParticleFlow", "WaveInterference", "PressureChamber", "HeatTransfer", "MechanicalTrigger"] as const;
