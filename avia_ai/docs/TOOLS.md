# Internal Tool API

Avia AI is a Streamlit app, not a REST service — there's no HTTP endpoint
to call from outside the process. The real "API surface" is the set of
LangChain `@tool`-decorated Python functions in `app/tools/`, bound to the
Ollama model in `app/agent/nodes.py`. This page documents each one the way
you'd document a REST endpoint: signature, arguments, and an example
call/response.

All tools return a plain string (already formatted for chat display) and
never raise — provider failures are caught and turned into a
`"⚠️ <message>"` string instead.

---

## `search_flights`

Search real flight offers between two airports/cities on a given date.

| Arg | Type | Required | Notes |
|---|---|---|---|
| `origin` | `str` | ✅ | Origin IATA code, e.g. `"TAS"` |
| `destination` | `str` | ✅ | Destination IATA code, e.g. `"IST"` |
| `departure_date` | `str` | ✅ | `YYYY-MM-DD` |
| `adults` | `int` | — | default `1` |
| `children` | `int` | — | default `0` |
| `return_date` | `str \| None` | — | `YYYY-MM-DD` |
| `cabin_class` | `str \| None` | — | `"economy"`, `"business"`, ... |
| `max_stops` | `int \| None` | — | `0` = direct only |
| `airline` | `str \| None` | — | name/code filter |
| `time_of_day` | `str \| None` | — | `"morning"`, `"afternoon"`, `"evening"`, `"night"` |
| `sort_by` | `str \| None` | — | `"price"`, `"duration"`, `"departure_time"` |

**Example call:** `search_flights(origin="TAS", destination="IST", departure_date="2026-08-15", max_stops=0)`

**Example response:**
```
TAS -> IST (2026-08-15) uchun 3 ta reys topildi:

| Aviakompaniya | Reys  | Jo'nash   | Yetib borish | ... | Narx      |
|---------------|-------|-----------|--------------|-----|-----------|
| Turkish...    | TK371 | TAS 02:30 | IST 05:45    | ... | 210.00 USD|
```

---

## `compare_flights`

Compare flights from the *most recent* search — never re-fetches.

| Arg | Type | Required |
|---|---|---|
| `flight_numbers` | `list[str] \| None` | — |
| `airlines` | `list[str] \| None` | — |

**Example call:** `compare_flights(airlines=["Turkish Airlines", "Uzbekistan Airways"])`

---

## `search_airports`

Find airports near a free-text city/place name (Geoapify).

| Arg | Type | Required |
|---|---|---|
| `city_or_place` | `str` | ✅ |

**Example call:** `search_airports(city_or_place="Istanbul")` → lists IST, SAW, ISL with city/country.

---

## `lookup_airport_by_code`

Resolve a 3-letter IATA code to its airport/city/country.

| Arg | Type | Required |
|---|---|---|
| `iata_code` | `str` | ✅ |

---

## `convert_currency`

Convert an arbitrary amount using a live rate.

| Arg | Type | Required |
|---|---|---|
| `amount` | `float` | ✅ |
| `from_currency` | `str` | ✅ | 3-letter code |
| `to_currency` | `str` | ✅ | 3-letter code |

---

## `convert_last_flight_prices`

Convert every priced flight from the last search into another currency.
Flights with no price (see AviationStack limitation) are skipped, not
guessed.

| Arg | Type | Required |
|---|---|---|
| `to_currency` | `str` | ✅ |

---

## `recommend_flight`

Pick one flight from the last search by a criterion.

| Arg | Type | Required | Notes |
|---|---|---|---|
| `criteria` | `str` | — | `"cheapest"` (default), `"fastest"`, `"direct"` |

---

## `get_destination_weather`

Current weather for a city (OpenWeatherMap).

| Arg | Type | Required |
|---|---|---|
| `city` | `str` | ✅ |

---

## `get_flight_status`

Live/scheduled status for a specific flight number (AviationStack).

| Arg | Type | Required |
|---|---|---|
| `flight_iata` | `str` | ✅ | e.g. `"TK371"` |

---

## `web_search`

General travel info outside the other tools' domain (visa rules, safety
advisories, city guides). **Never** used for flight prices/schedules.

| Arg | Type | Required |
|---|---|---|
| `query` | `str` | ✅ |

**Example response:**
```
- **Uzbekistan Passport Visa for Turkey**: Visa not required (https://...)
- **Visa Information For Foreigners**: ... (https://www.mfa.gov.tr/...)
```

---

## `recommend_destination_guide`

Real, sourced tourist attraction + hotel suggestions for a city (two
live web searches — never invents place/hotel names).

| Arg | Type | Required |
|---|---|---|
| `city` | `str` | ✅ |
