import React, { useMemo } from "react";
import * as THREE from "three";
import { heatColor, heatOf, LibProps, num } from "./common";

// Elemen pemanas berbentuk pegas panjang sepanjang sumbu x. Makin panas makin merah menyala.
export const HeatingCoil: React.FC<LibProps> = (p) => {
  const heat = heatOf(p);
  const turns = Math.round(num(p.props, "turns", 7));
  const geo = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    const steps = turns * 24;
    for (let i = 0; i <= steps; i++) {
      const a = (i / 24) * Math.PI * 2;
      pts.push(new THREE.Vector3(-2.5 + (i / steps) * 5, Math.sin(a) * 0.42, Math.cos(a) * 0.42));
    }
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), steps * 3, 0.07, 8);
  }, [turns]);
  const c = heatColor("#7a5a48", heat);
  return (
    <mesh geometry={geo}>
      <meshStandardMaterial color={c} emissive={c} emissiveIntensity={0.15 + heat * 2.4} metalness={0.4} roughness={0.45} />
    </mesh>
  );
};
