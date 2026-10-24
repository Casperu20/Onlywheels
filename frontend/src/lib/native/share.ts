/** Share a product or an AI photo. Falls back to copying the link. Returns false if nothing worked. */
export async function share(data: { title: string; text?: string; url: string }): Promise<boolean> {
  if (navigator.share) {
    try {
      await navigator.share(data);
      return true;
    } catch {
      return false; // user closed the share sheet
    }
  }
  try {
    await navigator.clipboard.writeText(data.url);
    return true;
  } catch {
    return false;
  }
}
