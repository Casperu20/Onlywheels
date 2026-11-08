import { Bounds, Center, Environment, Lightformer, OrbitControls, useBounds, useGLTF } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, useEffect, useMemo } from "react";
import { Box3, DoubleSide, Mesh, MeshStandardMaterial, type Material, type Object3D } from "three";

import { fitCarToLength, frontDirection, wheelModelScale, wheelMounts, type Bounds3, type CarViewModel } from "./carGeometry";
import type { FinishMaterial } from "./materials";
import { wheelSpec, type WheelSpec } from "./procedural";

/** Draco decoder copied from the `three` package at build time (see vite.config.ts); never a CDN. */
const DRACO_DECODER = "/draco/";
/** Materials named like this get the finish; otherwise every material except rubber/logo parts. */
const FINISH_PART = /finish|rim/i;
const KEEP_PART = /tire|tyre|rubber|logo|badge|emblem|valve|glass/i;
const WHEEL_PART = /wheel|tire|tyre|rim|felg|roata|brake|caliper|disc/i;

export interface ModelCanvasProps {
  /** Licensed GLB; `null` draws the generic wheel from `spec` instead. */
  url: string | null;
  spec?: WheelSpec;
  car?: CarViewModel | null;
  material: FinishMaterial;
  label: string;
  onReady: () => void;
}

// eslint-disable-next-line react-refresh/only-export-components -- a separate module would split three/drei into another chunk
export function clearModel(url: string) {
  useGLTF.clear(url);
}

function materialsOf(mesh: Mesh): Material[] {
  return Array.isArray(mesh.material) ? mesh.material : [mesh.material];
}

function Wheel({
  url,
  material,
  onReady,
  sizeScale = 1,
}: Omit<ModelCanvasProps, "label" | "url" | "spec" | "car"> & { url: string; sizeScale?: number }) {
  const { scene } = useGLTF(url, DRACO_DECODER);

  const { object, created } = useMemo(() => {
    const clone = scene.clone(true);
    const meshes: Mesh[] = [];
    clone.traverse((node) => {
      if (node instanceof Mesh) meshes.push(node);
    });
    const named = meshes.some((mesh) => materialsOf(mesh).some((m) => FINISH_PART.test(m.name)));
    const shouldPaint = (m: Material) => (named ? FINISH_PART.test(m.name) : !KEEP_PART.test(m.name));

    const replaced = new Map<Material, MeshStandardMaterial>();
    const paint = (source: Material) => {
      if (!shouldPaint(source)) return source;
      let painted = replaced.get(source);
      if (!painted) {
        painted =
          source instanceof MeshStandardMaterial ? source.clone() : new MeshStandardMaterial({ name: source.name });
        painted.color.set(material.color);
        painted.metalness = material.metalness;
        painted.roughness = material.roughness;
        replaced.set(source, painted);
      }
      return painted;
    };
    for (const mesh of meshes) {
      mesh.material = Array.isArray(mesh.material) ? mesh.material.map(paint) : paint(mesh.material);
    }
    return { object: clone, created: [...replaced.values()] };
  }, [scene, material.color, material.metalness, material.roughness]);

  useEffect(() => () => created.forEach((m) => m.dispose()), [created]);
  useEffect(onReady, [onReady]);

  return <primitive object={object} scale={sizeScale} />;
}

const HALF_TURN = Math.PI / 2;

/**
 * Code-drawn wheel (axle along Z, face towards the camera) for products without a GLB:
 * tire, rim barrel with lips, N spokes, hub, lug nuts and centre cap. Free to use, no assets.
 */
