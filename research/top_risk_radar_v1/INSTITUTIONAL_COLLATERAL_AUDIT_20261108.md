# Institutional XRP ETF collateral — duplication and integration audit (2026-11-08)

Status: [P] repository audit and documentation; [S] no dataset extraction, performance run, alert or deployment. PAPER only.

## Existing coverage
- `research/top_risk_radar_v1/PROTOCOL.md`: Model B optionally includes ETF holdings/flows and public attention, with provable point-in-time publication.
- `research/top_risk_radar_v1/BASELINE_DATASET_SPEC.md`: comparator M5 already includes ETF and institutional signals; M0–M4 provide baselines.
- `research/top_risk_radar_v1/DUAL_RADAR_VALIDATION.md`: institutional feature-family ablation, identical timestamps, OOS evaluation, publication-delay checks.
- `research/early_growth_radar_v1/PROTOCOL.md`: protocol only, no validated predictor.
- Repo compare main...research/xrp-top-risk-radar-v1-20261108: 56 commits ahead; this is NOT evidence of model performance.

## SEC N-MFP3 / Schwab claim
Social-media claim: Oct 31 filings allegedly show Bitwise $14.46m and Canary $3.21m in XRP-linked collateral. These amounts have NOT been reconciled to primary SEC filing line items. Do not publish them as verified flows or Schwab spot XRP purchases. Collateral market value is distinct from ETF subscriptions, issuer-held XRP, beneficial ownership, and new spot demand.

## Required verification before inclusion
1. Identify exact SEC accession, fund series, report period, filing date, original N-MFP3 structured collateral table and row identifiers; verify issuer, CUSIP/ticker, amounts, units and possible duplicate rows.
2. Record repo counterparties and transaction type, distinguish pledged collateral from direct positions and whether collateral is reused/reported more than once.
3. Capture event date, public filing timestamp, ingestion timestamp, corrections, original source URL and checksum; point-in-time availability gate must fail closed.
4. Monthly frequency, short sample and missing-history limitations: do NOT backfill publication time to report date; quantify sparse coverage and regime confounding.
5. Only then assess as optional institutional collateral feature within existing M5; compare M4 vs M5 on identical eligible dates with ablation, block uncertainty, false-positive cost and untouched chronological holdout. No new third radar.
6. Check existing source manifests and code before writing collectors; avoid repeating previously rejected ideas/tests.

## Decision
No new feature implementation or performance claim yet. Prioritize SEC primary-source verification and provenance audit; seek independent Claude review via established dialog before changing research scope. No Render, LIVE, production merge or force push.

## Owner decisions
None required for this documentation-only audit. Any performance run must satisfy existing OWNER_DECISIONS approvals and all data gates.
