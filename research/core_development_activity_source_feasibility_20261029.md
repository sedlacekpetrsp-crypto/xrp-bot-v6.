# XRP_CORE_DEVELOPMENT_ACTIVITY_V1 — source feasibility (2026-10-29)

Performance was not evaluated before this record.

The official GitHub Search Issues API was exhaustively paginated using non-overlapping merged-date partitions. Calendar years were used for 2020–2025; 2026 was split into calendar months because its annual result exceeds GitHub Search's 1,000-result ceiling. Every partition is below 1,000 and every returned page count exactly matches the API's reported `total_count`.

Merged PR counts:

- 2020: 38; 2021: 23; 2022: 35; 2023: 222; 2024: 166; 2025: 609.
- 2026 January–September: 112, 82, 165, 125, 127, 145, 168, 138, 107.
- Total: 2,262 unique PR numbers, coverage from `2020-01-02T07:08:15Z` through `2026-09-30T20:43:16Z`.
- 36 additional events share a public merge second with a different PR and are retained under the separately committed ingestion amendment.
- 32 exact API response payloads total 15,510,003 bytes. The SHA256 of the sorted provisional manifest (including every query URL, page hash, bytes, rows and reported total) is `d28da86bc006a1976f6d671b0cfcaa690e4bf23ee78985d0125ff9f4f1444c34`.

A direct source probe and complete pagination used only `pull_request.merged_at` and PR number. No commit date, issue close time, comment, code-size estimate or market return was inspected. Exact per-page URLs and SHA256 fingerprints will be written to the final result manifest.

Feasibility conclusion: the source covers the frozen control and five OOS calendar periods with materially more than the minimum event density. Proceed without changing source, thresholds or gates. This conclusion says nothing about profitability.
