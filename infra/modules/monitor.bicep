import { roles, roleId } from 'roles.bicep'

param location string
param tags object
param short string
@description('Alert rules exist in both environments and are enabled in production only: an enabled log alert rule bills.')
param production bool
param workspaceId string
param principalId string
param budget int
param budgetStartDate string
@secure()
param alertEmail string
param fixedMonthlyEur string
param dailyCapGb string

var events = 'customEvents | extend turn = tostring(customDimensions.turn_id)'
var api = 'requests | where name has "/api/"'
var businessHours = 'extend local = datetime_utc_to_local(timestamp, "Europe/Madrid") | where dayofweek(local) between (1d .. 5d) and hourofday(local) between (8 .. 20)'
var availability = 'summarize total = count(), failed = countif(toint(resultCode) >= 500) | extend availability_pct = round(100.0 * (total - failed) / total, 3)'
var ask = 'requests | where name has "/messages" and toint(resultCode) < 500 | summarize asks = count(), p95_s = round(percentile(duration, 95) / 1000, 2)'
var flows = 'extend flow = case(itemType == "dependency", "Model", name has "/messages", "Ask", "History")'
var tiles = [
  {
    title: 'K1 Time to accepted answer: median minutes (target 10)'
    query: '${events} | where name == "QuestionAsked" | project turn, asked = timestamp | join kind=inner (${events} | where name == "AnswerAccepted" | summarize accepted = min(timestamp) by turn) on turn | summarize turns = count(), median_min = round(percentile((accepted - asked) / 1m, 50), 1) | extend target = 10, met = iff(median_min <= 10, "✓", "✗")'
  }
  {
    title: 'K2 Grounded first draft: % of answered turns with no claim removed (target 95)'
    query: '${events} | where name == "AnswerDelivered" and customDimensions.outcome == "answer" | summarize answered = count(), grounded_pct = round(100.0 * countif(toint(customDimensions.dropped_claims) == 0) / count(), 1) | extend target = 95, met = iff(grounded_pct >= 95, "✓", "✗")'
  }
  {
    title: 'K3 Helpful answers: % of up votes among up and down votes (target 80)'
    query: '${events} | where name == "FeedbackGiven" and customDimensions.value in ("up", "down") | summarize votes = count(), helpful_pct = round(100.0 * countif(customDimensions.value == "up") / count(), 1) | extend target = 80, met = iff(helpful_pct >= 80, "✓", "✗")'
  }
  {
    title: 'K4 Weekly active seats: % of {Seats} seats asking in the ISO week (target 70)'
    query: '${events} | where name == "QuestionAsked" | summarize seats = dcount(tostring(customDimensions.user_hash)) by week = startofweek(timestamp, 1) | extend active_pct = round(100.0 * seats / {Seats}, 1), target = 70, met = iff(active_pct >= 70, "✓", "✗") | order by week desc'
  }
  {
    title: 'Availability, around the clock: % of /api requests without 5xx (SLO 99.7, SLA 99.5)'
    query: '${api} | ${availability} | extend slo = 99.7, sla = 99.5, met = iff(availability_pct >= 99.7, "✓", "✗")'
  }
  { title: 'Availability, business hours (SLO 99.7)', query: '${api} | ${businessHours} | ${availability} | extend slo = 99.7, met = iff(availability_pct >= 99.7, "✓", "✗")' }
  { title: 'Latency: p95 seconds of the ask route to the final event (SLO 6, SLA 8)', query: '${ask} | extend slo = 6, sla = 8, met = iff(p95_s < 6, "✓", "✗")' }
  {
    title: 'Errors: % of /api requests with 5xx (SLO 1)'
    query: '${api} | summarize total = count(), error_pct = round(100.0 * countif(toint(resultCode) >= 500) / count(), 2) | extend slo = 1, met = iff(error_pct < 1, "✓", "✗")'
  }
  {
    title: 'Health model, last hour: Ask, History and Model'
    query: 'union (${api}), (dependencies | where target has "services.ai" or name startswith "chat ") | where timestamp > ago(1h) | ${flows} | summarize total = count(), failed_pct = round(100.0 * countif(itemType == "dependency" and success == false or toint(resultCode) >= 500) / count(), 2), p95_s = round(percentile(duration, 95) / 1000, 2) by flow | extend state = case(failed_pct >= 50, "down", failed_pct >= 1 or (flow == "Ask" and p95_s >= 6), "degraded", "healthy")'
  }
  {
    title: 'Cost per question, last 30 days: tokens and semantic queries plus ${fixedMonthlyEur} € standing (SLO 0.05 € in production)'
    query: '${events} | where name == "AnswerDelivered" and timestamp > ago(30d) | summarize questions = count(), variable_eur = round(sum(todouble(customDimensions.cost_eur)), 4) | extend all_in_eur = round((variable_eur + ${fixedMonthlyEur}) / questions, 4), slo = 0.05'
  }
  { title: 'KPI events arriving, last 24 hours', query: 'customEvents | where timestamp > ago(1d) | summarize events = count() by name' }
]
var seats = { type: 9, name: 'parameters', content: { version: 'KqlParameterItem/1.0', parameters: [{ name: 'Seats', type: 1, value: '18', isRequired: true }] } }
var items = [
  for (tile, i) in tiles: {
    type: 3, name: 'tile-${i}'
    content: { version: 'KqlItem/1.0', title: tile.title, query: tile.query, size: 4, queryType: 0, resourceType: 'microsoft.insights/components', timeContext: { durationMs: 2592000000 } }
  }
]
var alerts = [
  { name: 'availability', description: 'Availability of /api below the 99.7 % SLO over the last hour', query: '${api} | ${availability} | where total >= 20 and availability_pct < 99.7' }
  { name: 'latency', description: 'p95 of the ask route at or above the 6 s SLO over the last hour', query: '${ask} | where asks >= 5 and p95_s >= 6' }
]

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-juriscope-${short}-swc'
  location: location
  tags: tags
  kind: 'web'
  properties: { Application_Type: 'web', WorkspaceResourceId: workspaceId, DisableLocalAuth: true, IngestionMode: 'LogAnalytics' }
}

