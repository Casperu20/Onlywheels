import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { handleStaleChunk } from "@/lib/chunkReload";

function preloadError() {
  return new Event("vite:preloadError", { cancelable: true });
}

describe("handleStaleChunk", () => {
  const reload = vi.fn();

  beforeEach(() => {
    sessionStorage.clear();
    reload.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("reloads once and swallows the error when a chunk from an old deploy is missing", () => {
    const event = preloadError();

    handleStaleChunk(event, reload);

    expect(reload).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
  });

  it("does not loop: a second failure right after a reload reaches the error boundary", () => {
    handleStaleChunk(preloadError(), reload);
    const second = preloadError();

    handleStaleChunk(second, reload);

    expect(reload).toHaveBeenCalledTimes(1);
    expect(second.defaultPrevented).toBe(false);
  });

  it("allows another reload after a later deploy", () => {
    vi.useFakeTimers();
    handleStaleChunk(preloadError(), reload);

    vi.advanceTimersByTime(61_000);
    handleStaleChunk(preloadError(), reload);

    expect(reload).toHaveBeenCalledTimes(2);
  });
});
