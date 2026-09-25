# Authenticated web dashboard

The project includes a React/Vite dashboard in `frontend/`.

## Architecture

```text
Browser
  |
  | HTTPS
  v
Azure Storage static website
  |
  | Microsoft Entra ID / MSAL (Authorization Code + PKCE)
  | Access token for access_as_user
  v
Azure Container Apps FastAPI API
  |
  v
Prediction service
```

The frontend is static and serverless. The backend remains Azure Container Apps with scale-to-zero.

## Authentication

The dashboard uses the existing Entra application registration:

`0e9834ae-b88e-47de-bfad-3aa958feea49`

The API scope is:

`api://0e9834ae-b88e-47de-bfad-3aa958feea49/access_as_user`

MSAL stores authentication state in browser session storage and sends the short-lived access token only to the API.

## One-time redirect URI configuration

After the infrastructure deployment has created the frontend storage endpoint, use Azure Cloud Shell:

```bash
cd ~/uk-market-ai-trader
git pull
bash scripts/configure_frontend_auth.sh
```

The script reads the generated frontend URL from the `serverless-base` deployment and adds it as the SPA redirect URI on the existing Entra application.

This is a one-time Entra configuration step. It needs an identity permitted to edit the application registration.

## Deployment

Run:

**GitHub -> Actions -> Deploy Azure serverless -> Run workflow**

The workflow now:

1. deploys/updates the Azure infrastructure
2. builds the FastAPI container
3. deploys the Container App
4. injects the API URL and Entra configuration into the static frontend
5. builds the React application
6. uploads it to Azure static website storage
7. smoke-tests both API and frontend URLs

## Dashboard features

- Microsoft sign in / sign out
- API online status
- LSE ticker input
- quick ticker buttons
- probability up/down
- UP / NEUTRAL / DOWN signal
- latest source quote
- walk-forward accuracy
- Brier score
- walk-forward fold count
- feature count
- labelled training row count

The site remains research/paper-trading only.
