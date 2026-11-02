metadata description = 'Container Apps environment shared by ca-juriscope-stg and ca-juriscope-prod (ADR-014). Production declares it; 08-environment.sh creates it first from this file.'
param location string
param tags object
param workspaceId string

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-07-01' = {
  name: 'cae-juriscope-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: { destination: 'azure-monitor' }, workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }], zoneRedundant: false
  }
}

#disable-next-line use-recent-api-versions
resource logs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'to-shared-workspace'
  scope: managedEnvironment
  properties: { workspaceId: workspaceId, logs: [{ categoryGroup: 'allLogs', enabled: true }] }
}
