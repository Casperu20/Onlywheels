import { useId, type SVGProps } from "react";

import { cn } from "@/lib/utils";

import type { Finish, ProductType, WheelStyle } from "../api";

/** Metal colours per finish: a diagonal light → dark → light sweep reads as brushed/polished metal. */
const PALETTES: Record<Finish, { face: string[]; lip: string[]; cap: string }> = {
  silver: { face: ["#f6f8fa", "#9aa1ab", "#e8ebef", "#6b727d", "#c9ced5"], lip: ["#ffffff", "#8b929c", "#f2f4f6", "#5c636d"], cap: "#2b2e34" },
  chrome: { face: ["#ffffff", "#5b6270", "#f8fafc", "#2f3540", "#dfe3e8"], lip: ["#ffffff", "#4b5260", "#ffffff", "#3a404b"], cap: "#1f2227" },
  black: { face: ["#6b717b", "#15171b", "#454a53", "#0b0c0e", "#2c3037"], lip: ["#d9dde2", "#5d636c", "#f2f4f6", "#3f444c"], cap: "#0f1012" },
  gunmetal: { face: ["#a8afb8", "#3a3f47", "#7f8690", "#24282e", "#5b616a"], lip: ["#e6e9ed", "#6b717a", "#f4f6f8", "#4a4f57"], cap: "#1c1f23" },
  bronze: { face: ["#f0d09c", "#86602f", "#d9ac6c", "#58401f", "#b8884f"], lip: ["#f8e2bd", "#8f6a3a", "#fff1d6", "#6b4d28"], cap: "#2a2118" },
  white: { face: ["#ffffff", "#cfd4db", "#ffffff", "#aeb5bf", "#eef1f4"], lip: ["#ffffff", "#b9c0c9", "#ffffff", "#9aa2ad"], cap: "#d9dde2" },
};

const CX = 200;
const RIM = 160; // outer radius of the rim lip in the 400×400 drawing
const HUB = 42;
const SPOKE_END = 148;

function polar(r: number, deg: number) {
  const a = ((deg - 90) * Math.PI) / 180;
  return `${(CX + r * Math.cos(a)).toFixed(2)} ${(CX + r * Math.sin(a)).toFixed(2)}`;
}

/** Spoke outlines: "path|angle" for shapes drawn pointing up and rotated, "path|abs" for absolute paths. */
function spokePaths(style: WheelStyle): string[] {
  const rotate = (count: number, local: string) =>
    Array.from({ length: count }, (_, i) => `${local}|${(360 / count) * i}`);

  switch (style) {
    case "split_spoke":
      return rotate(5, "M-10 -42 L-25 -146 L-13 -148 L-2 -44 Z M10 -42 L25 -146 L13 -148 L2 -44 Z");
    case "y_spoke":
      return rotate(5, "M-9 -42 L-9 -88 L-38 -144 L-23 -148 L0 -106 L23 -148 L38 -144 L9 -88 L9 -42 Z");
    case "multi_spoke":
      return rotate(10, "M-5 -42 L-8 -147 L8 -147 L5 -42 Z");
    case "mesh":
      return Array.from({ length: 10 }, (_, i) => {
        const a = i * 36;
        const cross = (dir: 1 | -1) =>
          `M${polar(HUB, a - 4)} L${polar(SPOKE_END, a + dir * 17 - 2.5)} L${polar(SPOKE_END, a + dir * 17 + 2.5)} L${polar(HUB, a + 4)} Z`;
        return `${cross(1)} ${cross(-1)}|abs`;
      });
    case "five_spoke":
    default:
      return rotate(5, "M-12 -42 L-28 -145 Q0 -151 28 -145 L12 -42 Z");
  }
}

function SpokeShapes({ design, ...props }: { design: WheelStyle } & SVGProps<SVGPathElement>) {
  return (
    <>
      {spokePaths(design).map((entry, i) => {
        const [d, angle] = entry.split("|");
        const transform = angle === "abs" ? undefined : `translate(${CX} ${CX}) rotate(${angle})`;
        return <path key={i} d={d} transform={transform} {...props} />;
      })}
    </>
  );
}

