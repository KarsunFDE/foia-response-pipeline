"""
cost_guard.py — placeholder seam for per-tenant Bedrock cost ceiling.

⚠ DELIBERATE PAIR-UNIQUE BROWNFIELD DEBT — ai-bedrock-no-cost-limit ⚠

Per D-059 Cohort #1 Pair 3 (foia-response-pipeline) injection from
skills/pair-brownfield-generator/references/pair-unique-debt-pool.yml.

The cohort finds this file EXISTING but with no implementation — the
`BedrockCostGuard.check()` coroutine is a no-op stub. Every Bedrock
InvokeModel call in app/main.py + app/foia_request_service.py bypasses
any per-tenant ceiling.

FOIA-domain risk: an adversarial requester triggers a multi-thousand-page
responsive-document upload, which fans out to redaction-proposer
InvokeModel calls. With no cost ceiling, a single tenant can drain the
Karsun-owned Bedrock account (D-050 — single shared AWS account in W5).
HITL #7 (W5 Wed AIOps auto-remediation authority) is the cohort's
remediation surface.

Fix (lands W5 — AIOps cost governance + HITL #7 authority boundary):

    class BedrockCostGuard:
        async def check(self, tenant: str, est_tokens: int):
            spent = await redis.get(f"bedrock:cost:{tenant}:daily")
            if spent + estimate(est_tokens) > LIMITS[tenant]:
                raise CostLimitExceeded(tenant)

The fix lives in cost_guard.py with real Redis-backed counters and
per-tenant LIMITS dict; middleware wires it into the FastAPI request
chain via a dependency that runs before every Bedrock-bound endpoint.

Cohort task in W5:
  - Wire BedrockCostGuard.check() into app/main.py + foia_request_service
  - Add per-tenant LIMITS dict (Redis-backed, 24h sliding window)
  - Surface CostLimitExceeded as HTTP 429 to the caller
  - HITL #7: instructor + pair agree on per-tenant ceiling before W5 Wed
    auto-remediation drill
"""
from __future__ import annotations

from typing import Optional


class CostLimitExceeded(RuntimeError):
    """Raised when a tenant exceeds its daily Bedrock cost ceiling."""

    def __init__(self, tenant: str, est_cost: Optional[float] = None) -> None:
        super().__init__(f"Bedrock cost ceiling exceeded for tenant={tenant}")
        self.tenant = tenant
        self.est_cost = est_cost


class BedrockCostGuard:
    """
    Per-tenant Bedrock cost ceiling. Stub — pair-unique debt.

    ⚠ Bug: every check() returns silently. No tenant is ever rate-limited.
    """

    async def check(self, tenant: str, est_tokens: int = 0) -> None:
        """
        Verify the tenant has budget for the requested call.

        Currently a no-op. Should be Redis-backed with per-tenant LIMITS.
        """
        # ⚠ pair-unique debt ai-bedrock-no-cost-limit:
        # no enforcement — returns silently. Stub for cohort to implement W5.
        return None
