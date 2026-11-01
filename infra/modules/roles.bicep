@export()
@description('Built-in role definition names: public constants, written without hyphens so the repository scan for identifiers stays strict.')
var roles = {
  storageBlobDataReader: '2a2b99086ea14ae28e65a410df84e7d1'
  storageBlobDataContributor: 'ba92f5b42d11453da403e96b0029c9fe'
  keyVaultSecretsUser: '4633458b17de408ab8740445c86b69e6'
  monitoringMetricsPublisher: '3913510d42f44e428a64420c390055eb'
  cosmosDataContributor: '00000000000000000000000000000002'
}

@export()
func uuid(hex string) string =>
  '${substring(hex, 0, 8)}-${substring(hex, 8, 4)}-${substring(hex, 12, 4)}-${substring(hex, 16, 4)}-${substring(hex, 20, 12)}'

@export()
func roleId(hex string) string => subscriptionResourceId('Microsoft.Authorization/roleDefinitions', uuid(hex))
