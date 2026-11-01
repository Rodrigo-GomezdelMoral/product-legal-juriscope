targetScope = 'resourceGroup'

@allowed(['staging', 'production'])
param env string
@description('Digest (sha256:...) of the image in the shared registry: images are promoted by digest, never rebuilt.')
param digest string
@description('Suffix of the revision this deployment creates.')
param revisionSuffix string
@description('Revision serving traffic before this deployment; empty on the first one.')
param stableRevision string = ''
@description('Client id of the product-legal-juriscope-<env> sign-in app.')
param authClientId string
@secure()
@description('Client secret of the sign-in app, stored in the Key Vault (ADR-006).')
param authClientSecret string
@secure()
@description('Address that receives the budget and alert e-mails.')
param alertEmail string
@minValue(0)
param minReplicas int
@maxValue(4)
param maxReplicas int
@description('Monthly budget of the resource group, in euros.')
param budget int
@description('Standing monthly cost of the environment in euros, for the workbook cost per question (docs/cost.md).')
param fixedMonthlyEur string
@description('Daily ingestion cap of Application Insights, in GB.')
param dailyCapGb string
param registryServer string
param foundryProjectEndpoint string
param foundryAccountEndpoint string
param searchEndpoint string
param chatModel string
param embeddingModel string
param location string = resourceGroup().location
@description('Region of the Container Apps environment and app only; everything else stays in the resource group region.')
param appLocation string = 'spaincentral'
@description('First month of the budget, fixed so that a redeployment never changes it.')
param budgetStartDate string = '2026-11-01'
param sharedResourceGroup string = 'rg-aiplatform-shared-swc'

var short = env == 'staging' ? 'stg' : 'prod'
var production = env == 'production'
var tags = { project: 'product-legal-juriscope', environment: env, owner: 'Rodrigo-GomezdelMoral' }
var shared = resourceGroup(sharedResourceGroup)

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' existing = { name: 'id-juriscope-${short}-swc' }
resource search 'Microsoft.Search/searchServices@2025-05-01' existing = { name: 'srch-aiplatform-shared', scope: shared }
resource workspace 'Microsoft.OperationalInsights/workspaces@2026-03-01' existing = { name: 'log-aiplatform-shared-swc', scope: shared }

module data 'modules/data.bicep' = {
  params: {
    location: location, tags: tags, short: short, principalId: identity.properties.principalId, searchPrincipalId: search.identity.principalId
    authClientSecret: authClientSecret
  }
}

module monitor 'modules/monitor.bicep' = {
  params: {
    location: location, tags: tags, short: short, production: production, workspaceId: workspace.id, principalId: identity.properties.principalId
    budget: budget, budgetStartDate: budgetStartDate, alertEmail: alertEmail, fixedMonthlyEur: fixedMonthlyEur, dailyCapGb: dailyCapGb
  }
}

module app 'modules/app.bicep' = {
  params: {
    location: appLocation, tags: tags, short: short, production: production, workspaceId: workspace.id, actionGroupId: monitor.outputs.actionGroupId
    image: '${registryServer}/product-legal-juriscope@${digest}', registryServer: registryServer, identityId: identity.id
    revisionSuffix: revisionSuffix, stableRevision: stableRevision, minReplicas: minReplicas, maxReplicas: maxReplicas
    authClientId: authClientId, authSecretUri: data.outputs.authSecretUri
    settings: {
      AZURE_CLIENT_ID: identity.properties.clientId
      FOUNDRY_PROJECT_ENDPOINT: foundryProjectEndpoint
      FOUNDRY_ACCOUNT_ENDPOINT: foundryAccountEndpoint
      SEARCH_ENDPOINT: searchEndpoint
      SEARCH_INDEX: 'jur-articles-${short}'
      CHAT_MODEL: chatModel
      EMBEDDING_MODEL: embeddingModel
      COSMOS_ENDPOINT: data.outputs.cosmosEndpoint
      APPLICATIONINSIGHTS_CONNECTION_STRING: monitor.outputs.connectionString
    }
  }
}

output revision string = app.outputs.revision
output fqdn string = app.outputs.fqdn
output corpusAccountUrl string = data.outputs.blobEndpoint
output storageId string = data.outputs.storageId
