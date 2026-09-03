# FactWindow MVP Specification

## Product promise

FactWindow puts expectations recorded before a scheduled event beside sourced facts published after it.

## Audience

Independent analysts, journalists, industry researchers, product researchers, and policy observers who want a compact before/after event brief without a database, web service, or trading integration.

## Version 0.1.1 scope

- Provide three commands: `demo`, `freeze`, and `compare`.
- `demo` creates a complete synthetic example and a readable Markdown report.
- `freeze` reads one TOML before-event file, requires a timezone-aware future event time, records the current UTC time, and writes a JSON snapshot with a SHA-256 content digest.
- `compare` reads a frozen snapshot and one TOML after-event file, verifies the snapshot digest and event identity, compares metrics, and writes `report.md` plus `report.json`.
- Reports show the research question, prior/expected/actual values, differences, source links, and unresolved items.
- The default CLI help, synthetic demo, and Markdown report use short Chinese-first bilingual labels. JSON keys and status codes remain stable English identifiers; human-readable text values in JSON may be bilingual.
- Errors name the invalid field and suggest a correction where useful.
- The CLI provides normal top-level and subcommand help.
- Python 3.11 or newer; no runtime dependencies outside the standard library.
- Apache-2.0 license; English and Simplified Chinese README files.

## Explicit non-goals

- No network access, live-source adapters, brokerage or account integration.
- No investment recommendation, prediction, return claim, or automated judgment.
- No database, web UI, LLM, plugin system, policy engine, permission matrix, or protected ledger.
- No private-project paths, real symbols, watchlists, holdings, transactions, reports, credentials, or licensed datasets.
- No dependency on another project in version 0.1.

## Input contract

The before-event TOML contains `event_id`, `title`, `scheduled_at`, `question`, optional `unknowns`, and one or more `[[expectations]]` entries. Each expectation contains `metric`, `expected`, optional `prior`, optional `unit`, and an HTTPS `source_url`.

The after-event TOML contains the same `event_id` and one or more `[[facts]]` entries. Each fact contains `metric`, `actual`, optional `unit`, an HTTPS `source_url`, and a timezone-aware `published_at` at or after the event time. `now` and `generated_at` values supplied to the core API must also be timezone-aware.

Metric names must be unique within each file. Values may be numbers, strings, or booleans. Numeric differences are `actual - expected`; other values are reported as `matched` or `changed`. Missing expected metrics remain visible as unresolved.
Facts that were not listed in the frozen expectations remain visible with status `unplanned` rather than being discarded.

Row status values are `above`, `below`, or `matched` for comparable numbers; `matched` or `changed` for other comparable scalars; `missing` for an expected metric with no fact; `unplanned` for a fact with no frozen expectation; and `unit_mismatch` when both sides declare different units. `missing` and `unit_mismatch` rows are listed as unresolved. Unit mismatch does not block the rest of the report and no numeric difference is calculated for that row.

## Acceptance path

From a clean checkout, a user can run the documented installation command and `factwindow demo`, then open the generated `report.md` without editing IDs or supplying long option lists.
