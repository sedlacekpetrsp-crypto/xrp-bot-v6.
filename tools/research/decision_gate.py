"""Společná rozhodovací brána výzkumných runnerů (kolo 9, Q1 + Q3). PAPER výzkum, bez obchodování.

Princip: ZAMÍTNUTO jen tehdy, existuje-li aspoň jeden prokazatelně platný důvod nezávislý na blokujících datových
závadách. Pokud zamítnutí závisí na vadných datech nebo nelze nezávislost prokázat ⇒ NEROZHODNUTO. KANDIDÁT jen bez
jakékoli blokující závady. Zasažené obchody ani dny se NEVYŘAZUJÍ a výkonnost se nepřepočítává (selection bias);
neexistuje žádný procentní práh závad.

Závady se předávají rozlišené podle období, varianty a robustního testu; závady v ladicím období kterékoli varianty
mění výběr varianty, a proto jsou globální.
"""

PERIODS = ("tuning", "validation", "final_test")

# Data, z nichž každé kritérium počítá (strategie zvolené varianty / benchmark), podle evaluate() obou runnerů.
CRITERIA_DATA = {
    "A1_sharpe_dd": {"strategy": ("validation",), "benchmark": ("validation",)},
    "A2_trades_ge_30": {"strategy": ("validation",), "benchmark": ()},
    "A3_x2_pf_profit": {"strategy": ("validation",), "benchmark": ()},
    "A4_wo_top3": {"strategy": ("validation",), "benchmark": ()},
    "A5_final_x2": {"strategy": ("final_test",), "benchmark": ("final_test",)},
    "B1_val_x2_profit_pf": {"strategy": ("validation",), "benchmark": ()},
    "B2_dd_le_0_6_bh": {"strategy": ("validation", "final_test"), "benchmark": ("validation", "final_test")},
    "B3_final_x2_profit": {"strategy": ("final_test",), "benchmark": ()},
    "B4_val_wo_top3": {"strategy": ("validation",), "benchmark": ()},
    "B5_trades_ge_20": {"strategy": ("validation", "final_test"), "benchmark": ()},
    "B6_tuning_x1_profit": {"strategy": ("tuning",), "benchmark": ()},
}
ROBUSTNESS_CHECKS = ("dsr_ge_0_95", "neighbors_val_x2_profit", "walk_forward_ge_3_of_4")
# Kolo 10: stopa B dočasně NESMÍ sama udělit KANDIDÁTA (reprodukce R9-7: projde se 4 obchody ve validaci).
# Zamítnutí přes stopu B zůstává platné (selhání na čistých datech je důkaz proti, ne pro).
TRACK_B_CAN_GRANT_CANDIDATE = False
WF_NEEDED = 3


def _dep(c):
    d = CRITERIA_DATA.get(c)
    return (set(PERIODS), set(PERIODS)) if d is None else (set(d["strategy"]), set(d["benchmark"]))


def criterion_status(c, ok, strat_bad, bench_bad):
    s_dep, b_dep = _dep(c)
    tainted = bool(s_dep & set(strat_bad)) or bool(b_dep & set(bench_bad))
    if ok:
        return "pass_tainted" if tainted else "pass"
    return "fail_unknown" if tainted else "fail"


def track_status(track, strat_bad=(), bench_bad=()):
    """→ (stav, kritéria). fail = aspoň jedno porušené kritérium s čistými daty (platný důvod); unknown = porušená jsou
    jen kritéria na vadných datech; pass = všechna prošla (seznam těch, která prošla na vadných datech)."""
    st = {c: criterion_status(c, ok, strat_bad, bench_bad) for c, ok in track.items()}
    fails = sorted(c for c, s in st.items() if s == "fail")
    if fails:
        return "fail", fails
    unknown = sorted(c for c, s in st.items() if s == "fail_unknown")
    if unknown:
        return "unknown", unknown
    return "pass", sorted(c for c, s in st.items() if s == "pass_tainted")


