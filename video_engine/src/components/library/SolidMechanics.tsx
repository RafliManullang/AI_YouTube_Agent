import React from "react";
import * as THREE from "three";
import { LibProps, num } from "./common";

// Tiga primitif mekanika benda padat (poros, sendi, bantalan, batang). Keadaan awal selalu utuh dan sudah bergerak pelan
// (berputar); aksi klimaks (menekuk, miring, patah) baru berjalan setelah kata pemicu, lewat u. Tanpa teks di dalam komponen.
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const ease = (x: number) => { const k = clamp01(x); return k * k * (3 - 2 * k); };
const DEG = Math.PI / 180;
const STEEL = "#b9c4d6";

const Shaft: React.FC<{ len: number; spin: number; color?: string; r?: number }> = ({ len, spin, color = STEEL, r = 0.5 }) => (
  // poros berputar pada sumbunya; garis terang di permukaan membuat putarannya terlihat
  <group rotation={[spin, 0, 0]}>
    <mesh rotation={[0, 0, Math.PI / 2]}>
      <cylinderGeometry args={[r, r, len, 28]} />
      <meshStandardMaterial color={color} metalness={0.8} roughness={0.28} />
    </mesh>
    <mesh position={[0, r + 0.01, 0]}>
      <boxGeometry args={[len * 0.9, 0.07, 0.16]} />
      <meshStandardMaterial color="#ffd23f" emissive="#ffd23f" emissiveIntensity={0.9} />
    </mesh>
  </group>
);

// 1. RotatingShaftAndJoint: dua poros berputar, bola sendi di tengah, poros kanan menekuk sampai sudut theta
export const RotatingShaftAndJoint: React.FC<LibProps> = ({ u, t, props }) => {
  const maxDeg = Math.min(60, Math.max(5, num(props, "tilt", 40)));
  const theta = maxDeg * ease(u / 0.8) * DEG;
  const spin = t * 3.2;
  return (
    <group>
      <group position={[-2.4, 0, 0]}><Shaft len={4.8} spin={spin} /></group>
      <group rotation={[0, 0, -theta]}>
        <group position={[2.4, 0, 0]}><Shaft len={4.8} spin={spin} /></group>
      </group>
      <mesh>
        <sphereGeometry args={[0.85, 28, 28]} />
        <meshStandardMaterial color="#ffb020" metalness={0.7} roughness={0.25} emissive="#ff8a00" emissiveIntensity={0.55 + 0.5 * ease(u / 0.8)} />
      </mesh>
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[1.5, 24, 24]} />
        <meshBasicMaterial color="#ffb020" transparent opacity={0.07} depthWrite={false} />
      </mesh>
    </group>
  );
};

// 2. BallBearingCage: cincin luar, cincin dalam, enam bola baja yang berputar; cincin dalam miring dan bola bergeser
export const BallBearingCage: React.FC<LibProps> = ({ u, t, props }) => {
  const maxDeg = Math.min(60, Math.max(5, num(props, "tilt", 45)));
  const th = maxDeg * ease(u / 0.8) * DEG;
  const balls = Math.round(num(props, "balls", 6));
  const base = t * 0.6;
  return (
    <group>
      <mesh>
        <torusGeometry args={[3.3, 0.32, 16, 64]} />
        <meshStandardMaterial color="#5f7898" metalness={0.6} roughness={0.35} transparent opacity={0.55} />
      </mesh>
      <group rotation={[0, th, 0]}>
        <mesh>
          <torusGeometry args={[1.5, 0.36, 16, 56]} />
          <meshStandardMaterial color="#ffb020" metalness={0.7} roughness={0.3} emissive="#ff8a00" emissiveIntensity={0.3} />
        </mesh>
      </group>
      {Array.from({ length: balls }).map((_, i) => {
        const a = base + (i / balls) * Math.PI * 2;
        const r = 2.4 + 0.22 * Math.sin(th) * Math.cos(2 * a);
        return (
          <mesh key={i} position={[Math.cos(a) * r, Math.sin(a) * r, 0.25 * Math.sin(th) * Math.sin(a)]}>
            <sphereGeometry args={[0.62, 24, 24]} />
            <meshStandardMaterial color="#e3ebf7" metalness={0.95} roughness={0.15} emissive="#9fc4ff" emissiveIntensity={0.25} />
          </mesh>
        );
      })}
    </group>
  );
};

// 3. RigidVsFlexibleRod: batang atas kaku (ditekuk lalu retak dan patah), batang bawah bersendi (menekuk mulus tanpa patah)
export const RigidVsFlexibleRod: React.FC<LibProps> = ({ u, t, props }) => {
  const maxDeg = Math.min(60, Math.max(10, num(props, "tilt", 40)));
  const bend = ease(u / 0.7);
  const crack = clamp01((u - 0.45) / 0.1);
  const broken = u > 0.55;
  const sep = broken ? ease((u - 0.55) / 0.3) : 0;
  const sway = 0.02 * Math.sin(t * 2.5); // keadaan awal: batang bergetar halus, tidak diam
  const rod = (len: number, color: string, emissive = 0.25) => (
    <mesh position={[len / 2, 0, 0]} rotation={[0, 0, 0]}>
      <boxGeometry args={[len, 0.55, 0.55]} />
      <meshStandardMaterial color={color} metalness={0.75} roughness={0.3} emissive={color} emissiveIntensity={emissive} />
    </mesh>
  );
  const segs = 3;
  const seg = (maxDeg * DEG * bend) / segs;
  return (
    <group>
      {/* atas: batang kaku */}
      <group position={[-3.2, 1.8, 0]} rotation={[0, 0, sway]}>
        <group rotation={[0, 0, broken ? 0.1 * sep : -(maxDeg * 0.5 * DEG) * bend]}>{rod(3.2, "#c24b4b", 0.2 + 0.5 * crack)}</group>
        <group position={[3.2, 0, 0]} rotation={[0, 0, broken ? -0.45 * sep : -(maxDeg * 0.5 * DEG) * bend]} >
          <group position={[0, -2.2 * sep, 0]}>{rod(3.2, "#c24b4b", 0.2 + 0.5 * crack)}</group>
        </group>
        {crack > 0 ? (
          <mesh position={[3.2, 0, 0.3]}>
            <boxGeometry args={[0.12, 0.9 + 0.5 * crack, 0.12]} />
            <meshStandardMaterial color="#ff2a2a" emissive="#ff2a2a" emissiveIntensity={2.2 * (broken ? 1 - sep : crack)} transparent opacity={broken ? 1 - sep : 1} />
          </mesh>
        ) : null}
      </group>
      {/* bawah: batang bersendi, menekuk mulus */}
      <group position={[-3.2, -1.8, 0]}>
        <group rotation={[0, 0, -seg]}>
          {rod(2.15, "#4fd7ff")}
          <group position={[2.15, 0, 0]}>
            <mesh><sphereGeometry args={[0.42, 20, 20]} /><meshStandardMaterial color="#ffb020" metalness={0.7} roughness={0.25} emissive="#ff8a00" emissiveIntensity={0.5} /></mesh>
            <group rotation={[0, 0, -seg]}>
              {rod(2.15, "#4fd7ff")}
              <group position={[2.15, 0, 0]}>
                <mesh><sphereGeometry args={[0.42, 20, 20]} /><meshStandardMaterial color="#ffb020" metalness={0.7} roughness={0.25} emissive="#ff8a00" emissiveIntensity={0.5} /></mesh>
                <group rotation={[0, 0, -seg]}>{rod(2.15, "#4fd7ff")}</group>
              </group>
            </group>
          </group>
        </group>
      </group>
    </group>
  );
};
