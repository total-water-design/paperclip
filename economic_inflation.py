"""Controlled official CPI sources and deterministic tariff indexation.

Provider URLs and series identifiers are selected from code-owned registries;
callers cannot supply URLs.  Provider observations remain distinguishable from
forecasts and cached data throughout the returned provenance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence
import json
import urllib.parse
import urllib.request


class InflationError(ValueError):
    """Raised when an inflation contract cannot be satisfied."""


@dataclass(frozen=True, order=True)
class Observation:
    year: int
    value: Decimal
    status: str = "actual"


@dataclass(frozen=True)
class SeriesDefinition:
    key: str
    provider: str
    country: str
    provider_series_id: str
    measure: str
    frequency: str = "annual"


SERIES: Mapping[str, SeriesDefinition] = MappingProxyType({
    "world_bank:usa:cpi_index": SeriesDefinition(
        "world_bank:usa:cpi_index", "world_bank", "USA", "FP.CPI.TOTL", "index"
    ),
    "world_bank:gbr:cpi_index": SeriesDefinition(
        "world_bank:gbr:cpi_index", "world_bank", "GBR", "FP.CPI.TOTL", "index"
    ),
    "world_bank:ind:cpi_index": SeriesDefinition(
        "world_bank:ind:cpi_index", "world_bank", "IND", "FP.CPI.TOTL", "index"
    ),
    "bls:usa:cpi_index": SeriesDefinition(
        "bls:usa:cpi_index", "bls", "USA", "CUUR0000SA0", "index"
    ),
})


Transport = Callable[[str, str, Mapping[str, str] | None, bytes | None], Any]


def _http_transport(method: str, url: str, headers: Mapping[str, str] | None, body: bytes | None) -> Any:
    request = urllib.request.Request(url, data=body, headers=dict(headers or {}), method=method)
    with urllib.request.urlopen(request, timeout=15) as response:  # nosec: controlled URLs only
        return json.loads(response.read().decode("utf-8"))


class OfficialProvider:
    name = ""

    def __init__(self, transport: Transport = _http_transport):
        self._transport = transport

    def fetch(self, series: SeriesDefinition, start_year: int, end_year: int) -> tuple[Observation, ...]:
        raise NotImplementedError


class WorldBankProvider(OfficialProvider):
    name = "world_bank"
    base_url = "https://api.worldbank.org/v2"

    def fetch(self, series: SeriesDefinition, start_year: int, end_year: int) -> tuple[Observation, ...]:
        if series.provider != self.name:
            raise InflationError("Series is not a World Bank series.")
        url = (
            f"{self.base_url}/country/{urllib.parse.quote(series.country)}/indicator/"
            f"{urllib.parse.quote(series.provider_series_id)}?format=json&per_page=1000"
            f"&date={start_year}:{end_year}"
        )
        payload = self._transport("GET", url, {"Accept": "application/json"}, None)
        rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else None
        if not isinstance(rows, list):
            raise InflationError("World Bank returned an invalid observation payload.")
        return _normalize((row.get("date"), row.get("value")) for row in rows)


class BLSProvider(OfficialProvider):
    name = "bls"
    endpoint = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    def fetch(self, series: SeriesDefinition, start_year: int, end_year: int) -> tuple[Observation, ...]:
        if series.provider != self.name or series.country != "USA":
            raise InflationError("Series is not a supported BLS US series.")
        body = json.dumps({
            "seriesid": [series.provider_series_id],
            "startyear": str(start_year),
            "endyear": str(end_year),
            "annualaverage": True,
        }).encode("utf-8")
        payload = self._transport("POST", self.endpoint, {"Content-Type": "application/json"}, body)
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise InflationError("BLS request did not succeed.")
        data = payload.get("Results", {}).get("series", [])
        rows = data[0].get("data", []) if data else []
        annual = ((row.get("year"), row.get("value")) for row in rows if row.get("period") == "M13")
        return _normalize(annual)


def _normalize(rows: Iterable[tuple[Any, Any]]) -> tuple[Observation, ...]:
    by_year: dict[int, Observation] = {}
    for raw_year, raw_value in rows:
        if raw_value is None:
            continue
        year = int(raw_year)
        value = Decimal(str(raw_value))
        if value <= 0:
            raise InflationError("Index observations must be positive.")
        by_year[year] = Observation(year, value)
    return tuple(by_year[year] for year in sorted(by_year))


def select_series(provider: str, country: str, measure: str = "index") -> SeriesDefinition:
    matches = [x for x in SERIES.values() if x.provider == provider and x.country == country.upper() and x.measure == measure]
    if len(matches) != 1:
        raise InflationError("No unique approved series exists for that provider/country/measure selection.")
    return matches[0]


def require_historical_window(observations: Sequence[Observation], start_year: int, end_year: int) -> tuple[Observation, ...]:
    if start_year > end_year:
        raise InflationError("Historical window start must not exceed end.")
    indexed = {x.year: x for x in observations}
    missing = [year for year in range(start_year, end_year + 1) if year not in indexed]
    if missing:
        raise InflationError(f"Historical window is incomplete; missing years: {missing}")
    return tuple(indexed[year] for year in range(start_year, end_year + 1))


def arithmetic_inflation(observations: Sequence[Observation]) -> Decimal:
    values = sorted(observations)
    if len(values) < 2:
        raise InflationError("At least two observations are required.")
    rates = [values[i].value / values[i - 1].value - Decimal(1) for i in range(1, len(values))]
    return sum(rates, Decimal(0)) / Decimal(len(rates))


def cagr_inflation(observations: Sequence[Observation]) -> Decimal:
    values = sorted(observations)
    if len(values) < 2 or values[-1].year == values[0].year:
        raise InflationError("At least two distinct annual observations are required.")
    periods = values[-1].year - values[0].year
    return (values[-1].value / values[0].value) ** (Decimal(1) / Decimal(periods)) - Decimal(1)


def blend_profiles(profiles: Mapping[str, Sequence[Observation]], weights_percent: Mapping[str, Decimal | int | str]) -> tuple[Observation, ...]:
    weights = {key: Decimal(str(value)) for key, value in weights_percent.items()}
    if set(weights) != set(profiles) or sum(weights.values(), Decimal(0)) != Decimal(100):
        raise InflationError("Blend weights must cover every profile and total exactly 100%.")
    if any(value < 0 for value in weights.values()):
        raise InflationError("Blend weights cannot be negative.")
    indexed = {key: {x.year: x for x in value} for key, value in profiles.items()}
    years = set.intersection(*(set(value) for value in indexed.values())) if indexed else set()
    if not years or any(set(value) != years for value in indexed.values()):
        raise InflationError("Blended profiles must have identical annual windows.")
    return tuple(Observation(year, sum(indexed[key][year].value * weights[key] / Decimal(100) for key in profiles), "blended") for year in sorted(years))


def splice_actual_forecast(actuals: Sequence[Observation], forecast: Sequence[Observation]) -> tuple[Observation, ...]:
    if not actuals:
        raise InflationError("At least one actual observation is required.")
    last_actual = max(x.year for x in actuals)
    result = {x.year: Observation(x.year, x.value, "actual") for x in actuals}
    for item in forecast:
        if item.year > last_actual:
            result[item.year] = Observation(item.year, item.value, "forecast")
    return tuple(result[year] for year in sorted(result))


def index_tariff(base_tariff: Decimal | int | str, base_year: int, profile: Sequence[Observation]) -> tuple[dict[str, str | int], ...]:
    tariff = Decimal(str(base_tariff))
    indexed = {x.year: x for x in profile}
    if tariff < 0 or base_year not in indexed:
        raise InflationError("Tariff must be non-negative and base year must exist in the profile.")
    base_index = indexed[base_year].value
    return tuple({"year": year, "tariff": str(tariff * indexed[year].value / base_index), "status": indexed[year].status} for year in sorted(indexed))


def immutable_snapshot(series: SeriesDefinition, observations: Sequence[Observation], *, retrieved_at: str) -> Mapping[str, Any]:
    record = {
        "schema": "twds.inflation_snapshot.v1",
        "series": asdict(series),
        "retrieved_at": retrieved_at,
        "observations": [{"year": x.year, "value": str(x.value), "status": x.status} for x in observations],
    }
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _freeze({**record, "sha256": sha256(canonical).hexdigest()})


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _verify_snapshot(snapshot: Mapping[str, Any]) -> None:
    expected = snapshot.get("sha256")
    unsigned = {key: _plain(value) for key, value in snapshot.items() if key != "sha256"}
    actual = sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if not expected or expected != actual:
        raise InflationError("Cached snapshot digest verification failed.")


class CachedOfficialSeries:
    """Fetch official data, falling back only to a named immutable cache."""

    def __init__(self, providers: Mapping[str, OfficialProvider], cached_snapshots: Mapping[str, Mapping[str, Any]] | None = None):
        self.providers = dict(providers)
        self.cache = dict(cached_snapshots or {})

    def get(self, series: SeriesDefinition, start_year: int, end_year: int) -> tuple[tuple[Observation, ...], Mapping[str, Any]]:
        checked_at = datetime.now(timezone.utc).isoformat()
        try:
            observations = require_historical_window(self.providers[series.provider].fetch(series, start_year, end_year), start_year, end_year)
            return observations, MappingProxyType({"provider": series.provider, "healthy": True, "source": "live", "checked_at": checked_at, "error": None})
        except Exception as exc:
            snapshot = self.cache.get(series.key)
            if not snapshot:
                raise InflationError(f"Official provider {series.provider} failed and no approved cache exists.") from exc
            if snapshot.get("series", {}).get("key") != series.key:
                raise InflationError("Cached snapshot series does not match the requested series.") from exc
            _verify_snapshot(snapshot)
            observations = _normalize((x["year"], x["value"]) for x in snapshot.get("observations", []))
            observations = require_historical_window(observations, start_year, end_year)
            health = MappingProxyType({"provider": series.provider, "healthy": False, "source": "cache", "checked_at": checked_at, "error": type(exc).__name__, "snapshot_sha256": snapshot.get("sha256")})
            return observations, health
