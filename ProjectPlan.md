# WhatsPoppingABQ — Project Plan

## Key Links
- **Dashboard:** https://whatspoppingabq.streamlit.app/
- **Codebase:** https://github.com/LoamySand/whatspoppingABQ
- **Jira Board:** https://loamysand.atlassian.net/jira/software/projects/SCRUM/boards/1


## Goals
1. Review the entire codebase to identify improvements
2. Migrate to Docker, redeploy on a self-hosted Raspberry Pi behind nginx
3. Redesign the schema and analytics views per best practice
4. Redesign the dashboard per data-viz/analytics principles (evaluate leaving Streamlit)
5. Migrate Supabase (free tier) → self-hosted Postgres
6. Implement user/usage tracking
7. Implement centralized error and log monitoring (frontend + backend)
8. Implement CI/CD
9. Reconfigure environment variable / secrets handling per best practice

## Jira Structure
Epics **SCRUM-5** through **SCRUM-13**, each broken into Stories and Tasks (SCRUM-14 through SCRUM-54). Full backlog lives on the board — this doc just adds sequencing and the source-of-truth links/schema.

| Epic | Key |
|---|---|
| Codebase Audit & Technical Debt Cleanup | SCRUM-5 |
| Dockerization & Self-Hosted Deployment | SCRUM-6 |
| Database Schema Redesign & Analytics Views | SCRUM-7 |
| Dashboard Redesign & Visualization Overhaul | SCRUM-8 |
| Postgres Migration: Supabase → Self-Hosted | SCRUM-9 |
| User Analytics & Usage Tracking | SCRUM-10 |
| Centralized Logging & Error Monitoring | SCRUM-11 |
| CI/CD Pipeline | SCRUM-12 |
| Secrets & Environment Variable Management | SCRUM-13 |

## Sprint Plan (2-week sprints, dependency-ordered)

| Sprint | Focus | Issues |
|---|---|---|
| 1 – Lock the doors | Rotate keys now, before infra changes; audit codebase in parallel | SCRUM-19, 18, 20, 21, 14 |
| 2 – Clean house | Consolidate duplicate flows, add tests/lint before Dockerizing | SCRUM-15, 16, 17 |
| 3 – Containerize | Dockerfiles + compose stack | SCRUM-22, 23 |
| 4 – Go self-hosted | Deploy to Pi, nginx/TLS, resilience | SCRUM-24, 25, 26 |
| 5 – Postgres up | Stand up self-hosted PG, migrate data | SCRUM-27, 28, 29 |
| 6 – Postgres cutover | Backups, decommission Supabase | SCRUM-30, 31 |
| 7 – Schema rework | Normalize schema, migrations tool, indexing/partitioning | SCRUM-32, 33, 35, 36 |
| 8 – Analytics views | Rebuild reporting views | SCRUM-34 |
| 9 – Dashboard research | Audit + build-vs-buy spike + IA redesign | SCRUM-37, 38, 39 |
| 10 – Dashboard build | Implement new dashboard + responsive | SCRUM-40, 41 |
| 11 – Know your users | Usage metrics + self-hosted analytics | SCRUM-42, 43, 44 |
| 12 – Observability | Centralized logs + structured logging | SCRUM-45, 46 |
| 13 – Error visibility | Error monitoring + alerting + Grafana | SCRUM-47, 48, 49 |
| 14 – Ship it automatically | CI/CD pipeline + branch protection + secrets runbook | SCRUM-50, 51, 52, 53, 54 |

**Why this order:** secrets get locked down before Docker/Postgres touch anything; the Postgres migration lands on a stable containerized environment; schema and dashboard work build on the new DB; observability and CI close the loop last so they can monitor the finished system rather than a moving target.
