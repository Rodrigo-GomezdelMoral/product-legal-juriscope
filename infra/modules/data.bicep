import { roles, roleId, uuid } from 'roles.bicep'

param location string
param tags object
param short string
@description('Principal id of the runtime identity, id-juriscope-<env>-swc.')
param principalId string
@description('Principal id of the shared search service, whose indexer reads the corpus.')
param searchPrincipalId string
@secure()
param authClientSecret string

var ninetyDays = 7776000
var partitions = { history: '/session_id', conversations: '/user_id' }

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2026-03-15' = {
  name: 'cosmos-juriscope-${short}-swc'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard', capabilities: [{ name: 'EnableServerless' }], consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    locations: [{ locationName: location, failoverPriority: 0, isZoneRedundant: false }]
    backupPolicy: { type: 'Continuous', continuousModeProperties: { tier: 'Continuous7Days' } }
    disableLocalAuth: true, disableKeyBasedMetadataWriteAccess: true, minimalTlsVersion: 'Tls12'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2026-03-15' = {
  parent: cosmos
  name: 'juriscope'
  properties: { resource: { id: 'juriscope' } }
}

resource containers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2026-03-15' = [
  for item in items(partitions): {
    parent: database
    name: item.key
    properties: { resource: { id: item.key, partitionKey: { paths: [item.value], kind: 'Hash' }, defaultTtl: ninetyDays } }
  }
]

resource cosmosAccess 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2026-03-15' = {
  parent: cosmos
  name: guid(cosmos.id, principalId, roles.cosmosDataContributor)
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${uuid(roles.cosmosDataContributor)}', principalId: principalId, scope: '${cosmos.id}/dbs/${database.name}'
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2026-06-01' = {
  name: 'stjuriscope${short}swc'
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    accessTier: 'Hot', allowBlobPublicAccess: false, allowSharedKeyAccess: false, defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2', supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2026-06-01' = {
  parent: storage
  name: 'default'
  properties: { deleteRetentionPolicy: { enabled: true, days: 7 } }
}

resource corpus 'Microsoft.Storage/storageAccounts/blobServices/containers@2026-06-01' = {
  parent: blobService
  name: 'corpus'
  properties: { publicAccess: 'None' }
}

resource corpusAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for grant in [
    { principalId: searchPrincipalId, role: roles.storageBlobDataReader, type: 'ServicePrincipal' }
    { principalId: deployer().objectId, role: roles.storageBlobDataContributor, type: null }
  ]: {
    name: guid(corpus.id, grant.principalId, grant.role)
    scope: corpus
    properties: { roleDefinitionId: roleId(grant.role), principalId: grant.principalId, principalType: grant.type }
  }
]

resource vault 'Microsoft.KeyVault/vaults@2026-02-01' = {
  name: 'kv-juriscope-${short}-swc'
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId, sku: { family: 'A', name: 'standard' }, enableRbacAuthorization: true
    enableSoftDelete: true, softDeleteRetentionInDays: 7, publicNetworkAccess: 'Enabled'
  }
}

resource authSecret 'Microsoft.KeyVault/vaults/secrets@2026-02-01' = {
  parent: vault
  name: 'auth-client-secret'
  properties: { value: authClientSecret, contentType: 'Client secret of the sign-in app' }
}

resource vaultAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, principalId, roles.keyVaultSecretsUser)
  scope: vault
  properties: { roleDefinitionId: roleId(roles.keyVaultSecretsUser), principalId: principalId, principalType: 'ServicePrincipal' }
}

output cosmosEndpoint string = cosmos.properties.documentEndpoint
output blobEndpoint string = storage.properties.primaryEndpoints.blob
output storageId string = storage.id
output authSecretUri string = authSecret.properties.secretUri
