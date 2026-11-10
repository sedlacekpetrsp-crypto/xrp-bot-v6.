# XRP radar CI: confirmed failure root cause (2026-11-10)

Status: [P] read-only inspection of raw GitHub Actions job log; [S] historical CI run 42803745418 (failed), no tests initiated by this diagnosis.

## Evidence

- Workflow run: https://github.com/sedlacekpetrsp-crypto/xrp-bot-v6./actions/runs/42803745418
- Job ID: 129787576778, branch `research/xrp-top-risk-radar-v1-20261108`, SHA `3cf1156742127a7ab21467199e3d6ea70c4f3723`.
- Command: `python -m pytest -q research/top_risk_radar_v1 research/early_growth_radar_v1`.
- Exact result: **2 failed, 289 passed in 0.36s**.
- Both failures: `research/top_risk_radar_v1/test_pit_metarmorphic_qa.py::test_future_and_unpublished_rows_cannot_change_known_prevalence`, parametrizations `growth-30` and `downside-14`.
- Exception from `research/top_risk_radar_v1/pit_prevalence.py:71`: `ValueError: negative label available before horizon maturity`.

## Root cause assessment

The synthetic fixture `future_decision` uses `decision_at=CUTOFF+1 day`, `label_available_at=CUTOFF+2 days`, and `False` event label. This is **invalid**: a negative event label cannot be finalized before the full 30-day growth / 14-day downside horizon. The production validator correctly fails closed, including on rows that would otherwise be excluded by the cutoff. The test incorrectly assumes the invalid row should be silently ignored.

## Safe repair proposal for Claude (not implemented here)

1. Correct the fixture so its `False` label is available no earlier than `decision_at + timedelta(days=horizon)`; it remains excluded because `decision_at > CUTOFF`. This preserves the intended metamorphic invariant without disabling validation.
2. Add a separate explicit regression asserting that an early negative label raises `ValueError` even when the decision is after cutoff. Do not relax `pit_prevalence.py` fail-closed behavior.
3. Run deterministic unit tests on an isolated `claude/*` branch and capture exact pass/fail counts, SHA and Actions run. No performance backtest, merge or deployment.

## Scope

This diagnosis refers to the verified failing run above, not necessarily the current branch HEAD. Recheck the current HEAD and latest CI before implementing. Green unit tests would not establish predictive OOS accuracy.
