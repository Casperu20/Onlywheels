# Car showroom: selected wheels fitted on a 3D car

Date: 2026-11-08 · Status: approved

## Intent

Today `/showroom` shows one wheel on its own (the uploaded GLB, or the free code-drawn generic wheel). Visitors want to see
**the wheel on a car**, like the configurators on big wheel shops (e.g. ejante.ro). The owner (a student) cannot model cars
by hand and has no budget, so the cars must come from free, commercially usable downloads (Sketchfab CC-BY), uploaded in
the Django admin without code changes.

Success: a visitor picks wheel + finish + size, flips "On a car", and sees all four wheels mounted on a realistic 3D car
they can rotate. If their active car (garage / vehicle search) has a 3D model, that car is shown; otherwise a generic body.

## Goals

- Admin-managed car models: upload a GLB, set body type, real length, optional link to a vehicle model, and the author
  credit. No code change to add a car.
- The car's own wheels are found automatically (by node/material names) and hidden; ours are mounted in their place.
  When detection fails, the admin can enter wheel positions by hand.
- Our wheel (uploaded GLB or generic wheel) is shown at its **real size** on a car scaled to its **real length**.
- A few generic bodies (hatchback, sedan, SUV from the CC-BY "Generic passenger car pack") plus a few real cars for the
  showcase (e.g. Dacia Logan, BMW E46, BMW E30).
- CC-BY credit shown under the viewer whenever a car is visible.
- The current wheel-only view stays as the default and as the fallback (no cars uploaded, car fails to load, or no WebGL
  → existing photo fallback).

## Non-goals

- Car paint colour picker, ride height, ET/offset or track-width visuals, steering, suspension, tyre-size simulation.
- Downloading models from Sketchfab automatically (downloads need the owner's free Sketchfab login).
- Modelling or editing cars in code; procedural car bodies.
- A car per every generation in the database.

## Anti-goals (would be a failure even if it "works")

- Wheels visibly floating, sunk into the body or at the wrong side (axle mirrored wrong).
- The first `/showroom` load gets slower for people who never switch to "On a car" (cars load only on demand).
- Shipping a third-party model without its credit, or using NC/no-derivatives licences.
- Breaking the existing wheel viewer, its tests, the CSP, or the service-worker precache budget.

## Constraints

- No new runtime dependencies; three / drei / r3f already present. three and drei must stay inside the lazy
  `ModelCanvas` chunk (a separate module importing them made Rollup split chunks and the service worker precache them),
  so any new three-using code lives in `ModelCanvas.tsx` or is only imported from it; pure maths goes in a three-free
  module like `procedural.ts`.
- GLBs are served from `/media` (R2 in production, CORS rule already documented). Same Draco decoder path.
- Test-first, backend + frontend gates green (pytest, ruff check, makemigrations --check, spectacular; vitest, tsc,
  eslint, build). Browser smoke test with the real CSP.
- Licensing: only CC0 / CC-BY / CC-BY-SA style licences that allow commercial use and modification. Brand cars (BMW,
  Dacia) are a design-rights grey area: fine for the university demo, flagged in SETUP for a real launch.

## Approaches considered

1. **Admin-uploaded cars, wheel positions auto-detected — chosen.** New model + admin + public list API; the browser
   finds the car's wheels when it loads the GLB, with a manual override in the admin. Most upfront work, but cars can be
   added any time without code.
2. Cars bundled in the frontend with hand-set positions. Faster, but every car is a redeploy, credits are hard-coded and
   the site download grows. Rejected by the owner.
3. Car body drawn in code. Free but looks poor next to the premium design. Dropped.

## Decided design

### Data (backend, `apps.catalog`)

New `CarModel3D` (my call: lives next to `Model3D` in catalog; public endpoint under catalog):

| Field | Notes |
|---|---|
| `name` | Shown in the car selector, e.g. "Dacia Logan II", "Generic sedan" |
| `slug` | unique |
| `body_type` | choices: hatchback, sedan, wagon, suv, coupe |
| `glb_file` | `.glb`, uploaded to `models3d/cars/` |
| `length_m` | real car length in metres (e.g. 4.29); the model is scaled to this |
| `vehicle_model` | optional FK to `vehicles.VehicleModel`; matches any generation of that model (my call: model-level, not generation-level, because there are few cars and generations change often) |
| `front` | which way the car's nose points in the GLB: `+z` (glTF convention, default), `-z`, `+x`, `-x` |
| `wheel_anchors` | optional JSON override, see below; empty = auto-detect |
| `detected_anchors`, `detection_status` | read-only, filled on save: `ok` / `failed` + message (see below) |
| `attribution` | required text, e.g. `"Dacia Logan Low Poly" by solid3DDD, CC BY 4.0` |
| `source_url` | optional URL of the original model |
| `is_active`, `sort_order` | visibility and order in the selector |

Public, read-only, unpaginated list `GET /api/v1/catalog/car-models/` returning cars that are active **and** usable
(`wheel_anchors` set, or `detection_status = ok`), with: id, name, slug,
body_type, glb_file URL, length_m, front, vehicle_model id + make/model names, effective anchors (manual override if set,
else detected), attribution, source_url. Also an
optional filter `?generation=<id>` is **not** needed: the frontend gets the generation's model id from the existing
vehicle API (builder: confirm the active-vehicle data has or can cheaply get the model id; if not, add `vehicle_model`
id to whatever endpoint the store is filled from).

Admin: list shows name, body type, active, detection status; edit page shows the detected anchors and the message when
detection failed. A "Preview in showroom" link (`/showroom?view=car&car=<slug>`) is shown for active, usable cars only
(my call: no staff-only preview of inactive cars; the detection status is the pre-publish check).

### Wheel anchors

```json
{"wheels": [{"x": 1.28, "y": 0.31, "z": 0.76}, ...4 items], "axis": "x" }
```

Positions in the car's own GLB units, before scaling; `axis` is the car's length axis. Empty = auto-detect.

**Auto-detect (backend, on save; my call):** done in pure Python from the GLB's JSON chunk, no new dependency. When
POSITION accessor `min`/`max` bounds are present (including bounds retained on Draco-compressed geometry), each mesh's
local box is known without decoding geometry. These bounds are optional in glTF; if missing or unusable, detection
fails with an admin message and the model can be made usable by entering manual anchors. World boxes follow from the
node TRS/matrix chain. A mesh is a stock-wheel part if its node name, an ancestor's
name, its mesh name or its material name matches `/wheel|tire|tyre|rim|felg|roata|brake|caliper|disc/i` (brakes hidden
too, because they clip through our rims). Matched boxes are clustered by centre; the 4 clusters nearest the bottom
corners are kept (a spare wheel in the boot is ignored). Length axis = longer horizontal side of the whole car's box.
Fewer than 4 clusters, or no plausible rectangle (two axles, left/right symmetric within ~10 %) → `detection_status =
failed` with a message; the car stays hidden from the public API until the admin fills `wheel_anchors`. Detection runs
again whenever the GLB changes. The browser only **hides** the stock parts (same name rule) and mounts ours at the
anchors from the API; it does not detect anything itself. Detection logic is plain Python, unit-tested with small
hand-built GLB fixtures.

### Mounting

- Scale the car uniformly so its bounding-box length along `axis` equals `length_m`; place it on the ground (min y = 0).
- Each anchor gets one instance of the current wheel (GLB or generic), real size (1 unit = 1 m), axle across the car,
  face pointing outward (the far-side wheels rotated 180°). Wheel orientation relies on the convention SETUP already
  states for wheel GLBs (axle along Z, face towards +Z); the generic wheel follows it too.
- Size in car view (my call): the generic wheel already follows the selected variant. An uploaded wheel GLB is scaled
  uniformly so its bounding-box diameter equals the tyre outer diameter that `wheelSpec` computes for the selected
  variant, so 17″ vs 19″ looks different on the car too. The wheel-only view keeps showing the GLB unscaled, as today.
- The camera's three-quarter front view uses `front`. Wheel centre height = anchor y (the stock wheel's centre), so
  a bigger diameter sits lower into the arch / lifts visually like the real thing would on the same tyre outer diameter.
  (My call: no automatic ride-height correction.)
