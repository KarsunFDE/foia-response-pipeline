"""
Pair-unique debt locked-failing test — ai-bedrock-no-cost-limit
(D-059, Cohort #1 Pair 3 — foia-response-pipeline).

Convention: assertion = what-true-after-modernization.

While debt is locked (current state):
  app/cost_guard.py:BedrockCostGuard.check() is a no-op stub. 1000
  successive calls for the same tenant never raise CostLimitExceeded.
  The locked test fires 1000 calls and asserts at least one
  CostLimitExceeded raise — currently 0 raises → fails.

After W5 fix:
  - check() is Redis-backed with per-tenant LIMITS
  - daily-spend counter is incremented per call
  - on ceiling breach, raises CostLimitExceeded
  - Test PASSES (>=1 raise observed in 1000 calls).

FOIA-domain rationale: adversarial requester uploads multi-thousand-page
responsive-document → redaction-proposer fans out → without ceiling,
single tenant drains Karsun-owned Bedrock account (D-050 single shared
AWS account in W5).
"""
from __future__ import annotations

import asyncio

import pytest


@pytest.mark.brownfield_debt
@pytest.mark.brownfield_debt_pair_unique_ai_bedrock_no_cost_limit
def test_tenant_bedrock_cost_capped_DEBT_LOCKED() -> None:
    from app.cost_guard import BedrockCostGuard, CostLimitExceeded

    guard = BedrockCostGuard()

    async def hammer() -> bool:
        for _ in range(1000):
            try:
                # Simulate a 2K-token redaction-proposer call.
                await guard.check(tenant="agency-foia-1", est_tokens=2000)
            except CostLimitExceeded:
                return True
        return False

    triggered = asyncio.get_event_loop().run_until_complete(hammer())

    # EXPECTED-AFTER-FIX: somewhere in 1000 successive calls the per-tenant
    # ceiling is breached → CostLimitExceeded raised. Pre-fix: check() is a
    # no-op and returns silently every time.
    assert triggered, (
        "Pair-unique debt ai-bedrock-no-cost-limit: BedrockCostGuard.check "
        "must raise CostLimitExceeded once a tenant exceeds its daily "
        "Bedrock cost ceiling. Currently 1000 calls all pass — a single "
        "tenant can drain the Karsun-paid Bedrock account (D-050). Fix "
        "lands W5 (AIOps cost governance + HITL #7 authority boundary)."
    )
