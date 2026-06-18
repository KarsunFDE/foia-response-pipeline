# Stage 1 — Business Understanding

## Goal
Establish why this migration is happening, what success looks like, and what constraints bound the work.

## Questions to Answer

### Driver
- What is the primary motivation for migrating from Angular to React?
- Is this a full rewrite or an incremental strangler-fig migration?

### Success Criteria
- What does "done" look like? (all views ported, feature parity, performance targets, etc.)
- Are there acceptance tests or stakeholder sign-offs required?

### Constraints
- Hard deadlines or release windows?
- Team members who own specific Angular modules?
- Must the Angular app remain live during migration?

### Risk Tolerance
- Which features are zero-downtime critical?
- What is the rollback plan if a migrated view regresses?

## Outputs
- Agreed migration strategy (big-bang vs. incremental)
- Defined done criteria
- Known constraints logged here for stages 3–6 to reference
