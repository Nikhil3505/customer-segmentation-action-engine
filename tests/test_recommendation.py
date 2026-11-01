"""
Unit tests for Recommendation Policy Engine, Consent Guardrails, and Suppression Rules.
"""

import json
from decimal import Decimal
from datetime import datetime, timezone
import pytest

from src.recommendation.guardrails import GuardrailPolicyEngine
from src.recommendation.engine import RecommendationEngine


@pytest.fixture
def sample_action():
    return {
        "action_id": "ACTN-2026-000001",
        "action_code": "VIP_CONCIERGE_REWARD",
        "action_name": "VIP Concierge",
        "target_segment_code": "VIP_LOYALIST",
        "channel": "EMAIL",
        "suppression_rules_json": json.dumps({
            "required_consent": "EMAIL_MARKETING",
            "cooldown_days": 30,
            "suppress_if_open_critical": True,
        }),
        "is_active": True,
    }


def test_consent_revocation_suppresses_marketing_action(sample_action):
    engine = GuardrailPolicyEngine()
    customer_id = "CUS-000001"
    consents = [
        {
            "customer_id": customer_id,
            "channel": "EMAIL_MARKETING",
            "status": "REVOKED",
        }
    ]
    res = engine.evaluate_action_eligibility(
        customer_id=customer_id,
        action=sample_action,
        consents=consents,
        support_cases=[],
        prior_outcomes=[],
    )

    assert res["decision"] == "SUPPRESS"
    assert res["is_suppressed"] is True
    assert res["suppression_reason"] == "CONSENT_REVOKED"


def test_open_critical_ticket_suppresses_marketing(sample_action):
    engine = GuardrailPolicyEngine()
    customer_id = "CUS-000002"
    consents = [
        {
            "customer_id": customer_id,
            "channel": "EMAIL_MARKETING",
            "status": "OPTED_IN",
        }
    ]
    cases = [
        {
            "customer_id": customer_id,
            "priority": "CRITICAL",
            "status": "OPEN",
        }
    ]
    res = engine.evaluate_action_eligibility(
        customer_id=customer_id,
        action=sample_action,
        consents=consents,
        support_cases=cases,
        prior_outcomes=[],
    )

    assert res["decision"] == "SUPPRESS"
    assert res["is_suppressed"] is True
    assert res["suppression_reason"] == "OPEN_CRITICAL_SUPPORT_CASE"


def test_cooldown_frequency_capping(sample_action):
    engine = GuardrailPolicyEngine()
    customer_id = "CUS-000003"
    consents = [
        {
            "customer_id": customer_id,
            "channel": "EMAIL_MARKETING",
            "status": "OPTED_IN",
        }
    ]
    prior = [
        {
            "customer_id": customer_id,
            "action_id": sample_action["action_id"],
            "delivery_status": "DELIVERED",
            "execution_timestamp": "2026-10-25T12:00:00+00:00",  # 6 days ago (cooldown is 30)
        }
    ]
    res = engine.evaluate_action_eligibility(
        customer_id=customer_id,
        action=sample_action,
        consents=consents,
        support_cases=[],
        prior_outcomes=prior,
        current_time=datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc),
    )

    assert res["decision"] == "SUPPRESS"
    assert res["suppression_reason"] == "COOLDOWN_ACTIVE"
