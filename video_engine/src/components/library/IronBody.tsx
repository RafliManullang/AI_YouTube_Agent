import React, { useMemo } from "react";
import * as THREE from "three";
import { heatColor, heatOf, LibProps, num, str } from "./common";

// Setrika rumahan dengan ukuran tetap: tapak aluminium runcing di depan, bodi plastik tembus pandang, gagang melengkung, tombol suhu.
const outline = (k: number) => {
  const s = new THREE.Shape();
  const L = 3.2 * k, W = 1.55 * k, R = 0.55 * k;
  s.moveTo(-L, -W + R);
  s.quadraticCurveTo(-L, -W, -L + R, -W);
  s.lineTo(L - 1.6 * k, -W);
  s.quadraticCurveTo(L + 0.5 * k, -W * 0.5, L + 0.55 * k, 0); // ujung runcing membulat
  s.quadraticCurveTo(L + 0.5 * k, W * 0.5, L - 1.6 * k, W);
  s.lineTo(-L + R, W);
  s.quadraticCurveTo(-L, W, -L, W - R);
  s.lineTo(-L, -W + R);
  return s;
};

const extrude = (shape: THREE.Shape, depth: number, bevel: number) => {
  const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: true, bevelSize: bevel, bevelThickness: bevel, bevelSegments: 3, curveSegments: 20 });
  g.rotateX(-Math.PI / 2); // berbaring: kedalaman jadi tinggi
  return g;
};

export const IronBody: React.FC<LibProps> = (p) => {
  const heat = heatOf(p);
  const ghost = num(p.props, "ghost", 1);
  const handleColor = str(p.props, "handleColor", "#ff6b4a");
  const sole = useMemo(() => extrude(outline(1), 0.42, 0.04), []);
  const shell = useMemo(() => {
    const g = extrude(outline(0.93), 1.9, 0.08);
    g.translate(0, 0.46, 0);
    return g;
  }, []);
  const handle = useMemo(
    () => new THREE.TubeGeometry(new THREE.CatmullRomCurve3([
      new THREE.Vector3(-2.7, 2.2, 0), new THREE.Vector3(-2.5, 3.4, 0), new THREE.Vector3(-0.5, 3.75, 0), new THREE.Vector3(0.7, 2.4, 0),
    ]), 40, 0.2, 10),
    [],
  );
  const soleColor = heatColor("#b9c3d1", heat);
  return (
    <group>
      <mesh geometry={sole}>
        <meshStandardMaterial color={soleColor} metalness={0.75} roughness={0.3} emissive={soleColor} emissiveIntensity={heat * 0.9} />
      </mesh>
      <mesh geometry={shell} renderOrder={2}>
        <meshPhysicalMaterial color="#7fa6d6" transparent opacity={0.1 + 0.3 * ghost} roughness={0.12} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <mesh geometry={handle}>
        <meshStandardMaterial color={handleColor} roughness={0.5} />
      </mesh>
      <mesh position={[1.7, 2.45, 0]}>
        <cylinderGeometry args={[0.36, 0.36, 0.26, 28]} />
        <meshStandardMaterial color="#222833" roughness={0.4} />
      </mesh>
    </group>
  );
};
