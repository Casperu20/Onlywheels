import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ProductDetail } from "@/features/catalog";
import { WheelViewer } from "@/features/showroom3d";
import { finishMaterial } from "@/features/showroom3d/materials";
import type { ModelCanvasProps } from "@/features/showroom3d/ModelCanvas";
import type { CarViewModel } from "@/features/showroom3d/carGeometry";
import { wheelSpec } from "@/features/showroom3d/procedural";

const state = vi.hoisted(() => ({
  webgl: true,
  mode: "ready" as "ready" | "loading" | "error",
  props: null as ModelCanvasProps | null,
  clear: vi.fn(),
}));

vi.mock("@/features/showroom3d/webgl", () => ({ supportsWebGL: () => state.webgl }));

vi.mock("@/features/showroom3d/ModelCanvas", () => ({
  clearModel: state.clear,
  default: function FakeCanvas(props: ModelCanvasProps) {
    state.props = props;
    if (state.mode === "error") throw new Error("GLB parse failed");
    return <FakeScene {...props} />;
  },
}));

function FakeScene({ onReady, label }: ModelCanvasProps) {
  useEffect(() => {
    if (state.mode === "ready") onReady();
  }, [onReady]);
  return <div role="img" aria-label={label} />;
}

const MODEL: NonNullable<ProductDetail["model_3d"]> = {
  glb_file: "/media/models3d/ch-r.glb",
  thumbnail: null,
  finish_materials: { black: { color: "#101010" } },
};

const CAR: CarViewModel = {
  name: "Generic sedan",
  glb_file: "/media/models3d/cars/sedan.glb",
  length_m: "4.200",
  front: "+z",
  wheel_anchors: {
    axis: "x",
    wheels: [
      { x: -1.2, y: 0.3, z: -0.7 },
      { x: -1.2, y: 0.3, z: 0.7 },
      { x: 1.2, y: 0.3, z: -0.7 },
      { x: 1.2, y: 0.3, z: 0.7 },
    ],
  },
  attribution: "Generic car by Example, CC BY 4.0",
  source_url: "https://example.com/car",
};

function renderViewer(
  model: ProductDetail["model_3d"],
  finish = "black",
  car: CarViewModel | null = null,
  view: "wheel" | "car" = "wheel",
  onViewChange = vi.fn(),
) {
  return render(
    <WheelViewer
      model={model}
      finish={finish}
      name="BBS CH-R"
      image="/media/ch-r.jpg"
      seed="bbs-ch-r"
      size={{ diameterIn: 19, widthIn: "8.5", pcd: "5x120" }}
      car={car}
      view={view}
      onViewChange={onViewChange}
    />,
  );
}

beforeEach(() => {
  state.webgl = true;
  state.mode = "ready";
  state.props = null;
  state.clear.mockReset();
});

afterEach(() => vi.restoreAllMocks());

