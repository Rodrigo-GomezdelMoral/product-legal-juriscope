param location string
param tags object
param short string
param production bool
param image string
param registryServer string
param identityId string
param revisionSuffix string
@description('Revision that keeps all traffic while the new one starts at 0 % behind the canary label; empty on the first deployment.')
param stableRevision string
param minReplicas int
param maxReplicas int
param authClientId string
@description('Key Vault URI of the sign-in client secret, read with the runtime identity (ADR-006).')
param authSecretUri string
param workspaceId string
param actionGroupId string
@description('Environment variables of the container.')
param settings object

var regionCodes = { swedencentral: 'swc', spaincentral: 'spc' }
var name = 'ca-juriscope-${short}-${regionCodes[location]}'
var canary = { revisionName: '${name}--${revisionSuffix}', weight: empty(stableRevision) ? 100 : 0, label: 'canary' }
var issuer = '${az.environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-07-01' = {
  name: 'cae-juriscope-${short}-${regionCodes[location]}'
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

resource app 'Microsoft.App/containerApps@2026-07-01' = {
  name: name
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identityId}': {} } }
  properties: {
    environmentId: managedEnvironment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Multiple'
      maxInactiveRevisions: 5
      ingress: {
        external: true, targetPort: 8000, transport: 'auto', allowInsecure: false
        traffic: empty(stableRevision) ? [canary] : [{ revisionName: stableRevision, weight: 100 }, canary]
      }
      registries: [{ server: registryServer, identity: identityId }]
      secrets: [{ name: 'auth-client-secret', keyVaultUrl: authSecretUri, identity: identityId }]
    }
    template: {
      revisionSuffix: revisionSuffix
      containers: [
        {
          name: 'juriscope'
          image: image
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [for item in items(settings): { name: item.key, value: item.value }]
          probes: [
            { type: 'Startup', httpGet: { path: '/healthz', port: 8000 }, periodSeconds: 5, failureThreshold: 24 }
            { type: 'Readiness', httpGet: { path: '/healthz', port: 8000 }, periodSeconds: 10, failureThreshold: 3 }
            { type: 'Liveness', tcpSocket: { port: 8000 }, periodSeconds: 10, failureThreshold: 3 }
          ]
        }
      ]
      scale: { minReplicas: minReplicas, maxReplicas: maxReplicas, rules: [{ name: 'http', http: { metadata: { concurrentRequests: '10' } } }] }
    }
  }
}

resource auth 'Microsoft.App/containerApps/authConfigs@2026-07-01' = {
  parent: app
  name: 'current'
  properties: {
    platform: { enabled: true }
    globalValidation: { unauthenticatedClientAction: 'AllowAnonymous' }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: { clientId: authClientId, clientSecretSettingName: 'auth-client-secret', openIdIssuer: issuer }
        validation: { allowedAudiences: ['api://${authClientId}', authClientId] }
      }
    }
    httpSettings: { requireHttps: true }
  }
}

resource serverErrors 'Microsoft.Insights/metricAlerts@2026-01-01' = {
  name: 'alert-juriscope-${short}-5xx'
  location: 'global'
  tags: tags
  properties: {
    description: 'Server errors on the app in the last 15 minutes', severity: 2, enabled: production, scopes: [app.id]
    evaluationFrequency: 'PT5M', windowSize: 'PT15M', autoMitigate: true, actions: [{ actionGroupId: actionGroupId }]
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion', name: 'server-errors', metricNamespace: 'Microsoft.App/containerApps', metricName: 'Requests'
          dimensions: [{ name: 'statusCodeCategory', operator: 'Include', values: ['5xx'] }], operator: 'GreaterThan', threshold: 5, timeAggregation: 'Total'
        }
      ]
    }
  }
}

output revision string = canary.revisionName
output fqdn string = app.properties.configuration.ingress.fqdn
