"""
Edge-case and deliberate anomaly injector for Customer Intelligence Platform.
Injects the 4 required negative scenarios with full traceability and separate ground-truth logging:
1. Customer included in conflicting exclusive segments.
2. Action violates consent (outreach delivered despite revoked/opted-out consent).
3. Return not netted from spend (gross order total used instead of net spend).
4. Outcome attributed to wrong action or wrong customer.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
import copy

from src.models.entities import (
    AnomalyType,
    GroundTruthAnomaly,
    SegmentMembership,
    ActionOutcome,
    Order,
    ConsentStatus,
    DeliveryStatus,
)


class EdgeCaseInjector:
    """
    Manages deliberate injection of domain edge cases into baseline valid data.
    Maintains complete isolation of ground-truth labels from input features.
    """

    def __init__(self, anomaly_rate: float = 0.02, fixed_timestamp: Optional[datetime] = None):
        self.anomaly_rate = anomaly_rate
        self.ground_truth_records: List[GroundTruthAnomaly] = []
        self._anomaly_counter = 0
        self.created_at = fixed_timestamp or datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)

    def _next_anomaly_id(self) -> str:
        self._anomaly_counter += 1
        return f"ANOM-{self._anomaly_counter:06d}"

    def inject_conflicting_exclusive_segments(
        self,
        memberships: List[Dict[str, Any]],
        segment_rules: List[Dict[str, Any]],
        target_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Edge Case 1: Customer included in conflicting exclusive segments.
        E.g., Customer legitimately in VIP_LOYALIST is also given an active membership in AT_RISK_DORMANT.
        """
        exclusive_rules = {r["segment_code"]: r["rule_id"] for r in segment_rules if r["is_exclusive"]}
        if "VIP_LOYALIST" not in exclusive_rules or "AT_RISK_DORMANT" not in exclusive_rules:
            return memberships

        vip_rule_id = exclusive_rules["VIP_LOYALIST"]
        dormant_rule_id = exclusive_rules["AT_RISK_DORMANT"]

        # Find customers with VIP membership
        vip_custs = [m for m in memberships if m["rule_id"] == vip_rule_id]
        injected = 0

        for m in vip_custs:
            if injected >= target_count:
                break
            cust_id = m["customer_id"]
            # Create a conflicting membership in AT_RISK_DORMANT
            conflicting_mem = copy.deepcopy(m)
            conflicting_mem["membership_id"] = f"MEM-{dormant_rule_id}-{cust_id}"
            conflicting_mem["rule_id"] = dormant_rule_id
            conflicting_mem["explainability_notes"] = (
                "[ANOMALY INJECTED] Conflicting exclusive segment membership assigned concurrently."
            )
            memberships.append(conflicting_mem)

            anomaly_id = self._next_anomaly_id()
            self.ground_truth_records.append(
                GroundTruthAnomaly(
                    anomaly_id=anomaly_id,
                    issue_type=AnomalyType.CONFLICTING_EXCLUSIVE_SEGMENTS,
                    entity_type="SegmentMembership",
                    entity_id=conflicting_mem["membership_id"],
                    customer_id=cust_id,
                    injected_details=(
                        f"Customer {cust_id} concurrently assigned to exclusive segments "
                        f"VIP_LOYALIST ({vip_rule_id}) and AT_RISK_DORMANT ({dormant_rule_id})."
                    ),
                    expected_behavior=(
                        "Exclusive segments must be mutually exclusive. Priority rank or rule resolution "
                        "must prevent dual active assignment."
                    ),
                    created_at=self.created_at,
                )
            )
            injected += 1

        return memberships

    def inject_action_violates_consent(
        self,
        outcomes: List[Dict[str, Any]],
        consents: List[Dict[str, Any]],
        action_catalog: List[Dict[str, Any]],
        target_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Edge Case 2: Action violates consent.
        An action is dispatched and marked DELIVERED even though customer has REVOKED or OPTED_OUT consent.
        """
        revoked_email_customers = {
            c["customer_id"]
            for c in consents
            if c["channel"] == "EMAIL_MARKETING" and c["status"] in ("REVOKED", "OPTED_OUT")
        }

        injected = 0
        for outcome in outcomes:
            if injected >= target_count:
                break
            cust_id = outcome["customer_id"]
            if cust_id in revoked_email_customers:
                outcome["delivery_status"] = DeliveryStatus.DELIVERED.value
                outcome["suppression_reason"] = None
                outcome["notes"] = "[ANOMALY INJECTED] Action dispatched despite explicit consent revocation."

                anomaly_id = self._next_anomaly_id()
                self.ground_truth_records.append(
                    GroundTruthAnomaly(
                        anomaly_id=anomaly_id,
                        issue_type=AnomalyType.ACTION_VIOLATES_CONSENT,
                        entity_type="ActionOutcome",
                        entity_id=outcome["outcome_id"],
                        customer_id=cust_id,
                        injected_details=(
                            f"Action {outcome['action_id']} dispatched (DELIVERED) to customer {cust_id} "
                            f"whose EMAIL_MARKETING consent is REVOKED/OPTED_OUT."
                        ),
                        expected_behavior=(
                            "Marketing action must be SUPPRESSED with suppression_reason='CONSENT_REVOKED'."
                        ),
                        created_at=self.created_at,
                    )
                )
                injected += 1

        return outcomes

    def inject_return_not_netted_from_spend(
        self,
        orders: List[Dict[str, Any]],
        target_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Edge Case 3: Return not netted from spend.
        Order has a significant refund, but net_amount is left equal to gross total_amount.
        """
        injected = 0
        for order in orders:
            if injected >= target_count:
                break
            refund = Decimal(str(order["refund_amount"]))
            total = Decimal(str(order["total_amount"]))
            if refund > Decimal("50.00") and order["net_amount"] != total:
                order["net_amount"] = total
                order["payment_status"] = "PAID"

                anomaly_id = self._next_anomaly_id()
                self.ground_truth_records.append(
                    GroundTruthAnomaly(
                        anomaly_id=anomaly_id,
                        issue_type=AnomalyType.RETURN_NOT_NETTED_FROM_SPEND,
                        entity_type="Order",
                        entity_id=order["order_id"],
                        customer_id=order["customer_id"],
                        injected_details=(
                            f"Order {order['order_id']} has refund_amount={refund}, but net_amount "
                            f"was erroneously calculated as {order['net_amount']} (equal to total_amount {total}) "
                            f"without netting refund."
                        ),
                        expected_behavior=(
                            f"net_amount must strictly equal total_amount ({total}) minus refund_amount ({refund}) = {total - refund}."
                        ),
                        created_at=self.created_at,
                    )
                )
                injected += 1

        return orders

    def inject_outcome_attributed_to_wrong_action(
        self,
        outcomes: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        target_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Edge Case 4: Outcome attributed to wrong action or wrong customer.
        Conversion revenue from an order is misattributed to an unrelated action or customer.
        """
        converted_outcomes = [o for o in outcomes if o.get("conversion_revenue") and Decimal(str(o["conversion_revenue"])) > Decimal("0.00")]
        if len(converted_outcomes) < 2 or len(actions) < 2:
            return outcomes

        injected = 0
        action_ids = [a["action_id"] for a in actions]

        for outcome in converted_outcomes:
            if injected >= target_count:
                break
            original_action_id = outcome["action_id"]
            wrong_action_id = next((aid for aid in action_ids if aid != original_action_id), action_ids[0])
            outcome["action_id"] = wrong_action_id
            outcome["notes"] = f"[ANOMALY INJECTED] Revenue misattributed from {original_action_id} to {wrong_action_id}."

            anomaly_id = self._next_anomaly_id()
            self.ground_truth_records.append(
                GroundTruthAnomaly(
                    anomaly_id=anomaly_id,
                    issue_type=AnomalyType.OUTCOME_ATTRIBUTED_TO_WRONG_ACTION,
                    entity_type="ActionOutcome",
                    entity_id=outcome["outcome_id"],
                    customer_id=outcome["customer_id"],
                    injected_details=(
                        f"Outcome {outcome['outcome_id']} for customer {outcome['customer_id']} with "
                        f"revenue ${outcome['conversion_revenue']} was misattributed to action {wrong_action_id} "
                        f"instead of genuine campaign {original_action_id}."
                    ),
                    expected_behavior=(
                        "Outcome must attribute conversions only to the specific recommended and dispatched action."
                    ),
                    created_at=self.created_at,
                )
            )
            injected += 1

        return outcomes

    def get_ground_truth(self) -> List[GroundTruthAnomaly]:
        """Return all logged ground truth anomalies."""
        return self.ground_truth_records
