#!/usr/bin/env bash
set -euo pipefail

CLIENT_ID="${CLIENT_ID:-0bf0ae72-693b-4923-a7ac-6f01252ea7bd}"
GITHUB_REPO="${GITHUB_REPO:-santanubiswas2k1/uk-market-ai-trader}"

OWNER="${GITHUB_REPO%%/*}"
REPO="${GITHUB_REPO##*/}"
REPO_JSON=$(curl -fsSL "https://api.github.com/repos/$GITHUB_REPO")
OWNER_ID=$(printf '%s' "$REPO_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["owner"]["id"])')
REPO_ID=$(printf '%s' "$REPO_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')
FEDERATED_SUBJECT="repo:${OWNER}@${OWNER_ID}/${REPO}@${REPO_ID}:ref:refs/heads/main"

APP_OBJECT_ID=$(az ad app show --id "$CLIENT_ID" --query id -o tsv)

EXISTING_ID=$(az ad app federated-credential list --id "$APP_OBJECT_ID" \
  --query "[?name=='github-main'].id | [0]" -o tsv)

if [ -n "$EXISTING_ID" ]; then
  az rest --method DELETE \
    --uri "https://graph.microsoft.com/v1.0/applications/$APP_OBJECT_ID/federatedIdentityCredentials/$EXISTING_ID"
fi

cat >/tmp/github-federated-credential.json <<EOF
{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "$FEDERATED_SUBJECT",
  "description": "GitHub Actions main branch",
  "audiences": ["api://AzureADTokenExchange"]
}
EOF

az ad app federated-credential create \
  --id "$APP_OBJECT_ID" \
  --parameters /tmp/github-federated-credential.json \
  --output none

echo "Federated credential repaired."
echo "Subject: $FEDERATED_SUBJECT"
