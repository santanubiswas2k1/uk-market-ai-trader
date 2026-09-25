#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-uk-market-ai-trader}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-serverless-base}"
API_CLIENT_ID="${API_CLIENT_ID:-0e9834ae-b88e-47de-bfad-3aa958feea49}"

FRONTEND_URL=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$DEPLOYMENT_NAME" \
  --query properties.outputs.frontendUrl.value \
  -o tsv)

if [ -z "$FRONTEND_URL" ]; then
  echo "Could not read frontend URL from deployment outputs."
  exit 1
fi

FRONTEND_ORIGIN="${FRONTEND_URL%/}"
APP_OBJECT_ID=$(az ad app show --id "$API_CLIENT_ID" --query id -o tsv)

BODY=$(cat <<EOF
{
  "spa": {
    "redirectUris": [
      "$FRONTEND_ORIGIN"
    ]
  }
}
EOF
)

az rest \
  --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$APP_OBJECT_ID" \
  --headers "Content-Type=application/json" \
  --body "$BODY" \
  --output none

cat <<EOF

Frontend authentication configured.

SPA client ID: $API_CLIENT_ID
Redirect URI:  $FRONTEND_ORIGIN
API scope:     api://$API_CLIENT_ID/access_as_user

Now rerun the GitHub workflow:
Actions -> Deploy Azure serverless -> Run workflow
EOF
