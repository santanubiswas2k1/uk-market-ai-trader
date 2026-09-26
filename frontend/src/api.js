import { config } from "./config";
import { getAccessToken } from "./auth";

function apiUrl(path) {
  return `${config.apiBaseUrl.replace(/\/$/, "")}${path}`;
}

function marketFeedUrl(path) {
  return `${config.marketFeedBaseUrl.replace(/\/$/, "")}${path}`;
}

async function readJsonResponse(response, fallbackLabel) {
  const text = await response.text();
  let payload = {};

  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      if (!response.ok) {
        throw new Error(`${fallbackLabel}: HTTP ${response.status}`);
      }
      throw new Error(`${fallbackLabel}: server returned a non-JSON response`);
    }
  }

  if (!response.ok) {
    throw new Error(
      payload.detail || `${fallbackLabel}: HTTP ${response.status}`,
    );
  }

  if (!text) {
    throw new Error(`${fallbackLabel}: server returned an empty response`);
  }

  return payload;
}

export async function getHealth() {
  const response = await fetch(apiUrl("/health"));
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}

export async function getMe() {
  const token = await getAccessToken();
  const response = await fetch(apiUrl("/me"), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(`Profile request failed: ${response.status}`);
  }
  return response.json();
}

export async function getPrediction(symbol, market = "uk") {
  const token = await getAccessToken();
  const response = await fetch(apiUrl(`/predict/${encodeURIComponent(symbol)}?market=${encodeURIComponent(market)}`), {
    headers: { Authorization: `Bearer ${token}` },
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || `Prediction failed: ${response.status}`);
  }
  return payload;
}


export async function searchSymbols(query, market = "uk") {
  const token = await getAccessToken();
  const response = await fetch(
    apiUrl(`/symbols/search?q=${encodeURIComponent(query)}&market=${encodeURIComponent(market)}&limit=8`),
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || `Symbol lookup failed: ${response.status}`);
  }
  return payload.results || [];
}


export async function getLiveQuote(symbol, market = "uk") {
  if (!config.marketFeedBaseUrl) {
    throw new Error("Market feed URL is not configured");
  }

  const token = await getAccessToken();
  const response = await fetch(
    marketFeedUrl(
      `/quote?symbol=${encodeURIComponent(symbol)}&market=${encodeURIComponent(market)}`,
    ),
    {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    },
  );

  return readJsonResponse(response, "Live quote failed");
}


export async function getPerformance(market = "") {
  const token = await getAccessToken();
  const query = market ? `?market=${encodeURIComponent(market)}` : "";
  const response = await fetch(apiUrl(`/performance${query}`), {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || `Performance request failed: ${response.status}`);
  }
  return payload;
}


export async function getScanner(market = "uk", limit = 10) {
  const token = await getAccessToken();
  const response = await fetch(
    apiUrl(
      `/scanner?market=${encodeURIComponent(market)}&limit=${encodeURIComponent(limit)}`,
    ),
    {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    },
  );

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || `Scanner request failed: ${response.status}`);
  }
  return payload;
}
