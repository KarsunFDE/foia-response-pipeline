"""
Pair-unique debt locked-failing test — obs-error-rethrown-stack-lost
(D-059, Cohort #1 Pair 3 — foia-response-pipeline).

Convention: assertion = what-true-after-modernization.

While debt is locked (current state):
  app/foia_request_service.py:draft_for_review_with_failure() catches a
  botocore ClientError and raises RuntimeError("AI call failed") WITHOUT
  `from e`. The chained `__cause__` is None.

After W5 fix:
  except botocore.exceptions.ClientError as e:
      raise RuntimeError("AI call failed") from e
  → __cause__ is the ClientError, test PASSES.

FOIA-domain rationale: when Bedrock throttles a multi-thousand-page
ResponsivePages redaction batch, the SRE needs to see ThrottlingException
in the chained cause to know to dial concurrency back. Stripping the
cause hides that signal.
"""
from __future__ import annotations

import asyncio
import pytest


@pytest.mark.brownfield_debt
@pytest.mark.brownfield_debt_pair_unique_obs_error_rethrown_stack_lost
def test_ai_error_preserves_cause_DEBT_LOCKED() -> None:
    from app.foia_request_service import draft_for_review_with_failure

    with pytest.raises(RuntimeError) as exc:
        asyncio.get_event_loop().run_until_complete(draft_for_review_with_failure())

    # EXPECTED-AFTER-FIX: __cause__ is the chained ClientError.
    # Pre-fix: __cause__ is None because the catch-and-rethrow used plain `raise`.
    assert exc.value.__cause__ is not None, (
        "Pair-unique debt obs-error-rethrown-stack-lost: "
        "draft_for_review_with_failure must chain its underlying cause via "
        "`raise RuntimeError(...) from e`. Currently __cause__ is None — "
        "original ClientError + stack is invisible to W5 AIOps debugging. "
        "Fix lands W5."
    )
    assert "ClientError" in type(exc.value.__cause__).__name__, (
        "Chained cause must be the original botocore ClientError."
    )
