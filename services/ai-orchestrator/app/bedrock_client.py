"""
bedrock_client.py — LangChain ChatBedrock wrapper (replaces raw boto3 call).

Routes all inference through langchain_aws.ChatBedrock so LangSmith can
trace every invocation automatically via the LANGSMITH_API_KEY /
LANGSMITH_TRACING env vars loaded by Docker Compose.

Per D-060: real Bedrock InvokeModel authorized from W2 onward as an
explicit exception to D-050 (AWS deferral). AWS *managed services*
(Knowledge Bases for Bedrock, Agents-for-Bedrock, OpenSearch Managed)
remain deferred to W5 — this file is InvokeModel only.

⚠ DELIBERATE: brownfield-debt items preserved across this Bedrock wiring:
  - Item 4 — caller endpoints still return raw dicts; no Pydantic
    response_model on /draft-foia-request, /draft-amendment, /answer-qa,
    or /eval/ssdd-draft.
  - Item 5 — legacy_chain.py still in place; 3 endpoints below thread
    through draft_with_legacy_chain (Drafting Wizard via /draft-foia-request,
    Amendment Editor via /draft-amendment, notification-copy via
    Notifier.cparWindowOpened upstream — invoked by Spring side).
  - Item 6 — no correlation-id forwarded into the Bedrock InvokeModel call.
  - Item 7 — pinecone-client still in requirements.txt; no `import pinecone`
    in this module.

Stub fallback: if ChatBedrock cannot initialise (no AWS credentials on a
dev laptop), invoke_model returns a stub response shaped like the real one
so the rest of the stack still flows.
"""
from __future__ import annotations

import logging
import os
from typing import Any

try:
    from langchain_aws import ChatBedrock
    from langchain_core.messages import HumanMessage, SystemMessage
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    _LANGCHAIN_AWS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _LANGCHAIN_AWS_AVAILABLE = False

log = logging.getLogger("ai-orchestrator.bedrock")

BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "anthropic.claude-3-7-sonnet-20250219-v1:0",
)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


_chat_model = None


def _get_chat_model(max_tokens: int, temperature: float) -> "ChatBedrock | None":
    if not _LANGCHAIN_AWS_AVAILABLE:
        return None
    try:
        return ChatBedrock(
            model_id=BEDROCK_MODEL_ID,
            region_name=AWS_REGION,
            model_kwargs={"max_tokens": max_tokens, "temperature": temperature},
        )
    except Exception as exc:
        log.warning("ChatBedrock init failed: %s", exc)
        return None


def invoke_model(prompt: str, *, system: str | None = None,
                  max_tokens: int = 1024,
                  temperature: float = 0.2) -> dict[str, Any]:
    """
    Invoke Anthropic Claude via Bedrock, routed through ChatBedrock so
    LangSmith traces every call automatically.

    Returns a dict with keys:
      - body: the model's text response (or stub)
      - model: Bedrock model id
      - region: AWS region
      - stub: True if returned the stub fallback

    ⚠ Item 4 — return shape NOT Pydantic-validated.
    ⚠ Item 6 — no correlation-id forwarded.
    """
    llm = _get_chat_model(max_tokens, temperature)
    if llm is None:
        log.info("bedrock stub-fallback (langchain-aws unavailable)")
        return _stub(prompt)

    messages = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))

    try:
        response = llm.invoke(messages)
        return {
            "body": response.content,
            "model": BEDROCK_MODEL_ID,
            "region": AWS_REGION,
            "stub": False,
        }
    except (NoCredentialsError, BotoCoreError, ClientError) as exc:
        log.warning("ChatBedrock invoke failed (%s); returning stub", exc)
        return _stub(prompt)
    except Exception as exc:
        log.warning("ChatBedrock invoke failed (%s); returning stub", exc)
        return _stub(prompt)


def _stub(prompt: str) -> dict[str, Any]:
    return {
        "body": f"[stub] would-Bedrock-respond to: {prompt[:80]}",
        "model": BEDROCK_MODEL_ID,
        "region": AWS_REGION,
        "stub": True,
    }
