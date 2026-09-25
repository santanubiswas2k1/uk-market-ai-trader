# Azure serverless deployment

The API is deployed to **Azure Container Apps on the Consumption workload profile**.

Why Container Apps for this project:

- scales to zero when idle
- no VM management
- works naturally with FastAPI, XGBoost, pandas and native Python packages
- supports Managed Identity
- supports Azure Container Registry without registry passwords
- can later add Container Apps Jobs for scheduled model training

## Resources

The base Bicep deployment creates:

- Azure Container Registry
- Azure Container Apps Environment
- User Assigned Managed Identity
- Azure Key Vault
- Storage Account / ADLS Gen2
- Log Analytics Workspace
- Application Insights
- RBAC granting the application identity:
  - AcrPull on ACR
  - Key Vault Secrets User on Key Vault

The application deployment creates a public HTTPS Container App with:

- 0 minimum replicas
- 3 maximum replicas
- 0.5 vCPU / 1 GiB RAM per replica
- health/readiness probes
- Managed Identity
- no registry password
- Key Vault URL and Entra settings supplied as environment variables

## GitHub -> Azure authentication

The deployment workflow uses **OpenID Connect (OIDC)**. Do not create a long-lived Azure client secret for GitHub.

Repository variables required:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_API_AUDIENCE`

Optional repository variables:

- `AZURE_RESOURCE_GROUP` (default: `rg-uk-market-ai-trader`)
- `AZURE_LOCATION` (default: `uksouth`)

The GitHub deployment identity needs sufficient rights on the resource group to deploy resources and RBAC assignments. A practical scoped setup is **Contributor + Role Based Access Control Administrator on this resource group only**.

## Microsoft Entra API registration

The protected endpoints expect an Entra access token.

Create an app registration for this API and expose an API scope, for example:

`api://<application-client-id>/access_as_user`

Set `AZURE_API_AUDIENCE` to the token audience expected by the API (commonly `api://<application-client-id>` or the application client ID, depending on the registration/token configuration).

The health endpoint remains public:

`GET /health`

Protected endpoints:

`GET /me`

`GET /predict/{symbol}`

## Deploy

After OIDC and repository variables are configured, run the **Deploy Azure serverless** workflow manually from GitHub Actions, or push to `main`.

The workflow:

1. logs into Azure with OIDC
2. creates/updates the resource group
3. deploys base infrastructure
4. remotely builds the image in ACR
5. deploys/updates the Container App
6. prints the HTTPS URL
7. calls `/health`

## Cost behaviour

Container Apps is configured with `minReplicas: 0`, so compute can scale to zero. ACR, Log Analytics, Key Vault and Storage may still have small standing/usage costs. Prediction requests after idle periods can experience a cold start.
