# PartLogic canonical data model

This document describes the **Vehicle + Fitment + Part Identity** data layer. It supports ingesting from many sources (retailers, used aggregators, OEM catalogs, EPC mirrors) without collapsing into incompatible string variants.

## Design principles

- **Canonical keys**: Normalized vehicles, configs, parts, and part numbers with stable IDs.
- **Backward compatibility**: Loose strings (year/make/model text) remain supported; they are parsed and resolved to canonical records when possible.
- **Provenance**: Source domain and confidence are stored; raw strings are never deleted or overwritten.
- **Progressive upgrade**: Records can be upgraded from string-only to canonical over time (e.g. via reconciliation jobs).

---

## A) Vehicles (canonical)

Table: `vehicles`

| Column       | Type    | Description                          |
|-------------|---------|--------------------------------------|
| vehicle_id  | INTEGER | PK                                   |
| year        | INTEGER | Model year                           |
| make        | TEXT    | Canonical make (e.g. "Audi", "BMW")  |
| model       | TEXT    | Canonical model (e.g. "A4", "3 Series") |
| generation  | TEXT    | Optional (e.g. "E46", "B8")          |
| submodel    | TEXT    | Optional (e.g. "quattro")            |
| trim        | TEXT    | Optional                             |
| body_style  | TEXT    | Optional                             |
| market      | TEXT    | Optional (US, CA, EU, etc.)          |
| created_at  | TEXT    | ISO datetime                         |
| updated_at  | TEXT    | ISO datetime                         |

Indexes: `(make, model)`, `(year)`.

---

## B) Vehicle configs

Table: `vehicle_configs`

More precise than vehicles; many configs per vehicle (engine, transmission, drivetrain).

| Column             | Type    | Description                    |
|--------------------|---------|--------------------------------|
| config_id         | INTEGER | PK                             |
| vehicle_id         | INTEGER | FK → vehicles                  |
| engine_code        | TEXT    | e.g. "AWM", "M54B30"           |
| engine_displacement_l | REAL | Optional                       |
| aspiration         | TEXT    | turbo / na / etc.              |
| transmission_code  | TEXT    | Optional                       |
| drivetrain         | TEXT    | fwd / awd / rwd / 4x4          |
| doors              | INTEGER | Optional                       |
| vin_pattern        | TEXT    | WMI/VDS or regex               |
| build_date_start   | TEXT    | Optional date                  |
| build_date_end     | TEXT    | Optional date                  |
| created_at / updated_at | TEXT |                                |

Index: `(vehicle_id)`.

---

## C) Vehicle aliases (backward compatibility + ingestion)

Table: `vehicle_aliases`

Stores **original strings as seen in the wild** and links them to canonical vehicles when resolved.

| Column      | Type    | Description                                  |
|-------------|---------|----------------------------------------------|
| alias_id    | INTEGER | PK                                            |
| alias_text  | TEXT    | **Raw string** from source (never overwritten) |
| alias_norm  | TEXT    | Normalized form for matching                 |
| year        | INTEGER | Parsed year if available                      |
| make_raw    | TEXT    | Parsed make (raw)                             |
| model_raw   | TEXT    | Parsed model (raw)                            |
| trim_raw    | TEXT    | Parsed trim (raw)                             |
| vehicle_id  | INTEGER | FK → vehicles (set when resolved)            |
| config_id   | INTEGER | FK → vehicle_configs (optional)              |
| source_domain | TEXT  | Which source asserted this alias             |
| confidence  | INTEGER | 0–100; link when ≥ threshold (e.g. 85)       |
| created_at / updated_at | TEXT |                        |

Indexes: `(alias_norm, source_domain)`, `(vehicle_id)`. Unlinked aliases (`vehicle_id IS NULL`) are candidates for reconciliation.

---

## D) Parts (canonical)

Table: `parts`

| Column     | Type    | Description                          |
|------------|---------|--------------------------------------|
| part_id    | INTEGER | PK                                   |
| part_type  | TEXT    | `oem` \| `aftermarket` \| `used` \| `universal` |
| brand      | TEXT    | Optional                             |
| name       | TEXT    | Optional                             |
| description| TEXT    | Optional                             |
| created_at / updated_at | TEXT |                        |

---

## E) Part numbers (PN + SKU namespace)

Table: `part_numbers`

One part can have many part numbers (OEM, OE, MPN, retailer SKU, UPC, etc.).

| Column        | Type    | Description                          |
|---------------|---------|--------------------------------------|
| pn_id         | INTEGER | PK                                   |
| part_id       | INTEGER | FK → parts                           |
| namespace     | TEXT    | e.g. oem, oe, manufacturer_mpn, retailer_sku, upc, ean |
| value         | TEXT    | **Raw number** as stored             |
| value_norm    | TEXT    | Normalized (uppercase, no spaces/dashes for matching) |
| source_domain | TEXT    | Optional                             |
| created_at    | TEXT    |                                      |

Unique index: `(namespace, value_norm)`. Indexes: `(part_id)`, `(value_norm)`.

---

## F) Supersessions (PN lineage)

Table: `supersessions`

| Column          | Type    | Description                |
|-----------------|---------|----------------------------|
| supersession_id | INTEGER | PK                         |
| from_pn_id      | INTEGER | FK → part_numbers (old)    |
| to_pn_id        | INTEGER | FK → part_numbers (new)    |
| effective_date  | TEXT    | Optional                   |
| notes           | TEXT    | Optional                   |
| source_domain   | TEXT    | Optional                   |

Indexes: `(from_pn_id)`, `(to_pn_id)`. Chain traversal yields the latest PN.

---

## G) Interchange groups

Table: `interchange_groups`

