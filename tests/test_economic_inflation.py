import json
from decimal import Decimal
from pathlib import Path

import pytest

from economic_inflation import (
    BLSProvider, CachedOfficialSeries, InflationError, Observation,
    WorldBankProvider, arithmetic_inflation, blend_profiles, cagr_inflation,
    immutable_snapshot, index_tariff, require_historical_window,
    select_series, splice_actual_forecast,
)


FIXTURES = Path(__file__).parent / "fixtures" / "economic_inflation"


def fixture_transport(name):
    payload = json.loads((FIXTURES / name).read_text())
    def transport(method, url, headers, body):
        assert url.startswith("https://")
        return payload
    return transport


def test_country_series_selection_is_allowlisted_and_rejects_unknowns():
    assert select_series("world_bank", "usa").provider_series_id == "FP.CPI.TOTL"
    assert select_series("bls", "USA").provider_series_id == "CUUR0000SA0"
    with pytest.raises(InflationError, match="No unique approved series"):
        select_series("world_bank", "ZZZ")


def test_world_bank_and_bls_adapters_parse_only_annual_official_data():
    wb = WorldBankProvider(fixture_transport("world_bank_cpi.json"))
    bls = BLSProvider(fixture_transport("bls_cpi.json"))
    expected = (Observation(2021, Decimal("100.0")), Observation(2022, Decimal("110.0")), Observation(2023, Decimal("121.0")))
    assert wb.fetch(select_series("world_bank", "USA"), 2021, 2023) == expected
    assert bls.fetch(select_series("bls", "USA"), 2021, 2023) == expected


def test_required_window_and_arithmetic_and_cagr_methods():
    values = [Observation(2021, Decimal("100")), Observation(2022, Decimal("110")), Observation(2023, Decimal("121"))]
    assert require_historical_window(values, 2021, 2023) == tuple(values)
    assert arithmetic_inflation(values) == Decimal("0.1")
    assert cagr_inflation(values) == Decimal("0.1")
    with pytest.raises(InflationError, match=r"missing years: \[2022\]"):
        require_historical_window([values[0], values[2]], 2021, 2023)


def test_blend_requires_exact_100_percent_and_aligned_windows():
    a = [Observation(2024, Decimal("100")), Observation(2025, Decimal("104"))]
    b = [Observation(2024, Decimal("100")), Observation(2025, Decimal("110"))]
    result = blend_profiles({"labor": a, "energy": b}, {"labor": "40", "energy": "60"})
    assert result[-1] == Observation(2025, Decimal("107.6"), "blended")
    with pytest.raises(InflationError, match="exactly 100"):
        blend_profiles({"labor": a, "energy": b}, {"labor": 40, "energy": 59.99})


def test_snapshot_is_deterministic_read_only_and_cache_fallback_is_explicit():
    series = select_series("world_bank", "USA")
    values = (Observation(2021, Decimal("100")), Observation(2022, Decimal("110")))
    snap = immutable_snapshot(series, values, retrieved_at="2026-08-28T00:00:00Z")
    assert snap["sha256"] == immutable_snapshot(series, values, retrieved_at="2026-08-28T00:00:00Z")["sha256"]
    with pytest.raises(TypeError):
        snap["sha256"] = "changed"
    with pytest.raises(TypeError):
        snap["series"]["country"] = "GBR"
    with pytest.raises(TypeError):
        snap["observations"][0]["value"] = "999"
    failed = WorldBankProvider(lambda *args: (_ for _ in ()).throw(TimeoutError()))
    observations, health = CachedOfficialSeries({"world_bank": failed}, {series.key: snap}).get(series, 2021, 2022)
    assert observations == values
    assert health["healthy"] is False
    assert health["source"] == "cache"
    assert health["error"] == "TimeoutError"


def test_provider_failure_without_matching_cache_is_not_silently_substituted():
    series = select_series("world_bank", "USA")
    failed = WorldBankProvider(lambda *args: (_ for _ in ()).throw(TimeoutError()))
    with pytest.raises(InflationError, match="no approved cache"):
        CachedOfficialSeries({"world_bank": failed}).get(series, 2021, 2022)


def test_tampered_cache_is_rejected_before_fallback_use():
    series = select_series("world_bank", "USA")
    failed = WorldBankProvider(lambda *args: (_ for _ in ()).throw(TimeoutError()))
    tampered = dict(immutable_snapshot(series, [Observation(2021, Decimal("100"))], retrieved_at="2026-08-28T00:00:00Z"))
    tampered["observations"] = [{"year": 2021, "value": "999", "status": "actual"}]
    with pytest.raises(InflationError, match="digest verification failed"):
        CachedOfficialSeries({"world_bank": failed}, {series.key: tampered}).get(series, 2021, 2021)


def test_actual_forecast_splice_never_overwrites_actual_and_indexes_tariff():
    actual = [Observation(2023, Decimal("100")), Observation(2024, Decimal("105"))]
    forecast = [Observation(2024, Decimal("999")), Observation(2025, Decimal("110.25"))]
    profile = splice_actual_forecast(actual, forecast)
    assert profile == (
        Observation(2023, Decimal("100"), "actual"),
        Observation(2024, Decimal("105"), "actual"),
        Observation(2025, Decimal("110.25"), "forecast"),
    )
    tariffs = index_tariff("2.00", 2023, profile)
    assert tariffs[-1] == {"year": 2025, "tariff": "2.2050", "status": "forecast"}
