# planned/ — schemas with no implemented producer

Files here are registered contracts for event types that **no service currently
emits**. They are excluded from the registry validators (Go
`alebrije-common-go/events/validator`, and by extension the equivalent
Python/Elixir validators, plus the `reusable-event-schema-check.yml` CI glob)
because those all scan `event-schemas/*.v1.json` non-recursively — a
subdirectory is invisible to them by construction, so nothing needs to change
in the validators themselves.

Kept (not deleted) so the shape isn't lost if the feature is eventually built.
Move a file back to the parent `event-schemas/` directory only once a real
producer exists and its `event_type` literal has been confirmed against the
producer's source (see `../README.md` section 4 "How to add a new event").

| File | Why it's here |
|------|----------------|
| `rewards.level.achieved.v1.json` | No `PublishLevelAchieved` in alebrije-mod-rewards-go; the real system uses tiers (`rewards.tier_changed`), not levels. |
| `rewards.redemption.confirmed.v1.json` | No separate confirmation event; redemptions are confirmed via `rewards.redeemed`. |

Moved 2026-07-03 (DEBT-AUDIT-20260701-019-rewards, option A2).