interface WheelVisualProps {
  type: ProductType;
  finish?: Finish | "";
  style?: WheelStyle | "";
  /** Show a tyre around the rim (complete sets, hero); tyres themselves always have one. */
  tire?: boolean;
  /** Show brake disc + caliper behind the spokes ("on the car" look). */
  brake?: boolean;
  /** Turn the wheel when the surrounding `.group` is hovered. */
  spin?: boolean;
  /** Text on the tyre sidewall. */
  tireLabel?: string;
  tireSize?: string;
  /** Used to pick the accessory drawing. */
  slug?: string;
  className?: string;
}

/**
 * Studio-style product artwork drawn in SVG, shown until real photos are uploaded in the admin
 * (product media). The spoke design follows the product's style, the colour its finish.
 */
export function WheelVisual({
  type,
  finish,
  style,
  tire,
  brake = false,
  spin = false,
  tireLabel = "ONLYWHEELS",
  tireSize = "225/40 R19 93Y",
  slug = "",
  className,
}: WheelVisualProps) {
  const uid = useId().replace(/:/g, "");
  if (type === "accessory") {
    return <AccessoryArt kind={/inel|ring/.test(slug) ? "rings" : "bolts"} className={className} />;
  }

  const palette = PALETTES[finish || "silver"];
  const design = style || "five_spoke";
  const showTire = type === "tire" || type === "set" || Boolean(tire);
  const showRim = type !== "tire";
  const id = (name: string) => `${uid}-${name}`;
  const url = (name: string) => `url(#${id(name)})`;
  // Rims sold alone fill the frame; with a tyre around them they shrink to fit inside it.
  const rimScale = showTire ? 1 : 1.22;
  const turning = cn(
    spin && "origin-center transition-transform duration-[1400ms] ease-out group-hover:rotate-[72deg]",
  );
  const turningStyle = { transformBox: "view-box" } as const;
  const hole = showRim ? RIM - 2 : 128;

  return (
    <svg viewBox="0 0 400 400" className={cn("aspect-square overflow-visible", className)} aria-hidden>
      <defs>
        <linearGradient id={id("face")} x1="0" y1="0" x2="1" y2="1">
          {palette.face.map((c, i) => (
            <stop key={i} offset={i / (palette.face.length - 1)} stopColor={c} />
          ))}
        </linearGradient>
        <linearGradient id={id("lip")} x1="0.1" y1="0" x2="0.9" y2="1">
          {palette.lip.map((c, i) => (
            <stop key={i} offset={i / (palette.lip.length - 1)} stopColor={c} />
          ))}
        </linearGradient>
        <radialGradient id={id("barrel")}>
          <stop offset="0.35" stopColor="#060708" />
          <stop offset="0.85" stopColor="#1d2025" />
          <stop offset="1" stopColor="#3a3e45" />
        </radialGradient>
        <radialGradient id={id("disc")}>
          <stop offset="0.5" stopColor="#24272c" />
          <stop offset="0.78" stopColor="#5a6068" />
          <stop offset="0.93" stopColor="#474c53" />
          <stop offset="1" stopColor="#25282d" />
        </radialGradient>
        <linearGradient id={id("caliper")} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ff8a4c" />
          <stop offset="0.55" stopColor="#ff4d1f" />
          <stop offset="1" stopColor="#b8300c" />
        </linearGradient>
        <radialGradient id={id("tire")}>
          <stop offset="0.7" stopColor="#24262b" />
          <stop offset="0.86" stopColor="#17181c" />
          <stop offset="0.96" stopColor="#0e0f11" />
          <stop offset="1" stopColor="#050506" />
        </radialGradient>
        <radialGradient id={id("nut")} cx="0.35" cy="0.3">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="0.5" stopColor="#9aa0a8" />
          <stop offset="1" stopColor="#3d4148" />
        </radialGradient>
        <radialGradient id={id("gloss")} cx="0.3" cy="0.25" r="0.6">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.3" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </radialGradient>
        <filter id={id("blur")} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3.5" />
        </filter>
        <path id={id("arcTop")} d={`M ${CX - 171} ${CX} A 171 171 0 0 1 ${CX + 171} ${CX}`} />
        <path id={id("arcBottom")} d={`M ${CX - 186} ${CX} A 186 186 0 0 0 ${CX + 186} ${CX}`} />
      </defs>

      {showTire && (
        <g className={turning} style={turningStyle}>
          <path
            fillRule="evenodd"
            fill={url("tire")}
            d={`M ${CX} ${CX - 198} a 198 198 0 1 0 0.01 0 Z M ${CX} ${CX - hole} a ${hole} ${hole} 0 1 1 -0.01 0 Z`}
          />
          {Array.from({ length: 72 }, (_, i) => (
            <rect
              key={i}
              x={CX - 4}
              y={CX - 199}
              width={8}
              height={i % 2 ? 6 : 9}
              rx={1.5}
              fill="#2a2d32"
              transform={`rotate(${i * 5} ${CX} ${CX})`}
            />
          ))}
          <circle cx={CX} cy={CX} r={182} fill="none" stroke="#2c2f35" strokeWidth="1" />
          <circle cx={CX} cy={CX} r={hole + 6} fill="none" stroke="#000" strokeOpacity="0.6" strokeWidth="5" />
          {!showRim && (
            // tyre on its own: bead edge and the far side's tread seen through the opening
            <>
              <circle cx={CX} cy={CX} r={hole - 12} fill="none" stroke="#1c1e22" strokeWidth="22" strokeDasharray="7 5" />
              <circle cx={CX} cy={CX} r={hole} fill="none" stroke="#4a4e56" strokeWidth="2.5" />
            </>
          )}
          <text fill="#555a63" fontSize="15" fontWeight="800" letterSpacing="4" fontFamily="Arial, sans-serif">
            <textPath href={`#${id("arcTop")}`} startOffset="50%" textAnchor="middle">
              {tireLabel.toUpperCase()}
            </textPath>
          </text>
          <text fill="#464a52" fontSize="12" fontWeight="700" letterSpacing="3" fontFamily="Arial, sans-serif">
            <textPath href={`#${id("arcBottom")}`} startOffset="50%" textAnchor="middle">
              {tireSize}
            </textPath>
          </text>
        </g>
      )}

      {showRim && (
        <g transform={rimScale === 1 ? undefined : `translate(${CX} ${CX}) scale(${rimScale}) translate(${-CX} ${-CX})`}>
          {/* lip, dark barrel and brake disc: everything behind the caliper */}
          <g className={turning} style={turningStyle}>
            <circle cx={CX} cy={CX} r={RIM} fill={url("lip")} />
            <circle cx={CX} cy={CX} r={RIM - 9} fill={url("barrel")} />
            <circle cx={CX} cy={CX} r={RIM - 9} fill="none" stroke="#000" strokeOpacity="0.7" strokeWidth="2" />
            {brake && (
              <>
                <circle cx={CX} cy={CX} r={114} fill={url("disc")} />
                {Array.from({ length: 36 }, (_, i) => (
                  <circle
                    key={i}
                    cx={CX}
                    cy={CX - (84 + (i % 3) * 11)}
                    r={2.4}
                    fill="#121417"
                    transform={`rotate(${i * 10 + (i % 3) * 3} ${CX} ${CX})`}
                  />
                ))}
                <circle cx={CX} cy={CX} r={60} fill="#1b1e22" stroke="#000" strokeOpacity="0.5" strokeWidth="2" />
              </>
            )}
          </g>

          {brake && (
            // the caliper is bolted to the car: it does not turn with the wheel
            <g>
              <path
                d={`M${polar(92, 28)} A92 92 0 0 1 ${polar(92, 80)} L${polar(130, 80)} A130 130 0 0 0 ${polar(130, 28)} Z`}
                fill="#000"
                opacity="0.55"
                transform="translate(3 5)"
                filter={url("blur")}
              />
              <path
                d={`M${polar(92, 28)} A92 92 0 0 1 ${polar(92, 80)} L${polar(130, 80)} A130 130 0 0 0 ${polar(130, 28)} Z`}
                fill={url("caliper")}
                stroke="#7a1f07"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <text
                transform={`translate(${polar(111, 54)}) rotate(54)`}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="11"
                fontWeight="900"
                fontFamily="Arial, sans-serif"
                fill="#fff"
                opacity="0.9"
              >
                OW
              </text>
            </g>
          )}

          {/* spokes in front of the caliper: blurred shadow, metal face, highlight edge */}
          <g className={turning} style={turningStyle}>
            <g transform="translate(4 6)" opacity="0.6" filter={url("blur")}>
              <SpokeShapes design={design} fill="#000" />
            </g>
            <SpokeShapes design={design} fill={url("face")} />
            <SpokeShapes design={design} fill="none" stroke="#ffffff" strokeOpacity="0.28" strokeWidth="1.2" />

            <circle cx={CX} cy={CX} r={HUB + 4} fill={url("face")} />
            <circle cx={CX} cy={CX} r={HUB + 4} fill="none" stroke="#000" strokeOpacity="0.35" strokeWidth="2" />
            {Array.from({ length: 5 }, (_, i) => (
              <g key={i} transform={`rotate(${i * 72 + 36} ${CX} ${CX})`}>
                <circle cx={CX} cy={CX - 31} r={7} fill="#0b0c0e" />
                <circle cx={CX} cy={CX - 31} r={5.5} fill={url("nut")} />
              </g>
            ))}
            <circle cx={CX} cy={CX} r={19} fill={palette.cap} stroke="#000" strokeOpacity="0.5" strokeWidth="2" />
            <text
              x={CX}
              y={CX + 4}
              textAnchor="middle"
              fontSize="11"
              fontWeight="900"
              fontFamily="Arial, sans-serif"
              fill="#ff642d"
            >
              OW
            </text>
            <circle cx={CX} cy={CX} r={RIM - 0.5} fill="none" stroke="#ffffff" strokeOpacity="0.5" strokeWidth="1" />
          </g>
        </g>
      )}

      {/* fixed studio light */}
      <circle cx={CX} cy={CX} r={showTire ? 198 : RIM * rimScale} fill={url("gloss")} />
    </svg>
  );
}

