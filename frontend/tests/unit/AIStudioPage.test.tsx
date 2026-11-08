import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Generation, StudioInfo } from "@/features/ai-studio";
import { AIStudioPage } from "@/routes/AIStudioPage";

const state = vi.hoisted(() => ({
  info: null as StudioInfo | null,
  generations: [] as Generation[],
  create: vi.fn(),
  remove: vi.fn(),
  retry: vi.fn(),
}));

vi.mock("@/features/ai-studio", () => ({
  isActive: (status: string) => status === "queued" || status === "running",
  useStudioInfo: () => ({ data: state.info, isPending: false }),
  useGenerations: () => ({ data: state.generations, isError: false }),
  useCreateGeneration: () => ({ mutate: state.create, isPending: false }),
  useDeleteGeneration: () => ({ mutate: state.remove, isPending: false }),
  useRetryGeneration: () => ({ mutate: state.retry, isPending: false }),
  usePrivateImage: (url: string | null) => ({ src: url ? `blob:${url}` : null, isError: false }),
}));

const INFO: StudioInfo = {
  enabled: true,
  daily_limit: 5,
  remaining_today: 3,
  max_upload_bytes: 1024,
  retention_days: 30,
  scenes: [
    { value: "city_night", label: "City at night" },
    { value: "studio", label: "Studio" },
  ],
  styles: [{ value: "photo", label: "Photorealistic" }],
};

function generation(fields: Partial<Generation>): Generation {
  return {
    id: "11111111-2222-3333-4444-555555555555",
    status: "done",
    scene: "city_night",
    style: "photo",
    variant: null,
    variant_name: null,
    error: "",
    input_url: "/api/v1/ai/generations/1/input/",
    result_url: "/api/v1/ai/generations/1/result/",
    created_at: "2026-01-01T12:00:00Z",
    finished_at: "2026-01-01T12:01:00Z",
    ...fields,
  };
}

function renderPage(path = "/ai-studio") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <AIStudioPage />
    </MemoryRouter>,
  );
}

const photo = (type = "image/jpeg", size = 10) => new File([new Uint8Array(size)], "car.jpg", { type });

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
  state.info = { ...INFO };
  state.generations = [];
  state.create.mockReset();
  state.remove.mockReset();
  state.retry.mockReset();
});

describe("AIStudioPage", () => {
  it("explains when the studio is switched off", () => {
    state.info = { ...INFO, enabled: false };
    renderPage();
    expect(screen.getByText("AI Studio nu este disponibil momentan")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Generează imaginea/ })).not.toBeInTheDocument();
  });

  it("uploads a photo with the chosen wheel, scene and style", async () => {
    renderPage("/ai-studio?variant=v-1&wheel=BBS%20CH-R%2019%22");
    expect(screen.getByText('BBS CH-R 19"')).toBeInTheDocument();
    expect(screen.getByText("Mai ai 3 din 5 generări azi.")).toBeInTheDocument();

    const file = photo();
    await userEvent.upload(screen.getByLabelText("Fotografia mașinii"), file);
    await userEvent.selectOptions(screen.getByLabelText("Decor"), "studio");
    await userEvent.click(screen.getByRole("button", { name: /Generează imaginea/ }));

    expect(state.create).toHaveBeenCalledWith(
      { image: file, scene: "studio", style: "photo", variant: "v-1" },
      expect.anything(),
    );
  });

  it("rejects unsupported or oversized files before uploading", async () => {
    renderPage();
    const input = screen.getByLabelText("Fotografia mașinii");
    fireEvent.change(input, { target: { files: [photo("image/gif")] } });
    expect(screen.getByRole("alert")).toHaveTextContent("Alege o fotografie JPEG, PNG sau WebP.");

    fireEvent.change(input, { target: { files: [photo("image/png", 4096)] } });
    expect(screen.getByRole("alert")).toHaveTextContent("Fotografia este prea mare");

    await userEvent.click(screen.getByRole("button", { name: /Generează imaginea/ }));
    expect(state.create).not.toHaveBeenCalled();
  });

  it("blocks generating once the daily limit is used", () => {
    state.info = { ...INFO, remaining_today: 0 };
    renderPage();
    expect(screen.getByText("Ai folosit toate generările de azi. Revino mâine.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generează imaginea/ })).toBeDisabled();
  });

  it("labels results as illustrative and offers download and delete", async () => {
    state.generations = [generation({ variant_name: "BBS CH-R" })];
    renderPage();
    expect(screen.getByText("Ilustrație AI")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Imagine generată cu AI" })).toHaveAttribute(
      "src",
      "blob:/api/v1/ai/generations/1/result/",
    );
    expect(screen.getByRole("link", { name: /Descarcă/ })).toHaveAttribute("download");
    await userEvent.click(screen.getByRole("button", { name: /Șterge/ }));
    expect(state.remove).toHaveBeenCalledWith(generation({}).id, expect.anything());
  });

  it("shows progress for running jobs and retry for failed ones", async () => {
    state.generations = [
      generation({ id: "a", status: "running", result_url: null }),
      generation({ id: "b", status: "failed", result_url: null, error: "Filtrul de siguranță a respins imaginea." }),
    ];
    renderPage();
    expect(screen.getByText("Se generează…")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Filtrul de siguranță");
    expect(screen.queryByText("Ilustrație AI")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Reîncearcă/ }));
    expect(state.retry).toHaveBeenCalledWith("b", expect.anything());
  });
});
