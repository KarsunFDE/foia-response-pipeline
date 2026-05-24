"""ai-orchestrator app package."""
# Surface pair-unique cost-guard stub so cohort can import directly.
# Pair-unique debt ai-bedrock-no-cost-limit — currently a no-op; cohort
# implements W5 (AIOps cost governance + HITL #7 authority).
from app.cost_guard import BedrockCostGuard, CostLimitExceeded  # noqa: F401
