from apps.risk.levels import RiskLevel
from apps.risk.ranking import RiskSegment, rank_routes, summarize_route

LOW, MOD, HIGH, SEV, STOP = RiskLevel


def test_summary_aggregates_miles_by_level_and_weighted_average() -> None:
    summary = summarize_route(
        "a",
        duration_seconds=3600,
        segments=[RiskSegment(LOW, 50), RiskSegment(HIGH, 25), RiskSegment(SEV, 25)],
    )
    assert summary.total_miles == 100
    assert summary.severe_miles == 25
    assert summary.high_miles == 25
    assert summary.average_risk == (0 * 50 + 2 * 25 + 3 * 25) / 100
    assert summary.max_level is SEV
    assert summary.is_travel_advised


def test_zero_length_segments_add_no_miles_but_still_set_the_peak() -> None:
    summary = summarize_route("a", 10, [RiskSegment(STOP, 0.0), RiskSegment(LOW, 5)])
    assert summary.no_travel_miles == 0
    assert summary.average_risk == 0
    assert summary.max_level is STOP
    assert not summary.is_travel_advised


def test_fewest_severe_miles_wins_even_if_slower() -> None:
    fast_but_severe = summarize_route("fast", 3600, [RiskSegment(SEV, 10), RiskSegment(LOW, 90)])
    slow_but_safe = summarize_route("slow", 7200, [RiskSegment(HIGH, 50), RiskSegment(LOW, 70)])

    ranked = rank_routes([fast_but_severe, slow_but_safe])

    assert [r.summary.route_id for r in ranked] == ["slow", "fast"]
    assert ranked[0].recommended
    assert ranked[0].reasons == ["fewest Severe miles vs. fast"]


def test_high_miles_break_severe_ties_then_average_then_duration() -> None:
    a = summarize_route("a", 100, [RiskSegment(HIGH, 10), RiskSegment(LOW, 90)])
    b = summarize_route("b", 50, [RiskSegment(HIGH, 20), RiskSegment(LOW, 80)])
    c = summarize_route("c", 200, [RiskSegment(HIGH, 10), RiskSegment(MOD, 90)])
    d = summarize_route("d", 300, [RiskSegment(HIGH, 10), RiskSegment(LOW, 90)])

    ranked = rank_routes([d, c, b, a])

    assert [r.summary.route_id for r in ranked] == ["a", "d", "c", "b"]
    assert ranked[0].reasons == [
        "shortest travel time vs. d",
        "lowest average risk vs. c",
        "fewest High miles vs. b",
    ]


def test_no_travel_miles_disqualify_a_route_from_recommendation() -> None:
    stop = summarize_route("stop", 10, [RiskSegment(STOP, 1), RiskSegment(LOW, 99)])
    severe = summarize_route("severe", 1000, [RiskSegment(SEV, 60), RiskSegment(LOW, 40)])

    ranked = rank_routes([stop, severe])

    assert [r.summary.route_id for r in ranked] == ["severe", "stop"]
    assert ranked[0].recommended
    assert ranked[0].reasons == ["no No-Travel miles vs. stop"]


def test_nothing_is_recommended_when_every_route_has_no_travel_miles() -> None:
    a = summarize_route("a", 10, [RiskSegment(STOP, 5), RiskSegment(LOW, 95)])
    b = summarize_route("b", 10, [RiskSegment(STOP, 50), RiskSegment(LOW, 50)])

    ranked = rank_routes([b, a])

    assert ranked[0].summary.route_id == "a"
    assert not any(r.recommended for r in ranked)


def test_single_route_is_recommended_without_reasons() -> None:
    ranked = rank_routes([summarize_route("only", 10, [RiskSegment(LOW, 10)])])
    assert ranked[0].recommended
    assert ranked[0].reasons == []
