const KEY = "ow:chunk-reload-at";
const MIN_INTERVAL_MS = 60_000;

/**
 * After a deploy, hashed chunks of the previous build are gone. Lazy chunks that the service worker
 * does not precache (e.g. the 3D viewer) then fail to import; reloading picks up the new build.
 * Reloads at most once per minute so a genuinely missing chunk still reaches the error boundary.
 */
export function handleStaleChunk(event: Event, reload: () => void = () => window.location.reload()) {
  const last = Number(sessionStorage.getItem(KEY) ?? 0);
  if (Date.now() - last < MIN_INTERVAL_MS) return;
  sessionStorage.setItem(KEY, String(Date.now()));
  event.preventDefault();
  reload();
}

export function installStaleChunkReload() {
  window.addEventListener("vite:preloadError", (event) => handleStaleChunk(event));
}
