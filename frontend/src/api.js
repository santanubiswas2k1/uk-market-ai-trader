import { config } from "./config";
import { getAccessToken } from "./auth";

function apiUrl(path) {
  return `${config.apiBaseUrl.replace(/\/$/, "")}${path}`;
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

export async function getPrediction(symbol) {
  const token = await getAccessToken();
  const response = await fetch(apiUrl(`/predict/${encodeURIComponent(symbol)}`), {
    headers: { Authorization: `Bearer ${token}` },
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || `Prediction failed: ${response.status}`);
  }
  return payload;
}
