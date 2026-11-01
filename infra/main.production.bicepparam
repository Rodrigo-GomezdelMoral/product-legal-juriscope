using 'main.bicep'

param env = 'production'
param minReplicas = 1
param maxReplicas = 4
param budget = 25
param fixedMonthlyEur = '15.6'
param dailyCapGb = '1'
param digest = readEnvironmentVariable('IMAGE_DIGEST')
param revisionSuffix = readEnvironmentVariable('REVISION_SUFFIX')
param stableRevision = readEnvironmentVariable('STABLE_REVISION', '')
param authClientId = readEnvironmentVariable('AUTH_CLIENT_ID')
param authClientSecret = readEnvironmentVariable('AUTH_CLIENT_SECRET')
param alertEmail = readEnvironmentVariable('ALERT_EMAIL_ADDRESS')
param registryServer = readEnvironmentVariable('REGISTRY_LOGIN_SERVER')
param foundryProjectEndpoint = readEnvironmentVariable('FOUNDRY_PROJECT_ENDPOINT')
param foundryAccountEndpoint = readEnvironmentVariable('FOUNDRY_ACCOUNT_ENDPOINT')
param searchEndpoint = readEnvironmentVariable('SEARCH_ENDPOINT')
param chatModel = readEnvironmentVariable('CHAT_MODEL')
param embeddingModel = readEnvironmentVariable('EMBEDDING_MODEL')
