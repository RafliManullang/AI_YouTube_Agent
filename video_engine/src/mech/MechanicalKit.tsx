import React from "react";
import { interpolateColors } from "remotion";
import { CoilSpring, GearWheel, INK } from "../components/MechanicalPrimitives";
import type { Archetype, MechNode, MechPipe } from "./rigSchema";

// Draw in a local 100×100 box; the rig owns position and dimensions. All SVG is authored here.
const shell = "M12 86V19Q12 10 20 8L75 4Q83 4 87 12L94 29V81Q94 88 87 90L22 95Q12 95 12 86Z";
const vessel = "M12 15Q50 0 88 15V83Q88 98 50 98T12 83Z";
const cup = "M8 26Q33 22 73 26L65 80Q62 93 38 93T15 80Z";
const bolt = (x: number, y: number) => (
  <g key={`${x}-${y}`}>
    <circle cx={x} cy={y} r="2" fill="#ced8db" />
    <path d={`M${x - 1} ${y + 1}l2 -2`} strokeWidth=".7" />
  </g>
);

function Liquid({ act, frame, clip, color }: { act: number; frame: number; clip: string; color: string }) {
  const h = 99 - 83 * act,
    wave = Math.sin(frame * 0.12) * 3;
  return (
    <g clipPath={`url(#${clip})`} stroke="none">
      <path d={`M0 ${h}q20 ${-5 + wave} 45 0t55 0v106H0Z`} fill={color} />
      <path d={`M0 ${h}q20 ${-5 + wave} 45 0t55 0`} fill="none" stroke="#effcff" strokeWidth="2" />
      {[22, 44, 72].map((x, i) => (
        <circle
          key={x}
          cx={x}
          cy={99 - ((frame * 0.4 + i * 12) % 36) * act}
          r="1.5"
          fill="white"
          opacity={act * 0.65}
        />
      ))}
    </g>
  );
}

function Context({
  node,
  act,
  frame,
  metal,
  clip,
}: {
  node: MechNode;
  act: number;
  frame: number;
  metal: string;
  clip: string;
}) {
  switch (node.variant) {
    case "cup":
      return (
        <>
          <ellipse cx="45" cy="94" rx="44" ry="5" fill={metal} />
          <path d="M70 37Q101 27 91 56Q84 70 66 69" fill="none" strokeWidth="9" />
          <path d={cup} fill="#dbeafe" />
          <Liquid act={act} frame={frame} clip={clip} color={node.color ?? "#854d27"} />
          <path d={cup} fill="none" />
          <ellipse cx="40" cy="26" rx="32" ry="5" fill="#627986" />
        </>
      );
    case "plate":
      return (
        <>
          <ellipse cx="50" cy="68" rx="47" ry="18" fill={metal} />
          <ellipse cx="50" cy="63" rx="46" ry="15" fill="#f0f5ec" />
          <ellipse cx="50" cy="63" rx="31" ry="8" fill="#afcad2" />
        </>
      );
    case "tire":
      return (
        <>
          <circle cx="50" cy="50" r="47" fill="#263545" />
          <circle cx="50" cy="50" r="38" fill="none" stroke="#69808c" strokeDasharray="4 6" />
          <GearWheel cx={50} cy={50} radius={25} rotation={0} teeth={8} color="#b5c3c7" />
        </>
      );
    case "hand":
      return (
        <path
          fill={node.color ?? "#dba079"}
          d="M12 94L9 61Q8 55 13 54L32 66 25 22Q24 14 32 15L42 45 40 10Q42 3 48 8L55 43 58 14Q61 8 66 14L67 47 76 27Q82 22 84 29L76 69Q73 82 59 94Z"
        />
      );
    case "paper":
      return (
        <g transform={`translate(0 ${-7 * act})`}>
          <path d="M15 13L65 8 84 26 82 93 17 96Z" fill="#f7eed5" />
          <path d="M65 8L64 28 84 26" fill="#cbbd9b" />
          <path d="M27 45l41 -3M27 57l32 -2" stroke="#aca58f" />
        </g>
      );
    case "shower":
      return (
        <>
          <path d="M8 21H36Q50 21 53 37" fill="none" strokeWidth="10" />
          <path d="M24 52Q47 16 78 46L80 53Z" fill={metal} />
          {[31, 45, 59, 72].map((x) => (
            <path
              key={x}
              d={`M${x} 59l-6 33`}
              stroke="#38bdf8"
              opacity={act}
              strokeDasharray="5 5"
              strokeDashoffset={-frame % 10}
            />
          ))}
        </>
      );
  }
}

// Flow bands bend around the upper surface. Use different dash velocities above and below.
function Slipstream({ frame }: { frame: number }) {
  return (
    <g fill="none" stroke="#b9f4ff" strokeWidth="1" opacity=".85">
      {[-13, -6, 6, 13].map((offset, i) => (
        <path
          key={offset}
          transform={`translate(0 ${offset})`}
          d={offset < 0 ? "M-5 53Q13 53 26 36Q39 22 65 40T105 50" : "M-5 57Q22 55 40 64T105 55"}
          strokeDasharray="6 4"
          strokeDashoffset={-frame * (i < 2 ? 0.85 : 0.38)}
        />
      ))}
    </g>
  );
}

