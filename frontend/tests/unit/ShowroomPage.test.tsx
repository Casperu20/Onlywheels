import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProductDetail, ProductListItem, Variant } from "@/features/catalog";
import type { CarModel } from "@/features/showroom3d/api";
import { ShowroomPage } from "@/features/showroom3d/ShowroomPage";

const state = vi.hoisted(() => ({
  list: { data: undefined as { results: ProductListItem[] } | undefined, isPending: false, isError: false },
  details: {} as Record<string, ProductDetail>,
  detailError: false,
  listParams: null as Record<string, string> | null,
  cars: [] as CarModel[],
  carModelsError: false,
  activeVehicleId: undefined as string | undefined,
  activeGeneration: undefined as { model: { id: string } } | undefined,
}));

vi.mock("@/features/catalog/hooks", () => ({
  useProducts: (params: Record<string, string>) => {
    state.listParams = params;
    return state.list;
  },
  useProduct: (slug: string) =>
    state.detailError
      ? { isPending: false, isError: true, data: undefined }
      : { isPending: false, isError: false, data: state.details[slug] },
}));

vi.mock("@/features/showroom3d/WheelViewer", () => ({
  WheelViewer: ({
    model,
    finish,
    name,
    image,
    seed,
    size,
    car,
    view,
  }: {
    model: ProductDetail["model_3d"];
    finish: string;
    name: string;
    image: string | null;
    seed: string;
    size?: { diameterIn: number | null; widthIn: string | null; pcd: string };
    car: CarModel | null;
    view: "wheel" | "car";
  }) => (
    <div
      data-testid="viewer"
      data-seed={seed}
      data-size={size ? `${size.diameterIn}x${size.widthIn} ${size.pcd}` : ""}
      data-view={view}
      data-car={car?.slug ?? ""}
    >
      {[name, finish, model?.glb_file ?? "no-model", image ?? "no-image"].join("|")}
    </div>
  ),
}));

vi.mock("@/features/showroom3d/api", () => ({
  useCarModels: () => ({
    data: state.cars,
    isError: state.carModelsError,
  }),
}));

vi.mock("@/features/vehicle/hooks", () => ({
  useGeneration: (id?: string) => ({
    data: id === state.activeVehicleId ? state.activeGeneration : undefined,
  }),
}));

vi.mock("@/features/vehicle/store", () => ({
  useVehicleStore: (selector: (value: { active: { id: string; label: string } | null }) => unknown) =>
    selector(state.activeVehicleId ? { active: { id: state.activeVehicleId, label: "BMW 3 Series" } } : { active: null }),
}));

function variant(id: string, fields: Partial<Variant>): Variant {
  return {
    id,
    sku: id,
    label: "",
    price: "1500.00",
    old_price: null,
    finish: "silver",
    diameter_in: 18,
    width_in: "8.0",
    et_mm: 35,
    pcd: "5x112",
    center_bore_mm: null,
    tire_size: "",
    tire_width_mm: null,
    tire_aspect: null,
    load_index: null,
    speed_rating: "",
    season: "",
    thread_size: "",
    available: 4,
    fitment: null,
    ...fields,
  };
}

function product(slug: string, name: string, fields: Partial<ProductDetail> = {}): ProductDetail {
  const variants = fields.variants ?? [variant(`${slug}-v1`, {})];
  return {
    id: slug,
    slug,
    type: "wheel",
    name,
    brand: { name: "BBS", slug: "bbs" },
    style: "",
    badge: "",
    rating_avg: "0",
    rating_count: 0,
    min_price: "1500.00",
    old_price: null,
    in_stock: true,
    is_favorite: false,
    image: `/media/${slug}.jpg`,
    finishes: [],
    diameters: [],
    cheapest_variant: variants[0] ?? null,
    description: "",
    category: null,
    media: [],
    variants,
    model_3d: { glb_file: `/media/models3d/${slug}.glb`, thumbnail: null, finish_materials: {} },
    ...fields,
  };
}

const CHR = product("ch-r", "CH-R", {
  variants: [
    variant("chr-s18", { finish: "silver", diameter_in: 18, price: "1500.00" }),
    variant("chr-s19", { finish: "silver", diameter_in: 19, price: "1700.00" }),
    variant("chr-b19", { finish: "black", diameter_in: 19, price: "1750.00" }),
  ],
});
const SR = product("sr", "SR");

