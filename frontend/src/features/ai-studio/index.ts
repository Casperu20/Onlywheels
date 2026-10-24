/**
 * AI photo studio (phase 2) – currently a "coming soon" page (routes/PlaceholderPage).
 *
 * Planned implementation (backend: apps/ai_studio):
 * - Input: a photo from `pickPhoto()` (lib/native) or a render from the 3D showroom, plus the
 *   selected variant, scene, angle and style.
 * - Upload: request a pre-signed URL, PUT the image directly to storage, then
 *   `POST /api/v1/ai/generations/` → 202 { id }.
 * - Progress: `useQuery` polling `GET /api/v1/ai/generations/{id}/` every 2 s while
 *   status is queued/running (WebSocket later); show the remaining daily quota.
 * - Result gallery per user with download and `share()` (lib/native).
 */
export {};
