import React from "react";
import { heatColor, heatOf, LibProps, num } from "./common";

// Kontak saklar yang menumpang di ujung keping bimetal (letakkan di posisi yang sama dengan BimetalStrip), dan lampu pemanas.
// Saat dingin keping lurus dan lampu menyala; saat panas keping melengkung, kontak ikut terangkat, lampu padam (pemanas terputus).
const LEN = 6.2;
const TH = 0.26;

export const ThermostatSwitch: React.FC<LibProps> = (p) => {
  const heat = heatOf(p);
  const bend = num(p.props, "bend", 1.05);
  const q = Math.round(heat * 60) / 60;
  const kappa = (bend / LEN) * q;
  const s = LEN - 0.75; // kontak berada dekat ujung keping
  const phi = kappa * s;
  const cx = Math.abs(kappa) < 1e-5 ? s : Math.sin(phi) / kappa;
  const cy = Math.abs(kappa) < 1e-5 ? 0 : (1 - Math.cos(phi)) / kappa;
  const lampOn = heat < 0.5;
  return (
    <group position={[-LEN / 2, 0, 0]}>
      <group position={[cx - Math.sin(phi) * (TH + 0.12), cy + Math.cos(phi) * (TH + 0.12), 0]} rotation={[0, 0, phi]}>
        <mesh>
          <boxGeometry args={[1.0, 0.2, 1.1]} />
          <meshStandardMaterial color={heatColor("#c0c8d4", q)} metalness={0.85} roughness={0.3} />
        </mesh>
      </group>
      <mesh position={[-0.2, 2.6, 0]}>
        <sphereGeometry args={[0.34, 24, 18]} />
        <meshStandardMaterial color={lampOn ? "#ffb020" : "#2a2f3a"} emissive={lampOn ? "#ffb020" : "#000000"} emissiveIntensity={lampOn ? 2.2 : 0} />
      </mesh>
    </group>
  );
};
