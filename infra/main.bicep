param location string = resourceGroup().location
param prefix string = 'ukmai'
param apiAudience string = ''

var suffix = uniqueString(resourceGroup().id)
var acrPullRoleDefinitionId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var keyVaultSecretsUserRoleDefinitionId = '4633458b-17de-408a-b874-0445c86b69e6'
var storageBlobDataContributorRoleDefinitionId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: toLower('${prefix}st${suffix}')
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${prefix}-law-${suffix}'
  location: location
  properties: {
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-appi-${suffix}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: toLower('${prefix}-kv-${suffix}')
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-identity-${suffix}'
  location: location
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: toLower('${prefix}acr${suffix}')
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${prefix}-cae-${suffix}'
  location: location
  properties: {}
}

resource frontendStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: toLower('${prefix}web${suffix}')
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}


resource functionStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: toLower('${prefix}fnst${suffix}')
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource functionPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${prefix}-feed-plan-${suffix}'
  location: location
  kind: 'linux'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

var functionStorageKey = functionStorage.listKeys().keys[0].value
var functionStorageConnection = 'DefaultEndpointsProtocol=https;AccountName=${functionStorage.name};AccountKey=${functionStorageKey};EndpointSuffix=${az.environment().suffixes.storage}'

resource marketFeedFunction 'Microsoft.Web/sites@2023-12-01' = {
  name: '${prefix}-market-feed-${suffix}'
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  properties: {
    serverFarmId: functionPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: functionStorageConnection
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'AZURE_TENANT_ID'
          value: subscription().tenantId
        }
        {
          name: 'AZURE_CLIENT_ID'
          value: identity.properties.clientId
        }
        {
          name: 'KEY_VAULT_URL'
          value: keyVault.properties.vaultUri
        }
        {
          name: 'API_AUDIENCE'
          value: apiAudience
        }
        {
          name: 'FRONTEND_ORIGIN'
          value: frontendStorage.properties.primaryEndpoints.web
        }
      ]
    }
  }
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, identity.id, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleDefinitionId
    )
  }
}

resource storageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, storageBlobDataContributorRoleDefinitionId)
  scope: storage
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      storageBlobDataContributorRoleDefinitionId
    )
  }
}

resource keyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, identity.id, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      keyVaultSecretsUserRoleDefinitionId
    )
  }
}

output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output environmentName string = environment.name
output identityName string = identity.name
output identityClientId string = identity.properties.clientId
output keyVaultName string = keyVault.name
output keyVaultUrl string = keyVault.properties.vaultUri
output storageAccountName string = storage.name
output storageAccountUrl string = storage.properties.primaryEndpoints.blob
output applicationInsightsName string = appInsights.name
output frontendStorageName string = frontendStorage.name
output frontendUrl string = frontendStorage.properties.primaryEndpoints.web

output marketFeedFunctionName string = marketFeedFunction.name
output marketFeedUrl string = 'https://${marketFeedFunction.properties.defaultHostName}/api'
