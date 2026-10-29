# XRP_CORE_DEVELOPMENT_ACTIVITY_V1 — ingestion amendment (2026-10-29)

Status: COMMITTED BEFORE ANY PERFORMANCE EVALUATION.

The complete official GitHub source revealed that two or more distinct pull requests can legitimately have the same public `pull_request.merged_at` second. The preregistration phrase “Reject conflicting duplicate PR numbers or merged timestamps” is clarified as follows:

- PR number is the event identity.
- Repeated pages/items with the same PR number are exact-deduplicated only when their `merged_at` agrees; conflicting timestamps for one PR are fatal.
- Distinct PR numbers sharing a `merged_at` timestamp are separate real merge events. Preserve and count every one.
- Event ordering is non-decreasing rather than strictly increasing. Calendar counts include multiplicity.

This is a source-ingestion correction, not a strategy change. Repository, fields, time windows, thresholds, execution, costs, folds and acceptance gates are unchanged. No returns or trade outcomes were calculated before this amendment.
