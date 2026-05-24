"""
foia_request_service.py — service-layer wrapper around Bedrock for FOIA-request
drafting flows.

⚠ DELIBERATE PAIR-UNIQUE BROWNFIELD DEBT — obs-error-rethrown-stack-lost ⚠

Per D-059 Cohort #1 Pair 3 (foia-response-pipeline) injection from
skills/pair-brownfield-generator/references/pair-unique-debt-pool.yml.

The service wraps `bedrock_client.invoke_model` for the redaction-proposer
flow but catches the underlying exception and raises a flat
`RuntimeError("AI call failed")` — without `raise ... from e`. The original
`botocore.exceptions.ClientError` (or whatever the underlying cause was) is
lost. AIOps debugging in W5 becomes guess-the-cause.

FOIA-domain context: this service is the seam between the Spring redaction-
review service and the Bedrock-backed redaction-proposer. When Bedrock
throttles (a common shape during multi-thousand-page responsive-document
runs), the original `ThrottlingException` is the signal an SRE needs to
adjust concurrency. Stripping the cause makes that signal invisible.

Fix (lands W5):

    except botocore.exceptions.ClientError as e:
        raise RuntimeError("AI call failed") from e

Cohort sees both the bug and the fix in the W5 AIOps Python-exception-chaining
session.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from app.bedrock_client import invoke_model, BEDROCK_MODEL_ID

log = logging.getLogger(__name__)


async def draft_for_review(prompt: str) -> Dict[str, Any]:
    """
    Draft a redaction-review narrative for a single ResponsivePages excerpt.

    ⚠ Bug: on Bedrock error, rethrows as flat RuntimeError without `from e` —
    original ClientError + stack is lost.
    """
    try:
        result = invoke_model(prompt, model_id=BEDROCK_MODEL_ID)
        return {"draft": result}
    except Exception:
        # ⚠ pair-unique debt obs-error-rethrown-stack-lost:
        # original cause + stack discarded. Should be `raise ... from e`.
        raise RuntimeError("AI call failed")


async def draft_for_review_with_failure() -> Dict[str, Any]:
    """
    Test seam: deliberately surfaces the cause-stripping bug by routing
    through the same `try/except` shape with a forced Bedrock failure.

    Used by the locked-failing test
    `tests/test_error_rethrown_stack_lost_debt.py`.
    """
    try:
        # Simulate the boto3 ClientError shape the cohort sees in W5.
        from botocore.exceptions import ClientError
        raise ClientError(
            error_response={"Error": {"Code": "ThrottlingException", "Message": "rate"}},
            operation_name="InvokeModel",
        )
    except Exception:
        # ⚠ same bug shape as draft_for_review — chained `from e` missing.
        raise RuntimeError("AI call failed")
