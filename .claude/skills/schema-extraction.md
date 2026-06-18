---
name: schema-extraction
description: Inventory explicit data schemas and reconstruct implicit data shapes from code, then produce a schema-map table. Use during the data/merge phase of codebase analysis. Handles repos with no schema files by reconstructing shape from models/interfaces/forms.
---

# Schema Extraction

Goal: every data entity's shape is captured and **schema-linked, not inferred loosely**. Serves accurate target-state design (the migrated frontend needs field types + constraints).

## 1. Classify data files
- **schema-defining** — declares shape: `.sql`/DDL, JSON-Schema, XSD, `.proto`, ORM models, migrations, data dictionaries, fixed-width/copybook layouts, pydantic/TS-interface models.
- **data-bearing** — holds rows/values: `.csv`, `.json` fixtures, seed data.

## 2. No schema files? Reconstruct from code
Most apps define shape implicitly. Reconstruct from: TypeScript interfaces, Angular models, class fields, form field definitions, pydantic `BaseModel`s, the way API responses are destructured. Cite `file:line` for each reconstructed entity. Mark these `category: inference`.

## 3. Link schema → entity → consumers
Build the chain so schemas join the architecture picture, not float loose. For each entity: where defined, what fields/types/constraints, who reads/writes it.

## 4. Flag both gap directions
- **orphaned schema** — schema on disk but nothing references it.
- **missing schema** — data entity used in code but no shape defined anywhere.

## 5. Constraints are business rules
Field length, NOT NULL, enums of valid codes, foreign keys, regex — extract these as candidate business rules, cited.

## Output — schema map (markdown table, report-only)
```
| Entity | Field | Type | Constraint | Defined at (file:line) | Source |
|--------|-------|------|------------|------------------------|--------|
| Contract | awardId | string | required | models/contract.ts:14 | explicit |
| Contract | amount  | number | > 0      | models/contract.ts:18 | reconstructed |
```
Plus two lists: orphaned schemas, missing schemas.
