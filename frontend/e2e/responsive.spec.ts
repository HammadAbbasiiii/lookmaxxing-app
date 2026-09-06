import { test, expect } from "@playwright/test";

const VIEWPORTS = [
  { width: 1920, height: 1080 },
  { width: 1440, height: 900 },
  { width: 1280, height: 720 },
  { width: 1024, height: 768 },
  { width: 768, height: 1024 },
  { width: 430, height: 932 },
  { width: 390, height: 844 },
  { width: 375, height: 667 },
];

test.describe("responsive layout", () => {
  for (const vp of VIEWPORTS) {
    test(`no horizontal overflow on landing at ${vp.width}x${vp.height}`, async ({
      page,
    }) => {
      await page.setViewportSize(vp);
      await page.goto("/");
      const overflow = await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth + 1,
      );
      expect(overflow).toBe(false);
    });

    test(`no horizontal overflow on login at ${vp.width}x${vp.height}`, async ({
      page,
    }) => {
      await page.setViewportSize(vp);
      await page.goto("/login");
      const overflow = await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth + 1,
      );
      expect(overflow).toBe(false);
    });
  }
});