export function RenderMechNode({
  node,
  act,
  frame,
  phase,
  archetype = "appliance_box",
}: {
  node: MechNode;
  act: number;
  frame: number;
  phase: number;
  archetype?: Archetype;
}) {
  const id = `kit-${node.id}`,
    metal = `url(#${id}-metal)`,
    coat = `url(#${id}-coat)`,
    clip = `${id}-clip`;
  const color = node.color ?? "#339399";
  const hot = interpolateColors(act, [0, 0.5, 1], ["#97a6ae", "#e99039", "#ff4923"]);
  let art: React.ReactNode;
  switch (node.type) {
    case "custom_shape":
      art = (
        <>
          {archetype === "aerodynamic_wing" && <Slipstream frame={frame} />}
          <svg width="100" height="100" viewBox={node.viewBox} preserveAspectRatio="none">
            {node.paths!.map(({ d, fill }, i) => (
              <path key={i} d={d} fill={fill} stroke={INK} strokeWidth="2" />
            ))}
          </svg>
        </>
      );
      break;
    case "casing":
      if (archetype === "open_frame") return null;
      if (archetype === "aerodynamic_wing") {
        art = (
          <>
            <Slipstream frame={frame} />
            <path d="M3 55Q18 9 57 37Q77 51 98 53Q66 55 36 62Q11 69 3 55Z" fill={metal} />
            <path d="M6 56Q37 57 67 51" fill="none" strokeWidth="1" />
          </>
        );
        break;
      }
      if (archetype === "cylinder_tube") {
        art = (
          <>
            <rect x="7" y="28" width="76" height="45" rx="12" fill={metal} />
            <path d="M8 27h9v47H8zM72 27h8v47h-8z" fill={coat} />
            <rect x="81" y="43" width="17" height="15" rx="2" fill={metal} />
            <path d="M23 38h42" stroke="#f0fffc" />
          </>
        );
        break;
      }
      if (archetype === "disc_rotary") {
        art = (
          <g transform={`rotate(${frame * 0.6 + phase * 3} 50 50)`}>
            <circle cx="50" cy="50" r="46" fill={metal} />
            <circle cx="50" cy="50" r="30" fill={coat} />
            <circle cx="50" cy="50" r="10" fill="#263844" />
            {[0, 60, 120, 180, 240, 300].map((a) => (
              <g key={a} transform={`rotate(${a} 50 50)`}>
                <path d="M48 9l7 8" />
                <circle cx="50" cy="25" r="3" fill="#233542" />
              </g>
            ))}
          </g>
        );
        break;
      }
      art = (
        <>
          <path d={shell} fill={coat} />
          <path d="M78 6L88 26V84L78 90Z" fill="#223f50" />
          <path d="M14 19L76 13V78L15 85Z" fill={metal} />
          <path d="M19 32L71 28V73L19 77Z" fill="#254851" />
          <path d="M21 35L47 33 24 72 21 72Z" fill="#61858b" stroke="none" />
          <path d="M17 89L77 84" stroke="#93b5b5" />
          {[32, 36, 40, 44].map((y) => (
            <path key={y} d={`M81 ${y}l5 -1`} strokeWidth="1.5" />
          ))}
          <circle cx="64" cy="21" r="3.4" fill="#ffc05f" />
          {bolt(21, 23)}
          {bolt(73, 80)}
        </>
      );
      break;
    case "tank":
      art = (
        <>
          <path d={vessel} fill="#d0e8ec" />
          <Liquid act={act} frame={frame} clip={clip} color={node.color ?? "#3aaed0"} />
          <path d={vessel} fill="none" />
          <ellipse cx="50" cy="15" rx="38" ry="8" fill={metal} />
          <path d="M22 29V78" stroke="white" opacity=".65" />
          {[36, 49, 62, 75].map((y) => (
            <path key={y} d={`M70 ${y}h12`} />
          ))}
        </>
      );
      break;
    case "piston":
      art = (
        <>
          <rect x="24" y="4" width="52" height="65" rx="9" fill={metal} />
          <rect x="31" y="12" width="38" height="50" rx="4" fill="#203340" />
          <g transform={`translate(0 ${act * 29})`}>
            <path d="M44 24h12v42H44Z" fill={metal} />
            <rect x="32" y="14" width="36" height="12" rx="3" fill={coat} />
            <path d="M38 64h24l-12 7Z" fill="#d6e1df" />
          </g>
          {bolt(29, 9)}
          {bolt(71, 9)}
        </>
      );
      break;
    case "heater":
      art = (
        <>
          <rect x="4" y="20" width="92" height="67" rx="12" fill={metal} />
          <rect x="12" y="28" width="76" height="50" rx="6" fill="#342e30" />
          {[9, 5].map((w) => (
            <path
              key={w}
              d="M7 63H19Q24 63 24 56V42Q24 33 31 33T38 42V61Q38 70 45 70T52 61V43Q52 34 59 34T66 43V60Q66 68 74 68H94"
              fill="none"
              strokeWidth={w}
              stroke={w === 9 ? INK : hot}
            />
          ))}
          {[32, 51, 68].map((x, i) => (
            <path
              key={x}
              d={`M${x} 20q${6 * Math.sin(frame * 0.13 + i)} -5 1 -10t0 -10`}
              stroke="#fff2d7"
              opacity={act * 0.85}
              fill="none"
            />
          ))}
        </>
      );
      break;
    case "valve":
      art = (
        <>
          <path d="M5 39H95V68H5Z" fill={metal} />
          <circle cx="50" cy="52" r="24" fill="#325462" />
          <g transform={`rotate(${act * 86} 50 52)`}>
            <rect x="45" y="28" width="10" height="48" rx="4" fill={coat} />
            <path d="M50 52V20l17 -7" fill="none" strokeWidth="5" />
          </g>
          <circle cx="50" cy="52" r="4" fill="#f8b54e" />
        </>
      );
      break;
    case "turbine":
      art = (
        <>
          <circle cx="50" cy="50" r="46" fill={metal} />
          <circle cx="50" cy="50" r="39" fill="#132c37" />
          <GearWheel cx={50} cy={50} radius={33} color={node.color ?? "#ebb052"} rotation={phase * 7} teeth={12} />
        </>
      );
      break;
    case "chamber":
      art = (
        <g transform={`translate(${act * act * 2 * Math.sin(frame * 1.7)} 0)`}>
          <path d="M12 26Q50 9 88 26L74 76Q50 94 26 76Z" fill={coat} />
          <ellipse cx="50" cy="26" rx="41" ry="11" fill={metal} />
          <path d="M29 42l6 27M48 42v32M68 40l-5 30" fill="none" stroke="#fff5ce" opacity=".55" />
        </g>
      );
      break;
    case "spring":
      art = (
        <>
          <path d="M10 92H90M10 8H90" strokeWidth="6" />
          <CoilSpring
            x={50}
            y={50 + 22 * act}
            width={52}
            height={84}
            coils={6}
            wire={4}
            compression={act}
            color={node.color ?? "#e5b75b"}
          />
        </>
      );
      break;
    case "context_object":
      art = <Context node={node} act={act} frame={frame} metal={metal} clip={clip} />;
      break;
  }
  return (
    <g
      transform={`translate(${node.x - node.w / 2} ${node.y - node.h / 2}) scale(${node.w / 100} ${node.h / 100})`}
      stroke={INK}
      strokeWidth={Math.min(3.3, 430 / Math.max(node.w, node.h))}
      strokeLinejoin="round"
      strokeLinecap="round"
    >
      <defs>
        <linearGradient id={`${id}-metal`} x2="85%" y2="75%">
          <stop stopColor="#eff4e9" />
          <stop offset=".46" stopColor="#a8c0c3" />
          <stop offset="1" stopColor="#566e7c" />
        </linearGradient>
        <linearGradient id={`${id}-coat`} x2="80%" y2="85%">
          <stop stopColor="#a9dfd8" />
          <stop offset=".46" stopColor={color} />
          <stop offset="1" stopColor="#234355" />
        </linearGradient>
        <clipPath id={clip}>
          <path d={node.type === "tank" ? vessel : cup} />
        </clipPath>
      </defs>
      {art}
    </g>
  );
}

