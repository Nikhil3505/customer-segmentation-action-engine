"""
Policy and Guardrail Evaluation for Action Recommendations.
Enforces customer consent rules, support friction suppression, and frequency caps.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

from src.models.entities import ConsentStatus, DeliveryStatus


class GuardrailPolicyEngine:
    """
    Evaluates policy guardrails before any action can be dispatched to a customer.
    """

    def __init__(self, cooldown_days_default: int = 14):
        self.cooldown_days_default = cooldown_days_default

    def evaluate_action_eligibility(
        self,
        customer_id: str,
        action: Dict[str, Any],
        consents: List[Dict[str, Any]],
        support_cases: List[Dict[str, Any]],
        prior_outcomes: List[Dict[str, Any]],
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Executes policy checks in sequence:
        1. Consent Guardrail
        2. Critical Support Ticket Suppression
        3. Frequency Capping / Cooldown Guardrail
        """
        now = current_time or datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)
        supp_rules = action.get("suppression_rules_json", "{}")
        if isinstance(supp_rules, str):
            import json
            supp_rules = json.loads(supp_rules)

        required_consent = supp_rules.get("required_consent")
        suppress_if_critical = supp_rules.get("suppress_if_open_critical", False)
        cooldown_days = supp_rules.get("cooldown_days", self.cooldown_days_default)

        guardrails_checked = []
        is_suppressed = False
        suppression_reason = None
        decision_details = []

        # 1. Consent Guardrail
        if required_consent:
            matching_consent = next(
                (c for c in consents if c["customer_id"] == customer_id and c["channel"] == required_consent),
                None
            )
            if not matching_consent or matching_consent.get("status") in (ConsentStatus.OPTED_OUT.value, ConsentStatus.REVOKED.value):
                status_str = matching_consent.get("status", "NO_RECORD") if matching_consent else "NO_RECORD"
                is_suppressed = True
                suppression_reason = "CONSENT_REVOKED"
                decision_details.append(f"Consent check FAILED: Channel {required_consent} has status {status_str}.")
                guardrails_checked.append({"guardrail": "CONSENT_VERIFICATION", "status": "FAIL", "reason": suppression_reason})
            else:
                decision_details.append(f"Consent check PASSED: Channel {required_consent} has status OPTED_IN.")
                guardrails_checked.append({"guardrail": "CONSENT_VERIFICATION", "status": "PASS"})
        else:
            decision_details.append("Consent check SKIPPED: Internal/Service action does not require marketing consent.")
            guardrails_checked.append({"guardrail": "CONSENT_VERIFICATION", "status": "EXEMPT"})

        # 2. Open Critical Support Ticket Guardrail
        if not is_suppressed and suppress_if_critical:
            open_critical_ticket = any(
                c["customer_id"] == customer_id
                and c.get("priority") == "CRITICAL"
                and c.get("status") in ("OPEN", "ESCALATED")
                for c in support_cases
            )
            if open_critical_ticket:
                is_suppressed = True
                suppression_reason = "OPEN_CRITICAL_SUPPORT_CASE"
                decision_details.append("Support guardrail TRIGGERED: Suppressed due to active critical support case.")
                guardrails_checked.append({"guardrail": "SUPPORT_FRICTION_CHECK", "status": "FAIL", "reason": suppression_reason})
            else:
                decision_details.append("Support guardrail PASSED: No active critical support tickets found.")
                guardrails_checked.append({"guardrail": "SUPPORT_FRICTION_CHECK", "status": "PASS"})

        # 3. Frequency Capping / Cooldown Guardrail
        if not is_suppressed:
            recent_dispatches = [
                o for o in prior_outcomes
                if o["customer_id"] == customer_id
                and o.get("action_id") == action["action_id"]
                and o.get("delivery_status") == DeliveryStatus.DELIVERED.value
            ]
            if recent_dispatches:
                latest_disp_dt = max(datetime.fromisoformat(o["execution_timestamp"]) for o in recent_dispatches)
                days_since = (now - latest_disp_dt).days
                if days_since < cooldown_days:
                    is_suppressed = True
                    suppression_reason = "COOLDOWN_ACTIVE"
                    decision_details.append(
                        f"Frequency cap TRIGGERED: Action dispatched {days_since}d ago, within {cooldown_days}d cooldown."
                    )
                    guardrails_checked.append({"guardrail": "FREQUENCY_CAPPING", "status": "FAIL", "reason": suppression_reason})
                else:
                    decision_details.append(f"Frequency cap PASSED: Last dispatch was {days_since}d ago (>= {cooldown_days}d).")
                    guardrails_checked.append({"guardrail": "FREQUENCY_CAPPING", "status": "PASS"})
            else:
                decision_details.append("Frequency cap PASSED: No prior dispatches in cooldown window.")
                guardrails_checked.append({"guardrail": "FREQUENCY_CAPPING", "status": "PASS"})

        final_decision = "SUPPRESS" if is_suppressed else "DISPATCH"
        return {
            "customer_id": customer_id,
            "action_id": action["action_id"],
            "decision": final_decision,
            "is_suppressed": is_suppressed,
            "suppression_reason": suppression_reason,
            "decision_details": decision_details,
            "guardrails_checked": guardrails_checked,
        }
