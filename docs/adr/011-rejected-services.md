# ADR-011 · Services and patterns deliberately left out

**Status:** accepted · **Date:** 2026-11-01

One firm, one tenant, 18 seats and about 350 questions a month, on a 25 € production budget. Each item below would add cost, code or
operations without serving a requirement in `docs/PRODUCT.md`.

| Rejected | Why | What covers the need instead |
|---|---|---|
| Front Door | one region, no global users, no WAF requirement; a monthly base fee on a 25 € budget | Container Apps HTTPS ingress, TLS 1.2 |
| API Management | one client (the web app), no API product to publish | Easy Auth, the role check, max replicas, TPM caps on the shared deployments |
| Feature flags (App Configuration) | changes ship through the evaluation gate and a canary | `eval.yml`, the 10 % canary of `release.yml`, rollback by digest |
| Managed Grafana | the KPIs and SLOs fit one workbook | Azure Monitor workbook in Bicep |
| Azure Load Testing | Locust runs from the GitHub runner for free | `load-test.yml` |
| Private endpoints and VNet integration | they would need a VNet, private DNS and a dedicated environment profile for one product; the services already require Entra ID and refuse keys | managed identities, `disableLocalAuth`, no shared keys, HTTPS only |
| Zone redundancy, multi-region | the SLA is 99.5 % and the shared search has one replica; a second region doubles cost | measured availability, Bicep and backups for a cold rebuild (RTO 4 h) |
| Defender for Cloud plans | per-resource monthly cost on a 25 € budget | secret scanning, push protection, CodeQL, Dependabot, pinned dependencies |
| AG-UI (`agent-framework-ag-ui`) | caps `fastapi<0.142` | FastAPI's own SSE (guide 8.1.1) |
| `agent-framework-hosting` | alpha | plain FastAPI on Container Apps |
| Agents or workflows defined in Foundry | the workflow branches in code and must pass the gate as code | `app/workflow.py`, self-hosted (guide Part 8.1) |
| Development environments in Azure, separate subscriptions | local development uses the emulator and the shared models; one subscription with a resource group per environment segments access | `rg-juriscope-stg-swc`, `rg-juriscope-prod-swc`, separate identities |
| Certifications (ISO, ENS) | out of scope for a portfolio product | the threat model and the RAI assessment |