function GenericWheel({ spec, material, onReady }: { spec: WheelSpec; material: FinishMaterial; onReady: () => void }) {
  const painted = useMemo(
    () =>
      new MeshStandardMaterial({
        name: "rim",
        color: material.color,
        metalness: material.metalness,
        roughness: material.roughness,
        side: DoubleSide,
      }),
    [material.color, material.metalness, material.roughness],
  );
  const fixed = useMemo(
    () => ({
      tire: new MeshStandardMaterial({ name: "tire", color: "#1b1b1d", metalness: 0, roughness: 0.92 }),
      lug: new MeshStandardMaterial({ name: "lug", color: "#d7d9dc", metalness: 1, roughness: 0.2 }),
      cap: new MeshStandardMaterial({ name: "logo", color: "#111214", metalness: 0.4, roughness: 0.4 }),
    }),
    [],
  );
  useEffect(() => () => painted.dispose(), [painted]);
  useEffect(() => () => Object.values(fixed).forEach((m) => m.dispose()), [fixed]);
  useEffect(onReady, [onReady]);

  const { rimRadius, rimWidth, tireOuter, tireWidth, spokes, spokeWidth, lugs, lugCircle } = spec;
  const tube = (tireOuter - rimRadius) / 2;
  const front = rimWidth / 2;
  const faceZ = front - 0.03;
  const hubRadius = Math.max(lugCircle + 0.022, rimRadius * 0.26);
  const spokeLength = rimRadius - hubRadius + 0.01;

  return (
    <group>
      <mesh material={fixed.tire} scale={[1, 1, tireWidth / 2 / tube]}>
        <torusGeometry args={[rimRadius + tube, tube, 24, 96]} />
      </mesh>
      <mesh material={painted} rotation={[HALF_TURN, 0, 0]}>
        <cylinderGeometry args={[rimRadius * 0.995, rimRadius * 0.995, rimWidth, 96, 1, true]} />
      </mesh>
      {[front, -front].map((z) => (
        <mesh key={z} material={painted} position={[0, 0, z]}>
          <torusGeometry args={[rimRadius, 0.008, 12, 96]} />
        </mesh>
      ))}
      {Array.from({ length: spokes }, (_, index) => (
        <group key={index} rotation={[0, 0, (index * 2 * Math.PI) / spokes]} position={[0, 0, faceZ]}>
          <mesh material={painted} position={[0, hubRadius + spokeLength / 2 - 0.005, 0]}>
            <boxGeometry args={[spokeWidth, spokeLength, 0.024]} />
          </mesh>
        </group>
      ))}
      <mesh material={painted} rotation={[HALF_TURN, 0, 0]} position={[0, 0, faceZ]}>
        <cylinderGeometry args={[hubRadius, hubRadius, 0.05, 48]} />
      </mesh>
      {Array.from({ length: lugs }, (_, index) => {
        const angle = (index * 2 * Math.PI) / lugs + Math.PI / 2;
        return (
          <mesh
            key={index}
            material={fixed.lug}
            rotation={[HALF_TURN, 0, 0]}
            position={[Math.cos(angle) * lugCircle, Math.sin(angle) * lugCircle, faceZ + 0.03]}
          >
            <cylinderGeometry args={[0.0095, 0.0095, 0.018, 6]} />
          </mesh>
        );
      })}
      <mesh material={fixed.cap} rotation={[HALF_TURN, 0, 0]} position={[0, 0, faceZ + 0.028]}>
        <cylinderGeometry args={[Math.min(0.03, lugCircle - 0.016), Math.min(0.03, lugCircle - 0.016), 0.012, 32]} />
      </mesh>
    </group>
  );
}

function boundsOf(box: Box3): Bounds3 {
  return {
    min: { x: box.min.x, y: box.min.y, z: box.min.z },
    max: { x: box.max.x, y: box.max.y, z: box.max.z },
  };
}

function isNamedWheelPart(node: Object3D): boolean {
  if (WHEEL_PART.test(node.name)) return true;
  if (node instanceof Mesh) {
    return materialsOf(node).some((material) => WHEEL_PART.test(material.name));
  }
  return false;
}

function CarScene({
  car,
  wheelUrl,
  spec,
  material,
  onReady,
}: {
  car: CarViewModel;
  wheelUrl: string | null;
  spec: WheelSpec;
  material: FinishMaterial;
  onReady: () => void;
}) {
  const { scene } = useGLTF(car.glb_file, DRACO_DECODER);
  const { object, bounds } = useMemo(() => {
    const clone = scene.clone(true);
    clone.updateMatrixWorld(true);
    const bounds = boundsOf(new Box3().setFromObject(clone));
    const hideWheelParts = (node: Object3D, inheritedWheel: boolean) => {
      const isWheel = inheritedWheel || isNamedWheelPart(node);
      if (isWheel) node.visible = false;
      node.children.forEach((child) => hideWheelParts(child, isWheel));
    };
    hideWheelParts(clone, false);
    return { object: clone, bounds };
  }, [scene]);
  const transform = useMemo(
    () => fitCarToLength(bounds, Number(car.length_m), car.wheel_anchors.axis),
    [bounds, car.length_m, car.wheel_anchors.axis],
  );
  const mounts = useMemo(() => wheelMounts(car.wheel_anchors, transform), [car.wheel_anchors, transform]);

  useEffect(onReady, [onReady]);

  return (
    <>
      <group position={[transform.offset.x, transform.offset.y, transform.offset.z]} scale={transform.scale}>
        <primitive object={object} />
      </group>
      {wheelUrl ? (
        <UploadedWheelSet url={wheelUrl} mounts={mounts} spec={spec} material={material} onReady={onReady} />
      ) : (
        mounts.map((mount, index) => (
          <group
            key={index}
            position={[mount.position.x, mount.position.y, mount.position.z]}
            rotation={[0, mount.rotationY, 0]}
          >
            <GenericWheel spec={spec} material={material} onReady={onReady} />
          </group>
        ))
      )}
    </>
  );
}

