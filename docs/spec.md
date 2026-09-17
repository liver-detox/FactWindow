# FactWindow v0.2.0 Specification

## Product promise

FactWindow puts expectations recorded before a scheduled event beside sourced facts and user-supplied answers published after it. A report keeps the original questions, the evidence available at generation time, and remaining gaps visible.

## Scope

- `demo` creates fictional inputs and a Markdown/JSON report using a simulated 2099 clock.
- `freeze` reads before-event TOML, requires a timezone-aware future event, and writes a JSON snapshot with the freeze time and a SHA-256 content digest.
- `compare` verifies a frozen snapshot and reads after-event TOML. It creates `report.md` and `report.json` using the real current time unless a caller explicitly supplies a clock through the core Python API.
- CLI guidance, the demo, and Markdown reports use Chinese-first bilingual labels. JSON field names and status codes remain English identifiers.
- Python 3.11 or newer; standard-library runtime; Apache-2.0.

## Before-event input

Required top-level fields are `event_id`, `title`, `scheduled_at`, and `question`. `scheduled_at` must be a quoted ISO-8601 datetime with a timezone, strictly later than the freeze time. One or more `[[expectations]]` entries are required:

| Field | Meaning |
|---|---|
| `metric` | Unique metric name, used to match the after-event fact |
| `expected` | Number, string, or boolean |
| `prior` | Optional prior value |
| `unit` | Optional unit; match the after-event spelling exactly |
| `source_url` | Complete HTTPS URL for the expectation's source |

Optional top-level fields:

- `unknowns`: a list of non-empty strings, retained as unresolved notes for compatibility. These notes have no answer-matching mechanism.
- `supports_if` and `refutes_if`: non-empty text describing what would support or refute the view. FactWindow displays this text without evaluating it.
- `review_by`: a quoted timezone-aware datetime at or after `scheduled_at`. It is a displayed review deadline, not an automated reminder or cutoff on accepting later evidence.

Optional `[[questions]]` entries each contain a unique non-empty `id` and non-empty `text`. IDs allow later answers to refer to the original frozen questions. Questions omitted from the after-event file remain pending.

Top-level fields must appear before the first `[[...]]` table in TOML; otherwise TOML assigns them to the preceding table.

## After-event input

The top-level `event_id` must match the snapshot. `facts` is required and must be a list. Use one or more `[[facts]]` tables, or write top-level `facts = []` if the event has occurred but no facts are available. Do not retain fictional facts when recording a real event.

Each fact contains a unique `metric`, scalar `actual`, optional `unit`, complete HTTPS `source_url`, and quoted timezone-aware `published_at`.

Optional `[[answers]]` entries contain:

| Field | Contract |
|---|---|
| `question_id` | An existing frozen question ID; at most one answer per question |
| `status` | `answered`, `pending`, or `conflicting` |
| `reason` | A non-empty explanation supplied by the user |
| `sources` | Nested `[[answers.sources]]` entries with `source_url` and `published_at` |

`answered` and `conflicting` require at least one source. `pending` may have no sources. A source attachment does not establish that the answer is true or that conflicting evidence has been fully collected. The status is the user's assessment.

Optional top-level `interpretation` holds the user's non-empty overall assessment, displayed separately from calculated metric results.

### Time rules

Every fact and every answer source must satisfy:

```text
event scheduled_at <= source published_at <= report generated_at
```

Reports cannot be generated before the event. All supplied datetimes, including core API `now` and `generated_at`, must include a timezone. Different timezone offsets are compared as instants. The upper bound also applies to unplanned facts and sources attached to pending answers.

These are consistency checks on supplied timestamps. FactWindow does not fetch or verify the source publication time.

## Comparison rules

Metrics match by exact name. Missing expectations and unplanned facts remain visible. Numeric differences are `actual - expected`; integers and finite floats belong to the same numeric category. Booleans are distinct from numbers. Strings are not parsed as numbers, so `100` and `"100"` are incompatible types.

| Status | Meaning | Difference calculated? |
|---|---|---|
| `above`, `below`, `matched` | Comparable numbers, relative to expected value | Yes |
| `matched`, `changed` | Comparable strings or booleans | No |
| `missing` | Expected metric has no fact | No |
| `unplanned` | Fact has no frozen expectation | No |
| `unit_mismatch` | Both sides declare different units | No |
| `unit_unconfirmed` | Exactly one side declares a unit | No |
| `type_mismatch` | Incompatible value categories | No |

Two values with both units omitted may be compared; the tool cannot infer whether their real-world units are compatible. It does not convert units. When units prevent comparison, the unit status takes precedence over a type mismatch. “Above” and “below” describe numerical relationships, not whether an outcome is good or bad.

`missing`, `unit_mismatch`, `unit_unconfirmed`, and `type_mismatch` rows are unresolved. Pending and conflicting questions are also unresolved. Answered questions retain their original text, reason, and sources in the report but are omitted from unresolved items. Legacy `unknowns` stay unresolved independently of structured question answers.

## Snapshot and report formats

New freezes write `schema_version = "factwindow.snapshot.v2"`. Existing `factwindow.snapshot.v1` snapshots remain readable and are not rewritten. The tool validates the snapshot and verifies `content_sha256` before comparison.

New reports use `schema_version = "factwindow.report.v2"` and include:

- event identity, research question, scheduled time, freeze time, and generation time;
- `snapshot_sha256`, matching the verified snapshot's `content_sha256`;
- metric rows preserving expected/actual values, sources, and fact publication times;
- `expectation_unit` and `fact_unit` on each row; the legacy `unit` value is populated only when both declared units match, and is otherwise `null`;
- `questions`, each with `id`, original `text`, `status`, `reason`, and `sources`;
- unresolved notes and optional support/refutation conditions, review deadline, and interpretation.

Markdown shows both units, source publication times, snapshot association, and question answers. The digest checks local content consistency and associates artifacts; anyone who changes a snapshot can calculate a new digest. It is not a trusted timestamp, proof of pre-event existence, or source authentication.

Consumers should check `schema_version` and handle the new comparison statuses and separate unit fields. Old snapshots are accepted, but old after-event files can now fail if they contain future-dated evidence. A one-sided unit omission or a string/number pair no longer produces a normal comparison.

## First-use acceptance path

From a clean checkout, the documented installation and `factwindow demo` commands create a readable report without editing IDs. Demo input files exactly match `examples/synthetic`. The [first-event guide](first-event.md) separates freezing a future event from completing the record after evidence is published. An empty-facts report after the event is supported and keeps missing facts visible.

## Boundaries

No network requests, live-source adapters, account integration, investment recommendations, source-truth judgments, automatic hypothesis scoring, database, web UI, or external timestamp service. Support/refutation conditions and review deadlines remain user-authored context. Synthetic examples are independently fictional and do not demonstrate external adoption or predictive effectiveness.
