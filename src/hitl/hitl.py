"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 11: Confidence Router
  TODO 12: Design 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# TODO 11: Implement ConfidenceRouter
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )

        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence",
                priority="low",
                requires_human=False,
            )

        if confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence — needs review",
                priority="normal",
                requires_human=True,
            )

        return RoutingDecision(
            action="escalate",
            confidence=confidence,
            reason="Low confidence — escalating",
            priority="high",
            requires_human=True,
        )


# ============================================================
# TODO 12: Design 3 HITL decision points + a review lifecycle
#
# For each decision point, define:
# - trigger: What condition activates this HITL check?
# - hitl_model: Which model? (human-in-the-loop, human-on-the-loop,
#   human-as-tiebreaker)
# - context_needed: What info does the human reviewer need?
# - example: A concrete scenario
# - approval_path: What approve/reject/timeout decision is recorded?
# - audit_fields: Which correlation ID, intent and proposed action/diff are logged?
#
# Think about real banking scenarios where human judgment is critical.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "High-value money transfer approval",
        "trigger": (
            "Agent proposes a transfer_money action above a value threshold "
            "(e.g. > 20,000,000 VND) or to a new/never-used beneficiary account."
        ),
        "hitl_model": "human-in-the-loop",
        "context_needed": (
            "Source account, destination account, amount, currency, stated intent "
            "from the conversation, beneficiary history (new vs known), and the "
            "raw user message that triggered the request."
        ),
        "example": (
            "Customer chats: 'Transfer 50,000,000 VND to account 0123456789 at "
            "Vietcombank.' Agent drafts the transfer but does not execute it — it "
            "is queued with correlation_id, amount and destination for a bank "
            "reviewer to approve before any money moves."
        ),
        "approval_path": (
            "approve: reviewer confirms identity/intent match, action executes and "
            "audit log records reviewer_id + approval_id. reject: action is "
            "cancelled, customer is notified with a reason. timeout (e.g. no "
            "decision in 15 min): request fails closed (not executed) and is "
            "escalated to a supervisor queue."
        ),
        "audit_fields": (
            "correlation_id, user_id, action=transfer_money, destination account, "
            "amount/payload diff (before vs proposed), reviewer_id, decision "
            "(approve/reject/timeout), decision_timestamp, approval_id."
        ),
    },
    {
        "id": 2,
        "name": "Guardrail-blocked request needing manual override review",
        "trigger": (
            "Input/output guardrail or LLM-as-Judge blocks a request that the "
            "monitoring layer flags as a possible false positive (e.g. block rate "
            "spikes for a topic, or a legitimate-looking banking question is "
            "blocked repeatedly by the same user)."
        ),
        "hitl_model": "human-on-the-loop",
        "context_needed": (
            "Original user message, which layer blocked it and why (matched "
            "pattern/judge verdict), the canned refusal sent to the user, and "
            "recent block-rate metrics for that user/topic."
        ),
        "example": (
            "A customer repeatedly asks about 'joint account password reset' and "
            "gets blocked by the PII/secret-pattern filter because it contains "
            "the word 'password'. A reviewer inspects the queued block log, sees "
            "it's benign, and can whitelist that phrasing or manually answer."
        ),
        "approval_path": (
            "approve (override): the reviewer manually sends a safe answer to the "
            "customer and logs the override. reject: the block stands, no "
            "customer-facing change. timeout: block stands by default (fail "
            "closed) — the reviewer queue is a monitoring/on-the-loop check, not "
            "a live gate, so no live transaction is waiting on it."
        ),
        "audit_fields": (
            "correlation_id, user_id, blocking layer, matched pattern/judge "
            "verdict, reviewer_id, override decision, override justification, "
            "decision_timestamp."
        ),
    },
    {
        "id": 3,
        "name": "Irreversible account action (close account / change password)",
        "trigger": (
            "Agent proposes any action in HIGH_RISK_ACTIONS that is destructive or "
            "hard to reverse: close_account, change_password, delete_data, "
            "update_personal_info."
        ),
        "hitl_model": "human-as-tiebreaker",
        "context_needed": (
            "Full intent summary, diff of what would change (e.g. old vs new "
            "phone/email on file, or account status before/after), identity "
            "verification signals already collected, and the ConfidenceRouter "
            "score that triggered escalation."
        ),
        "example": (
            "Customer asks the assistant to close their account entirely. The "
            "agent drafts the close_account request but ConfidenceRouter forces "
            "escalate=True regardless of confidence; a human agent verifies "
            "identity and reviews the diff (account status: active -> closed) "
            "before anything is executed."
        ),
        "approval_path": (
            "approve: reviewer confirms identity and intent, action executes, "
            "approval_id recorded and required by authorize_action() before the "
            "sink call. reject: action cancelled, customer notified, reason "
            "logged. timeout: fail closed — action never executes without an "
            "explicit human approval_id (see agents/security_boundary.py "
            "authorize_action)."
        ),
        "audit_fields": (
            "correlation_id, user_id, action type, before/after diff, "
            "reviewer_id, approval_id (format HITL-XXXXXXXX), decision "
            "(approve/reject/timeout), decision_timestamp."
        ),
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