#disable-next-line use-recent-api-versions
resource cap 'Microsoft.Insights/components/pricingPlans@2017-10-01' = {
  parent: insights
  name: 'current'
  properties: { planType: 'Basic', cap: json(dailyCapGb), warningThreshold: 90, stopSendNotificationWhenHitCap: false }
}

resource publisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, principalId, roles.monitoringMetricsPublisher)
  scope: insights
  properties: { roleDefinitionId: roleId(roles.monitoringMetricsPublisher), principalId: principalId, principalType: 'ServicePrincipal' }
}

resource workbook 'Microsoft.Insights/workbooks@2023-06-01' = {
  name: guid(insights.id, 'kpi-workbook')
  location: location
  tags: tags
  kind: 'shared'
  properties: {
    displayName: 'Juriscope KPIs, SLOs and health (${short})', category: 'workbook', sourceId: insights.id
    serializedData: string({ version: 'Notebook/1.0', items: concat([seats], items), fallbackResourceIds: [insights.id] })
  }
}

resource costBudget 'Microsoft.Consumption/budgets@2026-06-01' = {
  name: 'budget-juriscope-${short}'
  properties: {
    category: 'Cost', amount: budget, timeGrain: 'Monthly', timePeriod: { startDate: budgetStartDate }
    notifications: toObject([50, 80, 100], level => 'actual-${level}', level => {
      enabled: true, operator: 'GreaterThanOrEqualTo', threshold: level, thresholdType: 'Actual', contactEmails: [alertEmail]
    })
  }
}

resource group 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'ag-juriscope-${short}-swc'
  location: 'global'
  tags: tags
  properties: { groupShortName: 'juriscope', enabled: true, emailReceivers: [{ name: 'author', emailAddress: alertEmail, useCommonAlertSchema: true }] }
}

resource logAlerts 'Microsoft.Insights/scheduledQueryRules@2026-03-01' = [
  for alert in alerts: {
    name: 'alert-juriscope-${short}-${alert.name}'
    location: location
    tags: tags
    properties: {
      description: alert.description, severity: 2, enabled: production, scopes: [insights.id], evaluationFrequency: 'PT15M', windowSize: 'PT1H', autoMitigate: true
      criteria: {
        allOf: [
          { query: alert.query, timeAggregation: 'Count', operator: 'GreaterThan', threshold: 0, failingPeriods: { numberOfEvaluationPeriods: 1, minFailingPeriodsToAlert: 1 } }
        ]
      }
      actions: { actionGroups: [group.id] }
    }
  }
]

output connectionString string = insights.properties.ConnectionString
output actionGroupId string = group.id