describe("WheelViewer", () => {
  it("draws a generic 3D wheel sized from the variant when the product has no model", async () => {
    renderViewer(null, "bronze");
    expect(await screen.findByRole("img", { name: "Model 3D: BBS CH-R" })).toBeInTheDocument();
    expect(screen.getByText("Previzualizare 3D generică")).toBeInTheDocument();
    expect(state.props?.url).toBeNull();
    expect(state.props?.spec).toEqual(wheelSpec({ diameterIn: 19, widthIn: "8.5", pcd: "5x120", seed: "bbs-ch-r" }));
    expect(state.props?.material.color).toBe("#8c6a43");
  });

  it("falls back to the photo when the device has no WebGL, with or without a model", () => {
    state.webgl = false;
    const view = renderViewer(MODEL);
    expect(screen.getByText("Dispozitivul nu poate afișa 3D")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "BBS CH-R" })).toHaveAttribute("src", "/media/ch-r.jpg");
    view.unmount();
    renderViewer(null);
    expect(screen.getByText("Dispozitivul nu poate afișa 3D")).toBeInTheDocument();
    expect(state.props).toBeNull();
  });

  it("shows progress until the model has loaded", async () => {
    state.mode = "loading";
    renderViewer(MODEL);
    expect(await screen.findByRole("status")).toHaveTextContent("Se încarcă modelul 3D…");
  });

  it("renders the GLB with the finish material", async () => {
    renderViewer(MODEL);
    expect(await screen.findByRole("img", { name: "Model 3D: BBS CH-R" })).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(state.props?.url).toBe(MODEL.glb_file);
    expect(screen.queryByText("Previzualizare 3D generică")).not.toBeInTheDocument();
    expect(state.props?.material).toEqual({ color: "#101010", metalness: 0.6, roughness: 0.35 });
  });

  it("passes the selected car to the canvas and displays its attribution", async () => {
    renderViewer(MODEL, "bronze", CAR, "car");

    expect(await screen.findByRole("img", { name: "Model 3D: BBS CH-R" })).toBeInTheDocument();
    expect(state.props?.car).toEqual(CAR);
    expect(screen.getByRole("link", { name: CAR.attribution })).toHaveAttribute("href", CAR.source_url);
  });

  it("offers a return to wheel-only view after a car GLB fails to load", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    state.mode = "error";
    const onViewChange = vi.fn();
    renderViewer(MODEL, "black", CAR, "car", onViewChange);

    expect(await screen.findByRole("alert")).toHaveTextContent("Modelul 3D nu s-a putut încărca");
    await userEvent.click(screen.getByRole("button", { name: "Înapoi la janta" }));
    expect(onViewChange).toHaveBeenCalledWith("wheel");
  });

  it("clears both wheel and car GLTF caches when retrying the car view", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    state.mode = "error";
    renderViewer(MODEL, "black", CAR, "car");

    await screen.findByRole("alert");
    state.mode = "ready";
    await userEvent.click(screen.getByRole("button", { name: /Reîncearcă/ }));

    expect(state.clear).toHaveBeenNthCalledWith(1, MODEL.glb_file);
    expect(state.clear).toHaveBeenNthCalledWith(2, CAR.glb_file);
  });

  it("recovers from a failed GLB load", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    state.mode = "error";
    renderViewer(MODEL);
    expect(await screen.findByRole("alert")).toHaveTextContent("Modelul 3D nu s-a putut încărca");

    state.mode = "ready";
    await userEvent.click(screen.getByRole("button", { name: /Reîncearcă/ }));
    expect(state.clear).toHaveBeenCalledWith(MODEL.glb_file);
    expect(await screen.findByRole("img", { name: "Model 3D: BBS CH-R" })).toBeInTheDocument();
  });

  it("updates the material when the finish changes", async () => {
    const view = renderViewer(MODEL, "black");
    await screen.findByRole("img", { name: "Model 3D: BBS CH-R" });
    await act(async () => {
      view.rerender(<WheelViewer model={MODEL} finish="bronze" name="BBS CH-R" image={null} />);
    });
    expect(state.props?.material.color).toBe("#8c6a43");
  });
});

describe("finishMaterial", () => {
  it("uses safe defaults for missing, partial or invalid finish data", () => {
    expect(finishMaterial(undefined, "chrome")).toEqual({ color: "#e8eaed", metalness: 1, roughness: 0.05 });
    expect(finishMaterial({}, "unknown")).toEqual(finishMaterial({}, "silver"));
    expect(finishMaterial({ silver: { color: "red; background:url(x)", metalness: 7, roughness: -1 } }, "silver")).toEqual({
      color: "#c9ccd1",
      metalness: 1,
      roughness: 0,
    });
    expect(
      finishMaterial({ white: { metalness: Number.NaN, roughness: 0.5 } } as never, "white"),
    ).toEqual({ color: "#f2f2f2", metalness: 0.2, roughness: 0.5 });
  });
});
