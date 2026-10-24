/**
 * 3D showroom (phase 2) – currently a "coming soon" page (routes/PlaceholderPage).
 *
 * Planned implementation:
 * - Dependencies: three, @react-three/fiber, @react-three/drei.
 * - `ShowroomCanvas`: <Canvas> with an environment map, contact shadows and <OrbitControls>
 *   limited to sensible angles; lazy-loaded route so the 3D bundle is not in the main chunk.
 * - Models: car body GLB per vehicle generation + one wheel GLB per product (`catalog.Model3D`,
 *   already exposed as `model_3d` in the product detail API / `ProductDetail` type),
 *   Draco/KTX2-compressed and served from the CDN; `useGLTF.preload` on hover.
 * - Configurator state (Zustand): selected variant, finish, diameter, camera preset.
 *   Changing finish only swaps materials (`finish_materials` JSON from the API);
 *   changing diameter scales the wheel mesh — no API calls.
 * - "Add set to cart" reuses `useCartActions().add` with quantity 4.
 * - "Send to AI studio" renders the canvas to a PNG (`gl.domElement.toBlob`) as AI input.
 * - Fallback for low-end devices (no WebGL2): show product photos instead.
 */
export {};