export function RenderMechPipe({ pipe, flow, phase }: { pipe: MechPipe; flow: number; phase: number }) {
  const color = pipe.color ?? "#38bdf8",
    points = pipe.points.map((p) => p.join(",")).join(" ");
  // Chevrons follow the tangent of each segment (including elbows), in point order.
  return (
    <g fill="none" strokeLinecap="round" strokeLinejoin="round">
      {[24, 17, 9].map((w, i) => (
        <polyline key={w} points={points} strokeWidth={w} stroke={[INK, "#8da7ac", "#355464"][i]} />
      ))}
      <polyline points={points} stroke={color} strokeWidth="8" opacity={flow * 0.8} />
      {pipe.points.slice(1).map(([x, y], i) => {
        const [x0, y0] = pipe.points[i],
          dx = x - x0,
          dy = y - y0,
          length = Math.hypot(dx, dy);
        return (
          <g
            key={i}
            transform={`translate(${x0} ${y0}) rotate(${(Math.atan2(dy, dx) * 180) / Math.PI})`}
            opacity={flow}
          >
            {Array.from({ length: Math.ceil(length / 38) }, (_, j) => {
              const d = j * 38 + ((phase * 3) % 38);
              return d + 6 < length && <path key={j} d={`M${d} -4l5 4 -5 4`} stroke="#effffd" strokeWidth="3" />;
            })}
          </g>
        );
      })}
    </g>
  );
}
