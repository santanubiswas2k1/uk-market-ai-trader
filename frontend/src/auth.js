import { PublicClientApplication } from "@azure/msal-browser";
import { config } from "./config";

const authority = config.tenantId
  ? `https://login.microsoftonline.com/${config.tenantId}`
  : undefined;

export const msal = new PublicClientApplication({
  auth: {
    clientId: config.entraClientId,
    authority,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
});

export const loginRequest = {
  scopes: [config.apiScope],
};

export async function initialiseAuth() {
  await msal.initialize();
  const response = await msal.handleRedirectPromise();

  if (response?.account) {
    msal.setActiveAccount(response.account);
  } else {
    const accounts = msal.getAllAccounts();
    if (accounts.length > 0) {
      msal.setActiveAccount(accounts[0]);
    }
  }

  return msal.getActiveAccount();
}

export async function signIn() {
  return msal.loginRedirect(loginRequest);
}

export async function signOut() {
  return msal.logoutRedirect();
}

export async function getAccessToken() {
  const account = msal.getActiveAccount();
  if (!account) {
    throw new Error("Please sign in first.");
  }

  try {
    const response = await msal.acquireTokenSilent({
      ...loginRequest,
      account,
    });
    return response.accessToken;
  } catch {
    await msal.acquireTokenRedirect(loginRequest);
    return null;
  }
}