function AccessoryArt({ kind, className }: { kind: "bolts" | "rings"; className?: string }) {
  const uid = useId().replace(/:/g, "");
  const id = (name: string) => `${uid}-${name}`;
  const url = (name: string) => `url(#${id(name)})`;

  if (kind === "rings") {
    return (
      <svg viewBox="0 0 400 400" className={cn("aspect-square", className)} aria-hidden>
        <defs>
          <linearGradient id={id("ring")} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#5b616b" />
            <stop offset="0.5" stopColor="#24272c" />
            <stop offset="1" stopColor="#40454d" />
          </linearGradient>
        </defs>
        {[
          [150, 170],
          [250, 230],
        ].map(([x, y], i) => (
          <g key={i}>
            <ellipse cx={x} cy={y + 14} rx={92} ry={46} fill="#000" opacity="0.35" />
            <ellipse cx={x} cy={y} rx={92} ry={46} fill={url("ring")} />
            <ellipse cx={x} cy={y - 4} rx={62} ry={30} fill="#0b0c0e" />
            <ellipse cx={x} cy={y - 4} rx={62} ry={30} fill="none" stroke="#ff642d" strokeOpacity="0.8" strokeWidth="3" />
          </g>
        ))}
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 400 400" className={cn("aspect-square", className)} aria-hidden>
      <defs>
        <linearGradient id={id("bolt")} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#6b717b" />
          <stop offset="0.35" stopColor="#f2f4f6" />
          <stop offset="0.6" stopColor="#9aa1ab" />
          <stop offset="1" stopColor="#4a4f57" />
        </linearGradient>
      </defs>
      {[-70, 0, 70].map((dx, i) => (
        <g key={i} transform={`translate(${200 + dx} ${210 + (i === 1 ? -20 : 10)}) rotate(${dx / 6})`}>
          <ellipse cx="0" cy="118" rx="34" ry="8" fill="#000" opacity="0.35" />
          <rect x="-14" y="-10" width="28" height="120" rx="3" fill={url("bolt")} />
          {Array.from({ length: 11 }, (_, k) => (
            <rect key={k} x="-14" y={4 + k * 10} width="28" height="2" fill="#2f3339" opacity="0.6" />
          ))}
          <path d="M-30 -10 L30 -10 L18 -40 L-18 -40 Z" fill={url("bolt")} />
          <rect x="-26" y="-74" width="52" height="36" rx="4" fill={url("bolt")} />
          <rect x="-26" y="-74" width="52" height="36" rx="4" fill="none" stroke="#000" strokeOpacity="0.35" />
          <rect x="-4" y="-74" width="8" height="36" fill="#ffffff" opacity="0.25" />
        </g>
      ))}
    </svg>
  );
}
