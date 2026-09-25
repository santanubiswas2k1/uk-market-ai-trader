#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NAME="${DISPLAY_NAME:-uk-market-ai-trader-api}"

CLIENT_ID=$(az ad app create \
  --display-name "$DISPLAY_NAME" \
  --sign-in-audience AzureADMyOrg \
  --query appId -o tsv)

OBJECT_ID=$(az ad app show --id "$CLIENT_ID" --query id -o tsv)
SCOPE_ID=$(python - <<'PY'
import uuid
print(uuid.uuid4())
PY
)

BODY=$(cat <<EOF
{
  "identifierUris": ["api://$CLIENT_ID"],
  "api": {
    "oauth2PermissionScopes": [
      {
        "adminConsentDescription": "Access the UK Market AI Trader API",
        "adminConsentDisplayName": "Access UK Market AI Trader",
        "id": "$SCOPE_ID",
        "isEnabled": true,
        "type": "User",
        "userConsentDescription": "Access the UK Market AI Trader API",
        "userConsentDisplayName": "Access UK Market AI Trader",
        "value": "access_as_user"
      }
    ]
  }
}
EOF
)

az rest \
  --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/$OBJECT_ID" \
  --headers "Content-Type=application/json" \
  --body "$BODY" \
  --output none

cat <<EOF

Microsoft Entra API registration created.

Application (client) ID: $CLIENT_ID
API audience:             api://$CLIENT_ID
Delegated scope:          api://$CLIENT_ID/access_as_user

Set this GitHub repository variable:
AZURE_API_AUDIENCE=api://$CLIENT_ID
EOF
