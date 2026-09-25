const runtime = window.__APP_CONFIG__ || {};

export const config = {
  apiBaseUrl: runtime.apiBaseUrl || import.meta.env.VITE_API_BASE_URL || "",
  marketFeedBaseUrl:
    runtime.marketFeedBaseUrl || import.meta.env.VITE_MARKET_FEED_BASE_URL || "",
  marketFeedRefreshMs: Number(
    runtime.marketFeedRefreshMs ||
      import.meta.env.VITE_MARKET_FEED_REFRESH_MS ||
      60000,
  ),
  entraClientId: runtime.entraClientId || import.meta.env.VITE_ENTRA_CLIENT_ID || "",
  tenantId: runtime.tenantId || import.meta.env.VITE_ENTRA_TENANT_ID || "",
  apiScope: runtime.apiScope || import.meta.env.VITE_API_SCOPE || "",
};
