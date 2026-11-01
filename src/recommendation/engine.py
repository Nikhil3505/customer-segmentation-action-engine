"""
Action Recommendation Engine.
Matches customer segment profiles to candidate actions, enforces policy guardrails,
records recommendations and dispatches, and audits for policy violations.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional

from src.models.entities import DeliveryStatus, ConsentStatus
from src.recommendation.guardrails import GuardrailPolicyEngine


class RecommendationEngine:
    """
    Orchestrates end-to-end action selection, guardrail validation, and outcome tracking.
    """

    def __init__(
        self,
        action_catalog: List[Dict[str, Any]],
        segment_rules: List[Dict[str, Any]],
        reference_date: Optional[datetime] = None,
    ):
        self.actions = action_catalog
        self.rules = segment_rules
        self.reference_date = reference_date or datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)
        self.policy_engine = GuardrailPolicyEngine()

    def recommend_for_customer(
        self,
        customer_id: str,
        segment_code: str,
        consents: List[Dict[str, Any]],
        support_cases: List[Dict[str, Any]],
        prior_outcomes: List[Dict[str, Any]],
        recommendation_index: int = 1,
    ) -> Dict[str, Any]:
        """
        Determines the Next Best Action for a customer and evaluates guardrails.
        """
        # Find matching action in catalog
        candidate_actions = [a for a in self.actions if a["target_segment_code"] == segment_code and a.get("is_active", True)]
        if not candidate_actions:
            candidate_actions = [a for a in self.actions if a.get("is_active", True)]

        selected_action = candidate_actions[0] if candidate_actions else None
        if not selected_action:
            raise ValueError(f"No active actions found for segment code {segment_code}")

        rec_id = f"REC-2026-{recommendation_index:06d}"
        policy_eval = self.policy_engine.evaluate_action_eligibility(
            customer_id=customer_id,
            action=selected_action,
            consents=consents,
            support_cases=support_cases,
            prior_outcomes=prior_outcomes,
            current_time=self.reference_date,
        )

        return {
            "recommendation_id": rec_id,
            "customer_id": customer_id,
            "segment_code": segment_code,
            "action": selected_action,
            "decision": policy_eval["decision"],
            "is_suppressed": policy_eval["is_suppressed"],
            "suppression_reason": policy_eval["suppression_reason"],
            "guardrails_checked": policy_eval["guardrails_checked"],
            "decision_details": policy_eval["decision_details"],
            "created_at": self.reference_date.isoformat(),
        }

    def audit_consent_violations(
        self,
        outcomes: List[Dict[str, Any]],
        consents: List[Dict[str, Any]],
        action_catalog: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Audits all executed outcomes against customer consent records to detect violations.
        Flags any marketing communication DELIVERED to a customer with REVOKED/OPTED_OUT status.
        """
        import json
        actions_by_id = {a["action_id"]: a for a in action_catalog}
        consents_by_cust: Dict[str, Dict[str, str]] = {}
        for c in consents:
            consents_by_cust.setdefault(c["customer_id"], {})[c["channel"]] = c["status"]

        violations = []
        for o in outcomes:
            if o.get("delivery_status") == DeliveryStatus.DELIVERED.value:
                action = actions_by_id.get(o["action_id"])
                if not action:
                    continue
                rules = action.get("suppression_rules_json", "{}")
                if isinstance(rules, str):
                    rules = json.loads(rules)
                req_consent = rules.get("required_consent")
                if req_consent:
                    cust_con = consents_by_cust.get(o["customer_id"], {}).get(req_consent)
                    if cust_con in (ConsentStatus.OPTED_OUT.value, ConsentStatus.REVOKED.value):
                        violations.append({
                            "outcome_id": o["outcome_id"],
                            "customer_id": o["customer_id"],
                            "action_id": o["action_id"],
                            "action_name": action["action_name"],
                            "required_channel": req_consent,
                            "consent_status": cust_con,
                            "description": (
                                f"Consent Violation: Action {action['action_name']} ({o['action_id']}) "
                                f"was DELIVERED to customer {o['customer_id']} despite channel {req_consent} "
                                f"having status {cust_con}."
                            ),
                        })

        return violations

    def audit_outcome_misattributions(
        self,
        outcomes: List[Dict[str, Any]],
        action_catalog: List[Dict[str, Any]],
        memberships: List[Dict[str, Any]],
        segment_rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Audits outcomes to detect conversions attributed to an action that does not match
        the customer's legitimate segment or campaign intent.
        """
        rule_to_code = {r["rule_id"]: r["segment_code"] for r in segment_rules}
        cust_segments = {m["customer_id"]: rule_to_code.get(m["rule_id"]) for m in memberships}
        action_map = {a["action_id"]: a for a in action_catalog}

        misattributions = []
        for o in outcomes:
            rev = o.get("conversion_revenue")
            if rev is not None and Decimal(str(rev)) > Decimal("0.00"):
                action = action_map.get(o["action_id"])
                cust_seg = cust_segments.get(o["customer_id"])
                if action and cust_seg and action["target_segment_code"] != cust_seg:
                    misattributions.append({
                        "outcome_id": o["outcome_id"],
                        "customer_id": o["customer_id"],
                        "action_id": o["action_id"],
                        "attributed_revenue": float(rev),
                        "action_target_segment": action["target_segment_code"],
                        "customer_actual_segment": cust_seg,
                        "description": (
                            f"Outcome Misattribution: Conversion revenue ${rev} for customer {o['customer_id']} "
                            f"(segment {cust_seg}) was attributed to action {action['action_code']} "
                            f"(targeted for {action['target_segment_code']})."
                        ),
                    })

        return misattributions