- One loaded wheel is cloned four times; materials shared, disposed on change as today.

### UI (`/showroom`)

- New toggle "Wheel only / On a car" (default wheel only; remembers choice in the URL `?view=car`).
- When "On a car": car selector listing active cars, preselected: the car whose `vehicle_model` matches the visitor's
  active vehicle, else the first by `sort_order`. Shows "Your car" next to the matching one.
- Camera framing switches to the whole car, three-quarter front view; same orbit limits idea, pan off.
- Under the viewer: `3D car: <attribution>` linking to `source_url`. Existing wheel credit/notes unchanged.
- The "Generic 3D preview" banner still appears when the wheel itself is generic.
- No cars uploaded → the toggle is hidden. Car fails to load → error with Retry + "Back to wheel only".
- i18n ro + en for all new strings.

### Loading / performance

- Car GLBs load only after switching to "On a car"; not precached by the service worker.
- SETUP tells the owner to optimise downloads with `npx @gltf-transform/cli optimize in.glb out.glb --compress draco
  --texture-compress webp` (run on demand, not added to package.json), target under ~8 MB per car.

### Docs

SETUP: "Cars for the showroom" (where to download, licence rules, optimise command, admin fields, how to fix detection
with `wheel_anchors`, crediting). ROADMAP showroom rows. PROJECT_STRUCTURE if new files.

## Left to the builder

- Exact component split inside `ModelCanvas.tsx`, camera numbers, lighting tweaks, ground shadow (nice to have:
  drei `ContactShadows`, if it stays in the chunk).
- Serializer/viewset shape following existing catalog patterns; tests per existing conventions.
- Clustering thresholds, as long as the unit tests cover: a clean 4-wheel car, a car with brakes as separate nodes, a car
  with a spare wheel in the boot (5th cluster ignored), nested/rotated node transforms, and a car with no wheel names
  (→ failed).
- Verifying with at least the Generic passenger car pack and one real car downloaded by the owner. Until the owner
  downloads them, the browser smoke test uses a small self-made test car GLB (box body + 4 named cylinders).
