import type { Generation } from "./api";

/** "BMW Seria 3 G20 / G21 (2019–prezent)" */
export function vehicleLabel(generation: Generation, presentLabel: string): string {
  const years = `${generation.year_from}–${generation.year_to ?? presentLabel}`;
  return `${generation.make.name} ${generation.model.name} ${generation.name} (${years})`;
}
