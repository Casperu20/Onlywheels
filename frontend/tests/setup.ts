import "@testing-library/jest-dom/vitest";

import i18n from "@/i18n";

beforeAll(async () => {
  await i18n.changeLanguage("ro");
});
