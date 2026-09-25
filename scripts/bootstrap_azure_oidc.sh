#!/usr/bin/env bash
set -euo pipefail

GITHUB_REPO="${GITHUB_REPO:-santanubiswas2k1/uk-market-ai-trader}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-uk-market-ai-trader}"
LOCATION="${LOCATION:-uksouth}"
APP_NAME="${APP_NAME:-uk-market-ai-trader-github}"

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "Using subscription: $SUBSCRIPTION_ID"
echo "Using tenant:       $TENANT_ID"

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

CLIENT_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
APP_OBJECT_ID=$(az ad app show --id "$CLIENT_ID" --query id -o tsv)
SP_OBJECT_ID=$(az ad sp create --id "$CLIENT_ID" --query id -o tsv)

cat >/tmp/github-federated-credential.json <<EOF
{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:$GITHUB_REPO:ref:refs/heads/main",
  "description": "GitHub Actions main branch",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF

az ad app federated-credential create \
  --id "$APP_OBJECT_ID" \
  --parameters /tmp/github-federated-credential.json \
  --output none

RG_SCOPE=$(az group show --name "$RESOURCE_GROUP" --query id -o tsv)

az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role Contributor \
  --scope "$RG_SCOPE" \
  --output none

az role assignment create \
  --assignee-object-id "$SP_OBJECT_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "User Access Administrator" \
  --scope "$RG_SCOPE" \
  --output none

cat <<EOF

GitHub OIDC identity created.

Add these as GitHub repository VARIABLES:
AZURE_CLIENT_ID=$CLIENT_ID
AZURE_TENANT_ID=$TENANT_ID
AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP
AZURE_LOCATION=$LOCATION

You must also add:
AZURE_API_AUDIENCE=<your Microsoft Entra API audience>

No Azure client secret was created.
EOF
