import "server-only";

/**
 * OSS vs SaaS boundary:
 * - OSS build exposes only "local" unless a private region provider is present.
 * - SaaS/enterprise deployments provide a server-only module that returns real regions.
 *
 * IMPORTANT: UI cannot unlock regions because all validation happens server-side.
 */

export type StudioRegionProvider = {
  listRegions: () => Promise<readonly string[]>;
};

type PrivateModuleShape = {
  regionProvider?: StudioRegionProvider;
  createRegionProvider?: () => StudioRegionProvider | Promise<StudioRegionProvider>;
};

async function loadPrivateProvider(): Promise<StudioRegionProvider | null> {
  const moduleName = process.env.LI_CLOUD_REGIONS_MODULE ?? "@li/lis-cloud/regions";
  try {
    // Avoid bundler resolution in OSS builds where this module doesn't exist.
    // The import is resolved at runtime only in SaaS/enterprise deployments.
    const mod = (await import(/* turbopackIgnore: true */ moduleName)) as PrivateModuleShape;
    if (mod.regionProvider) return mod.regionProvider;
    if (mod.createRegionProvider) return await mod.createRegionProvider();
    return null;
  } catch {
    return null;
  }
}

export async function allowedStudioRegions(): Promise<readonly string[]> {
  const provider = await loadPrivateProvider();
  if (provider) {
    const regions = await provider.listRegions();
    if (regions.length > 0) return regions;
  }
  return ["local"];
}