function UploadedWheelSet({
  url,
  mounts,
  spec,
  material,
  onReady,
}: {
  url: string;
  mounts: ReturnType<typeof wheelMounts>;
  spec: WheelSpec;
  material: FinishMaterial;
  onReady: () => void;
}) {
  const { scene } = useGLTF(url, DRACO_DECODER);
  const bounds = useMemo(() => {
    scene.updateMatrixWorld(true);
    return boundsOf(new Box3().setFromObject(scene));
  }, [scene]);
  const sizeScale = wheelModelScale(bounds, spec);
  return mounts.map((mount, index) => (
    <group
      key={index}
      position={[mount.position.x, mount.position.y, mount.position.z]}
      rotation={[0, mount.rotationY, 0]}
    >
      <Wheel url={url} material={material} onReady={onReady} sizeScale={sizeScale} />
    </group>
  ));
}

function carCameraPosition(car: CarViewModel): [number, number, number] {
  const front = frontDirection(car.front);
  const length = Number(car.length_m);
  const side = car.wheel_anchors.axis === "x" ? { x: 0, z: 1 } : { x: 1, z: 0 };
  return [
    front.x * length * 0.65 + side.x * length * 0.35,
    length * 0.25,
    front.z * length * 0.65 + side.z * length * 0.35,
  ];
}

/** Re-frame the camera when the generic wheel changes size (Bounds only fits on mount/resize). */
function Refit({ on }: { on: unknown }) {
  const bounds = useBounds();
  useEffect(() => {
    bounds.refresh().clip().fit();
  }, [bounds, on]);
  return null;
}

/** Heavy three.js scene; only loaded through `React.lazy` by WheelViewer. */
export default function ModelCanvas({ url, spec, car = null, material, label, onReady }: ModelCanvasProps) {
  const camera = car
    ? { position: carCameraPosition(car), fov: 35, near: 0.01, far: 100 }
    : { position: [0, 0, 1.4] as [number, number, number], fov: 35, near: 0.01, far: 20 };
  return (
    <Canvas
      role="img"
      aria-label={label}
      dpr={[1, 2]}
      camera={camera}
      className="touch-none"
    >
      <ambientLight intensity={0.35} />
      <directionalLight position={[2, 3, 4]} intensity={1.4} />
      <Environment resolution={256}>
        <Lightformer form="rect" intensity={2} position={[0, 2, 3]} scale={[4, 1, 1]} />
        <Lightformer form="rect" intensity={1} position={[-3, 0, 1]} scale={[2, 2, 1]} />
        <Lightformer form="ring" intensity={1.5} position={[3, 1, -2]} scale={2} />
        <Lightformer form="rect" intensity={0.8} position={[0, 0, 5]} scale={[6, 4, 1]} />
      </Environment>
      <Suspense fallback={null}>
        <Bounds fit clip observe margin={car ? 1.4 : 1.25}>
          {car ? (
            <>
              <CarScene
                car={car}
                wheelUrl={url}
                spec={spec ?? wheelSpec({ seed: "" })}
                material={material}
                onReady={onReady}
              />
              <Refit on={spec} />
            </>
          ) : (
            <>
              <Center>
                {url ? (
                  <Wheel url={url} material={material} onReady={onReady} />
                ) : (
                  <GenericWheel spec={spec ?? wheelSpec({ seed: "" })} material={material} onReady={onReady} />
                )}
              </Center>
              {!url && <Refit on={spec} />}
            </>
          )}
        </Bounds>
      </Suspense>
      <OrbitControls
        makeDefault
        enablePan={false}
        minDistance={car ? 1 : 0.3}
        maxDistance={car ? 20 : 4}
        minPolarAngle={Math.PI / 6}
        maxPolarAngle={(Math.PI * 5) / 6}
      />
    </Canvas>
  );
}
