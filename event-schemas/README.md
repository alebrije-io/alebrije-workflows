# Alebrije Event Schema Registry

Source of truth for the shape of every event that travels the Alebrije
EventBus (Redis Streams). Implements [ADR-31](../../ADR-31-event-bus-schema-governance.md)
Phase 1.

JSON Schema **Draft 2020-12**. One file per event, one file for the shared
envelope. Validators live in the three common libraries:

| Language | Validator module                                            | Underlying lib                   |
|----------|-------------------------------------------------------------|----------------------------------|
| Python   | `alebrije_common.events.validator`                          | `jsonschema`                     |
| Elixir   | `AlebrijeCommon.Events.Validator`                           | `ex_json_schema`                 |
| Go       | `github.com/alebrije-io/alebrije-common-go/events/validator`| `santhosh-tekuri/jsonschema/v5`  |

---

## 1. Naming convention

Every event file is named `<event_type>.v<major>.json` where `<event_type>`
follows the strict ADR-31 pattern:

```
<domain>.<entity>.<action>
```

* `<domain>` — bounded context (`rewards`, `crm`, `payments`, `cadences`, ...)
* `<entity>` — noun (`points`, `contact`, `invoice`, ...)
* `<action>` — past-tense verb (`earned`, `stage_changed`, `completed`, ...)

All three segments are `snake_case`, lowercase, letters + underscores only.
The regex in `envelope.v1.json` enforces it at runtime:

```regex
^[a-z_]+\.[a-z_]+\.[a-z_]+$
```

The filename (minus the `.vN.json` suffix) MUST equal the `event_type`
string — validators rely on this mapping to locate the schema.

---

## 2. Envelope (`envelope.v1.json`)

Every event uses the same outer shape: `event_id`, `event_type`,
`event_version`, `tenant_id`, `timestamp`, `producer`, `data`, plus optional
`context_id`, `external_ref`, and `trace_id`. Per-event schemas inherit
this envelope via:

```json
{
  "allOf": [
    { "$ref": "envelope.v1.json" },
    { "properties": { "event_type": { "const": "..." }, "data": { ... } } }
  ]
}
```

Callback events that MUST echo a correlation id (for example
`notifications.email.delivered`) override `required` to include
`external_ref` on top of the envelope's base requirements.

---

## 3. Events covered in Phase 1

| Event                                  | Phase 1 schema file                           |
|----------------------------------------|-----------------------------------------------|
| `rewards.points.earned`                | `rewards.points.earned.v1.json`               |
| `rewards.points.redeemed`              | `rewards.points.redeemed.v1.json`             |
| `crm.contact.created`                  | `crm.contact.created.v1.json`                 |
| `crm.contact.stage_changed`            | `crm.contact.stage_changed.v1.json`           |
| `payments.invoice.overdue`             | `payments.invoice.overdue.v1.json`            |
| `payments.payment.completed`           | `payments.payment.completed.v1.json`          |
| `notifications.email.delivered`        | `notifications.email.delivered.v1.json`       |
| `notifications.email.opened`           | `notifications.email.opened.v1.json`          |
| `field_ops.order.completed`            | `field_ops.order.completed.v1.json`           |
| `cadences.enrolled`                    | `cadences.enrolled.v1.json`                   |
| `cadences.converted`                   | `cadences.converted.v1.json`                  |

---

## 4. How to add a new event

1. Pick a name that satisfies `<domain>.<entity>.<action>` — past-tense
   verb, snake_case everywhere.
2. Create `<event_type>.v1.json` next to the existing schemas. Start from
   an existing file as a template; always use `allOf` + `$ref` to inherit
   `envelope.v1.json`.
3. Put `"event_type": { "const": "<event_type>" }` inside the second
   `allOf` branch so the envelope regex is further narrowed to this
   specific event.
4. Define `data.required` with the minimum set a consumer can rely on.
   Prefer `additionalProperties: true` on `data` — forward compatibility
   is an ADR-31 invariant (consumers must tolerate unknown fields).
5. If the event is a provider callback that needs to echo a correlation
   id, add `"required": ["external_ref"]` at the top level of the branch
   (see `notifications.email.delivered.v1.json`).
6. Open a PR. CI should validate the schema with a draft-2020-12 parser
   and, ideally, confirm a sample event round-trips through all three
   language validators (Phase 4).

---

## 5. How consumers validate

**Python** (FastAPI services):

```python
from alebrije_common.events.validator import validate_event

def on_event(event: dict) -> None:
    validate_event(event)  # raises jsonschema.ValidationError if invalid
    ...
```

**Elixir** (Broadway / Phoenix services):

```elixir
case AlebrijeCommon.Events.Validator.validate(event) do
  :ok -> process(event)
  {:error, errors} -> Logger.warn("invalid event: #{inspect(errors)}")
end
```

**Go** (go-redis consumers):

```go
v, err := validator.New("/path/to/event-schemas")
if err != nil { return err }

if err := v.Validate(event["event_type"].(string), event); err != nil {
    return fmt.Errorf("invalid event: %w", err)
}
```

Phase 2 will wire these into the publishers and consumers inside the
`alebrije-common*` libraries so services don't have to call them by hand.

---

## 6. Versioning policy

Version per-event, not globally. `event_version` in the envelope is
`<major>.<minor>` and matches the `.vN` suffix on the file.

**Additive (minor bump, same file):**

* Add an optional field to `data`.
* Add a new enum value (consumers tolerate unknowns).
* Relax an existing constraint (remove `maxLength`, lower `minimum`, ...).

Ship as a minor bump — no coordination required because forward compat is
guaranteed.

**Breaking (major bump, new file):**

* Rename or remove a field.
* Change a field's type.
* Make a previously optional field required.
* Tighten a constraint.

Procedure:

1. Create `<event_type>.v2.json` next to `v1`.
2. Publish to a new stream (`events:<domain>:v2`) during the deprecation
   window (minimum 2 sprints per ADR-31 §5.2).
3. Publishers emit to both streams; consumers migrate one at a time.
4. Remove `v1` only after every known consumer is on `v2`.

**Forward compatibility (consumers):** consumers MUST tolerate unknown
fields in `data`. In Python: `model_config = ConfigDict(extra="ignore")`.
In Go: default `json.Unmarshal` behaviour. In Elixir: use `Map.get` instead
of exhaustive pattern matching.

---

## 7. Out of scope for Phase 1

* Wiring validators into `publish` / `consume` paths of the common libs
  (Phase 2).
* CI workflow that runs the contract check for every consumer of a
  modified schema (Phase 4).
* Golden-sample `.example.json` fixtures per event (Phase 2).
* Migration of legacy event names (`payment.confirmed` →
  `payments.payment.completed`, `contact.stage_changed` →
  `crm.contact.stage_changed`, etc.) — Phase 5.