const location = { search: "" };

function LocationProbe() {
  location.search = useLocation().search;
  return null;
}

function renderPage(path = "/showroom") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <ShowroomPage />
      <LocationProbe />
    </MemoryRouter>,
  );
}

const viewer = () => screen.getByTestId("viewer").textContent;

beforeEach(() => {
  state.list = { data: { results: [CHR, SR] }, isPending: false, isError: false };
  state.details = { "ch-r": CHR, sr: SR };
  state.detailError = false;
  state.cars = [];
  state.carModelsError = false;
  state.activeVehicleId = undefined;
  state.activeGeneration = undefined;
});

describe("ShowroomPage", () => {
  it("lists every wheel (generic 3D for those without a model) and opens the first one", () => {
    renderPage();
    expect(state.listParams).toMatchObject({ type: "wheel" });
    expect(state.listParams).not.toHaveProperty("has_3d");
    expect(viewer()).toBe("BBS CH-R|silver|/media/models3d/ch-r.glb|/media/ch-r.jpg");
    expect(screen.getByRole("link", { name: "Vezi produsul" })).toHaveAttribute("href", "/catalog/ch-r");
  });

  it("passes the selected size and product to the viewer for the generic wheel", async () => {
    renderPage("/showroom?product=ch-r&variant=chr-s18");
    expect(screen.getByTestId("viewer")).toHaveAttribute("data-size", "18x8.0 5x112");
    expect(screen.getByTestId("viewer")).toHaveAttribute("data-seed", "ch-r");
    await userEvent.selectOptions(screen.getByLabelText("Dimensiune"), "chr-s19");
    expect(screen.getByTestId("viewer")).toHaveAttribute("data-size", "19x8.0 5x112");
  });

  it("selects the product and variant from the query string", () => {
    renderPage("/showroom?product=ch-r&variant=chr-b19");
    expect(viewer()).toContain("|black|");
    expect(screen.getByLabelText("Dimensiune")).toHaveValue("chr-b19");
  });

  it("keeps the wheel-only view by default when car models are available", () => {
    state.cars = [carModel("generic-sedan", "Generic sedan")];
    renderPage("/showroom?product=ch-r&variant=chr-s19");

    expect(screen.getByTestId("viewer")).toHaveAttribute("data-view", "wheel");
    expect(screen.getByTestId("viewer")).toHaveAttribute("data-car", "");
    expect(screen.getByRole("button", { name: "Doar janta" })).toHaveAttribute("aria-pressed", "true");
    expect(location.search).toContain("product=ch-r");
    expect(location.search).toContain("variant=chr-s19");
  });

  it("switches to a car view and preserves product, variant, and selected car in the URL", async () => {
    state.cars = [carModel("generic-sedan", "Generic sedan"), carModel("generic-suv", "Generic SUV")];
    renderPage("/showroom?product=ch-r&variant=chr-s19");

    await userEvent.click(screen.getByRole("button", { name: "Pe mașină" }));
    expect(location.search).toContain("product=ch-r");
    expect(location.search).toContain("variant=chr-s19");
    expect(location.search).toContain("view=car");
    expect(location.search).toContain("car=generic-sedan");
    expect(screen.getByTestId("viewer")).toHaveAttribute("data-view", "car");

    await userEvent.selectOptions(screen.getByLabelText("Model de mașină"), "generic-suv");
    expect(location.search).toContain("car=generic-suv");
    expect(location.search).toContain("product=ch-r");
    expect(location.search).toContain("variant=chr-s19");
  });

  it("prefers the active garage vehicle's matching model and labels it", () => {
    state.cars = [
      carModel("generic-sedan", "Generic sedan"),
      carModel("bmw-3-series", "BMW 3 Series", {
        id: "vehicle-model-bmw",
        name: "3 Series",
        make: "BMW",
      }),
    ];
    state.activeVehicleId = "generation-bmw";
    state.activeGeneration = { model: { id: "vehicle-model-bmw" } };
    renderPage("/showroom?view=car");

    expect(screen.getByLabelText("Model de mașină")).toHaveValue("bmw-3-series");
    expect(screen.getByRole("option", { name: "BMW 3 Series (mașina ta)" })).toBeInTheDocument();
    expect(screen.getByTestId("viewer")).toHaveAttribute("data-car", "bmw-3-series");
  });

  it("does not label any car as the user's when no garage vehicle is active", () => {
    state.cars = [
      carModel("generic-sedan", "Generic sedan"),
      carModel("bmw-3-series", "BMW 3 Series", { id: "vehicle-model-bmw", name: "3 Series", make: "BMW" }),
    ];
    renderPage("/showroom?view=car");

    expect(screen.getByRole("option", { name: "Generic sedan" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /mașina ta/ })).not.toBeInTheDocument();
  });

  it("keeps the selected car view when changing wheels and drops the stale variant", async () => {
    state.cars = [carModel("generic-suv", "Generic SUV")];
    renderPage("/showroom?product=ch-r&variant=chr-s19&view=car&car=generic-suv");

    await userEvent.selectOptions(screen.getByLabelText("Model de jantă"), "sr");

    expect(location.search).toContain("product=sr");
    expect(location.search).toContain("view=car");
    expect(location.search).toContain("car=generic-suv");
    expect(location.search).not.toContain("variant=");
    expect(screen.getByTestId("viewer")).toHaveAttribute("data-view", "car");
    expect(screen.getByTestId("viewer")).toHaveAttribute("data-car", "generic-suv");
  });

  it("hides car controls when no usable models are available", () => {
    renderPage();
    expect(screen.queryByRole("button", { name: "Pe mașină" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Model de mașină")).not.toBeInTheDocument();
  });

  it("reports an unavailable car list without blocking wheel-only showroom", () => {
    state.carModelsError = true;
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent("Nu am putut încărca modelele 3D de mașini");
    expect(screen.getByTestId("viewer")).toHaveAttribute("data-view", "wheel");
  });

  it("changes product, finish and size", async () => {
    renderPage();
    await userEvent.selectOptions(screen.getByLabelText("Finisaj"), "black");
    expect(viewer()).toContain("|black|");
    expect(location.search).toContain("variant=chr-b19");

    await userEvent.selectOptions(screen.getByLabelText("Finisaj"), "silver");
    await userEvent.selectOptions(screen.getByLabelText("Dimensiune"), "chr-s19");
    expect(location.search).toContain("variant=chr-s19");

    await userEvent.selectOptions(screen.getByLabelText("Model de jantă"), "sr");
    expect(viewer()).toContain("BBS SR|");
    expect(location.search).toBe("?product=sr");
  });

  function carModel(
    slug: string,
    name: string,
    vehicleModel: { id: string; name: string; make: string } | null = null,
  ): CarModel {
    return {
      id: slug,
      slug,
      name,
      body_type: "sedan",
      glb_file: `/media/models3d/cars/${slug}.glb`,
      length_m: "4.200",
      front: "+z",
      vehicle_model: vehicleModel,
      wheel_anchors: {
        axis: "x",
        wheels: [
          { x: -1.2, y: 0.3, z: -0.7 },
          { x: -1.2, y: 0.3, z: 0.7 },
          { x: 1.2, y: 0.3, z: -0.7 },
          { x: 1.2, y: 0.3, z: 0.7 },
        ],
      },
      attribution: "Car model by Example, CC BY 4.0",
      source_url: "https://example.com/car",
    };
  }

  it("keeps a linked product without a model selectable and passes its photo", () => {
    state.details["plain"] = product("plain", "Plain", { model_3d: null });
    renderPage("/showroom?product=plain");
    expect(viewer()).toBe("BBS Plain|silver|no-model|/media/plain.jpg");
    expect(screen.getByLabelText("Model de jantă")).toHaveValue("plain");
  });

  it("guides the user when the catalogue has no wheels", () => {
    state.list = { data: { results: [] }, isPending: false, isError: false };
    renderPage();
    expect(screen.getByText("Încă nu avem jante în catalog")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Vezi jantele din catalog" })).toHaveAttribute("href", "/catalog?type=wheel");
  });

  it("shows an error when the product cannot be loaded", () => {
    state.detailError = true;
    renderPage("/showroom?product=missing");
    expect(screen.getByRole("alert")).toHaveTextContent("Nu am putut încărca produsul.");
    expect(screen.queryByTestId("viewer")).not.toBeInTheDocument();
  });
});