def robustness_status(ctx):
    """ctx: dsr (float | None), dsr_defects {..}, neighbors {tag: (net, defects)}, wf {rok: (net, trades, defects)}.
    Vrací {test: pass | pass_tainted | fail | fail_unknown | unevaluable}. Fold bez obchodů je nehodnotitelný, ne neúspěšný."""
    out = {}
    dsr, dd = ctx.get("dsr"), ctx.get("dsr_defects") or {}
    if dsr is None:
        out["dsr_ge_0_95"] = "unevaluable"
    elif dsr >= 0.95:
        out["dsr_ge_0_95"] = "pass_tainted" if dd else "pass"
    else:
        out["dsr_ge_0_95"] = "fail_unknown" if dd else "fail"
    nb = ctx.get("neighbors") or {}
    failing = [t for t, (v, d) in nb.items() if not v > 0]
    if not failing:
        out["neighbors_val_x2_profit"] = "pass_tainted" if any(d for _, d in nb.values()) else "pass"
    else:
        out["neighbors_val_x2_profit"] = "fail" if any(not nb[t][1] for t in failing) else "fail_unknown"
    wf = ctx.get("wf") or {}
    pos_clean = [y for y, (v, n, d) in wf.items() if v > 0 and n > 0 and not d]
    pos_taint = [y for y, (v, n, d) in wf.items() if v > 0 and (n == 0 or d)]
    undecided = [y for y, (v, n, d) in wf.items() if not v > 0 and (n == 0 or d)]
    if len(pos_clean) >= WF_NEEDED:
        out["walk_forward_ge_3_of_4"] = "pass"
    elif len(pos_clean) + len(pos_taint) >= WF_NEEDED:
        out["walk_forward_ge_3_of_4"] = "pass_tainted"
    elif len(pos_clean) + len(pos_taint) + len(undecided) < WF_NEEDED:
        out["walk_forward_ge_3_of_4"] = "fail"  # ani všechny nehodnotitelné foldy by nestačily
    else:
        out["walk_forward_ge_3_of_4"] = "fail_unknown"
    return out


def decide(track_a, track_b, robust_ctx, strat_bad=(), bench_bad=(), global_defects=None, blocking=None,
           candidate_extra_ok=True, candidate_extra_reason=""):
    """→ (verdikt, detail).
    1. Globální závady (mění výběr varianty / obchodů) ⇒ NEROZHODNUTO: nelze přijmout ani zamítnout celou strategii.
    2. Platné zamítnutí: robustní test selhal na čistých datech, NEBO obě stopy selhaly aspoň jedním kritériem
       s čistými daty ⇒ ZAMÍTNUTO.
    3. KANDIDÁT jen když některá stopa prošla, všechny robustní testy prošly čistě, žádná blokující závada
       a splněna dodatečná podmínka runneru (např. latence).
    4. Jinak NEROZHODNUTO."""
    g = {k: v for k, v in (global_defects or {}).items() if v}
    ta, tb = track_status(track_a, strat_bad, bench_bad), track_status(track_b, strat_bad, bench_bad)
    rs = robustness_status(robust_ctx)
    detail = {"track_a": ta[0], "track_a_criteria": ta[1], "track_b": tb[0], "track_b_criteria": tb[1],
              "robustness": rs, "strategy_bad_periods": sorted(strat_bad), "benchmark_bad_periods": sorted(bench_bad),
              "global_defects": g, "blocking": dict(blocking or {})}
    if g:
        return "NEROZHODNUTO — globální datové závady mění výběr varianty/obchodů: " + ", ".join(sorted(g)), detail
    rob_fail = sorted(k for k, s in rs.items() if s == "fail")
    if rob_fail:
        detail["rejection_reasons"] = rob_fail
        return "ZAMÍTNUTO", detail
    if ta[0] == "fail" and tb[0] == "fail":
        detail["rejection_reasons"] = ta[1] + tb[1]
        return "ZAMÍTNUTO", detail
    clean_robust = all(s == "pass" for s in rs.values())
    granting = (ta[0], tb[0]) if TRACK_B_CAN_GRANT_CANDIDATE else (ta[0],)
    if "pass" in granting and clean_robust and not blocking and not strat_bad and not bench_bad \
            and candidate_extra_ok:
        return "KANDIDÁT NA FORWARD PAPER", detail
    why = []
    if tb[0] == "pass" and ta[0] != "pass" and not TRACK_B_CAN_GRANT_CANDIDATE:
        why.append("prošla jen stopa B, která je dočasně pozastavena (nemůže udělit KANDIDÁTA)")
    if "pass" in (ta[0], tb[0]):
        if blocking or strat_bad or bench_bad:
            why.append("blokující datové závady: " + ", ".join(sorted(blocking or {})))
        if not clean_robust:
            why.append("robustnost nehodnotitelná/na vadných datech: "
                       + ", ".join(sorted(k for k, s in rs.items() if s != "pass")))
        if not candidate_extra_ok:
            why.append(candidate_extra_reason)
    else:
        why.append("zamítnutí stojí jen na kritériích/testech s vadnými daty: "
                   + ", ".join(sorted(set(ta[1] if ta[0] == "unknown" else []) | set(tb[1] if tb[0] == "unknown" else [])
                                      | {k for k, s in rs.items() if s in ("fail_unknown", "unevaluable")})))
    return "NEROZHODNUTO — " + "; ".join(w for w in why if w), detail