| Column        | Type    | Description                                  |
|---------------|---------|----------------------------------------------|
| group_id      | INTEGER | PK                                           |
| group_type    | TEXT    | hollander_like, aftermarket_interchange, oem_equivalence |
| source_domain | TEXT    | Optional                                     |
| notes         | TEXT    | Optional                                     |
| created_at / updated_at | TEXT |                              |

---

## H) Interchange members

Table: `interchange_members`

| Column   | Type    | Description   |
|----------|---------|---------------|
| group_id | INTEGER | FK → interchange_groups |
| pn_id    | INTEGER | FK → part_numbers       |

Primary key: `(group_id, pn_id)`.

---

## I) Kits (bundle relationships)

Table: `kits`

| Column            | Type    | Description        |
|-------------------|---------|--------------------|
| kit_id            | INTEGER | PK                 |
| kit_part_id       | INTEGER | FK → parts (bundle)|
| component_part_id | INTEGER | FK → parts (component) |
| qty               | REAL    | Optional           |
| notes             | TEXT    | Optional           |
| source_domain     | TEXT    | Optional           |

---

## J) Fitments (part ↔ vehicle/config)

Table: `fitments`

Core join: which part fits which vehicle (and optionally which config), with qualifiers.

| Column           | Type    | Description                              |
|------------------|---------|------------------------------------------|
| fitment_id       | INTEGER | PK                                       |
| part_id          | INTEGER | FK → parts                               |
| vehicle_id       | INTEGER | FK → vehicles (minimum)                  |
| config_id        | INTEGER | FK → vehicle_configs (preferred when known) |
| position         | TEXT    | front / rear / left / right / etc.       |
| qualifiers_json  | TEXT    | JSON: { "with_abs": true, "except_turbo": true, "pr_codes": ["1LT"], ... } |
| vin_range_start  | TEXT    | Optional                                 |
| vin_range_end    | TEXT    | Optional                                 |
| build_date_start | TEXT    | Optional                                 |
| build_date_end   | TEXT    | Optional                                 |
| confidence       | INTEGER | 0–100                                    |
| source_domain    | TEXT    | Optional                                 |
| created_at / updated_at | TEXT |                            |

Indexes: `(part_id)`, `(vehicle_id)`, `(config_id)`, `(source_domain)`.

---

## K) Sources (registry)

The **source registry** is JSON-backed (`app/data/sources_registry.json`). Each source has:

- `domain` (unique), `name`, `category`, `tags`, `notes`
- `source_type`: `buyable` | `reference`
- `reference_kind` (for reference sources): `standards`, `vin_decode`, `oem_epc`, `service_info`, `tsb_recall`, `paint_trim`, `industrial_specs`
- `status`, `priority`
- `supports_vin`, `supports_part_number_search`, `supports_fitment`
- `robots_policy`, `sitemap_url`, `api_available`

---

## Normalization

- **Domain**: Strip scheme and path; lowercase (`normalize_domain` in `source_registry`).
- **Vehicle string**: Normalize whitespace/punctuation; drivetrain tokens (Quattro, 4Motion, AWD) to consistent forms; produce `alias_norm` for matching (`vehicle_normalizer`).
- **Part number**: `value` = raw; `value_norm` = uppercase, no spaces, optional strip hyphens (`part_number_value_norm` in `part_numbers`).

---

## Resolver and reconciliation

- **resolve_vehicle_alias(alias_text, source_domain)**
  1) Exact `alias_norm` + source_domain already linked → return that vehicle_id/config_id.
  2) Parse year/make/model; match existing `vehicles` row.
  3) If no match and confidence ≥ threshold, create new `vehicles` row and link.
  4) Upsert `vehicle_aliases` (preserve raw `alias_text`, set `vehicle_id`/`config_id` when confidence ≥ 85).

- **reconcile_unlinked_aliases(limit)**
  Runs the resolver on aliases where `vehicle_id IS NULL` (incremental).

---

## Search integration (backward compatibility)

- Existing search API still accepts loose `vehicle_make`, `vehicle_model`, `vehicle_year` query params.
- When those are present, the backend builds an alias string, calls `resolve_vehicle_alias`, and stores `vehicle_id`/`config_id` on `search_history` for the recorded search.
- No change to response shape or UI; resolution is additive and used for caching and analytics.

---

## Import and CLI

- **import_vehicles.py** — `--file <csv>` (year, make, model, generation, submodel, trim, body_style, market)
- **import_aliases.py** — `--file <csv>` (alias_text, source_domain, year, make_raw, model_raw, trim_raw)
- **import_parts.py** — `--file <csv>` (part_type, brand, name, description)
- **import_fitments.py** — `--file <csv>` (part_id, vehicle_id, config_id, position, qualifiers_json, …)
- **reconcile_aliases.py** — `--limit 500` (run resolver on unlinked aliases)

Starter CSV templates: `data/templates/vehicles_template.csv`, `aliases_template.csv`, `parts_template.csv`, `fitments_template.csv`.

---

## Admin API and UI

- **GET /canonical/aliases** — List vehicle aliases; `unlinked_only=true` for reconciliation queue.
- **PATCH /canonical/aliases/{id}/link** — Manually link alias to vehicle_id (and optional config_id).
- **GET /canonical/part_numbers** — Search by namespace and/or value_norm.
- **GET /canonical/fitments** — Fitment inspector: filter by year/make/model or part_id; returns qualifiers and provenance.
- **GET /canonical/vehicles** — List vehicles (for admin when linking).

Admin UI pages: Vehicle Aliases, Part Numbers, Fitment Inspector (see frontend `/admin/aliases`, `/admin/parts`, `/admin/fitments`).
