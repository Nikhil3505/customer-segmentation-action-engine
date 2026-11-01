"""
Deterministic Synthetic Data Generation Engine for YottaFlex AI challenge.
Produces 11 relational entities with strictly enforced foreign keys, realistic distributions,
deterministic IDs, and reproducible seed behavior.
Supports scalable generation (starter mode vs full 50k customers / 200k orders / 1M events).
"""

import os
import json
import csv
import sqlite3
import random
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional, Tuple

from src.models.entities import (
    Customer,
    Product,
    Order,
    OrderLine,
    EngagementEvent,
    SupportCase,
    Consent,
    SegmentRule,
    SegmentMembership,
    ActionCatalog,
    ActionOutcome,
    LifecycleStage,
    CustomerStatus,
    ProductCategory,
    PaymentStatus,
    FulfillmentStatus,
    EventChannel,
    EventType,
    SupportChannel,
    SupportPriority,
    SupportCategory,
    SupportStatus,
    ConsentChannel,
    ConsentStatus,
    SegmentCode,
    ActionChannel,
    DeliveryStatus,
    EngagementResponse,
)
from src.generator.edge_cases import EdgeCaseInjector


class SyntheticDataGenerator:
    """
    Core synthetic data engine that generates 11 relational entities deterministically.
    """

    def __init__(
        self,
        seed: int = 20261022,
        scale: str = "starter",
        num_customers: Optional[int] = None,
        num_orders: Optional[int] = None,
        num_events: Optional[int] = None,
        inject_anomalies: bool = True,
    ):
        self.seed = seed
        self.scale = scale
        self.rng = random.Random(seed)
        self.inject_anomalies = inject_anomalies
        self.reference_date = datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)

        # Scale parameters
        if scale == "full":
            self.num_customers = num_customers or 50_000
            self.num_orders = num_orders or 200_000
            self.num_events = num_events or 1_000_000
            self.num_cases = 25_000
        else:  # starter mode
            self.num_customers = num_customers or 1_000
            self.num_orders = num_orders or 4_000
            self.num_events = num_events or 20_000
            self.num_cases = 500

        # Memory stores
        self.customers: List[Dict[str, Any]] = []
        self.products: List[Dict[str, Any]] = []
        self.segment_rules: List[Dict[str, Any]] = []
        self.action_catalog: List[Dict[str, Any]] = []
        self.consents: List[Dict[str, Any]] = []
        self.orders: List[Dict[str, Any]] = []
        self.order_lines: List[Dict[str, Any]] = []
        self.engagement_events: List[Dict[str, Any]] = []
        self.support_cases: List[Dict[str, Any]] = []
        self.segment_memberships: List[Dict[str, Any]] = []
        self.action_outcomes: List[Dict[str, Any]] = []

        self.edge_injector = EdgeCaseInjector(fixed_timestamp=self.reference_date)

    def generate_all(self) -> Dict[str, Any]:
        """Generate all 11 core entities in strict dependency order."""
        # 1. Master entities
        self._generate_products()
        self._generate_segment_rules()
        self._generate_action_catalog()
        self._generate_customers()
        self._generate_consents()

        # 2. Transactional and event entities
        self._generate_orders_and_lines()
        self._generate_engagement_events()
        self._generate_support_cases()

        # 3. Derived analytics entities
        self._generate_segment_memberships()
        self._generate_action_outcomes()

        # 4. Inject labeled edge cases if enabled
        if self.inject_anomalies:
            target_anom = 5 if self.scale == "starter" else 20
            self.segment_memberships = self.edge_injector.inject_conflicting_exclusive_segments(
                self.segment_memberships, self.segment_rules, target_count=target_anom
            )
            self.action_outcomes = self.edge_injector.inject_action_violates_consent(
                self.action_outcomes, self.consents, self.action_catalog, target_count=target_anom
            )
            self.orders = self.edge_injector.inject_return_not_netted_from_spend(
                self.orders, target_count=target_anom
            )
            self.action_outcomes = self.edge_injector.inject_outcome_attributed_to_wrong_action(
                self.action_outcomes, self.action_catalog, target_count=target_anom
            )

        return {
            "customers": self.customers,
            "products": self.products,
            "orders": self.orders,
            "order_lines": self.order_lines,
            "engagement_events": self.engagement_events,
            "support_cases": self.support_cases,
            "consents": self.consents,
            "segment_rules": self.segment_rules,
            "segment_memberships": self.segment_memberships,
            "action_catalog": self.action_catalog,
            "action_outcomes": self.action_outcomes,
            "ground_truth": [g.model_dump() for g in self.edge_injector.get_ground_truth()],
        }

    # --- Master Entity Generators ---

    def _generate_products(self):
        """Generate static master catalog of 20 deterministic products."""
        catalog_defs = [
            ("PRD-000001", "SKU-ELEC-1001", "UltraHD Smart Monitor 32-inch", ProductCategory.ELECTRONICS.value, "Displays", "399.99", "220.00"),
            ("PRD-000002", "SKU-ELEC-1002", "Wireless ANC Headphones Pro", ProductCategory.ELECTRONICS.value, "Audio", "199.99", "95.00"),
            ("PRD-000003", "SKU-ELEC-1003", "Mechanical Ergonomic Keyboard", ProductCategory.ELECTRONICS.value, "Peripherals", "129.99", "55.00"),
            ("PRD-000004", "SKU-ELEC-1004", "Precision Wireless Mouse", ProductCategory.ELECTRONICS.value, "Peripherals", "79.99", "30.00"),
            ("PRD-000005", "SKU-SAAS-2001", "Enterprise Analytics Cloud Annual", ProductCategory.SAAS.value, "Subscriptions", "1200.00", "150.00"),
            ("PRD-000006", "SKU-SAAS-2002", "Pro Workflow Automation Monthly", ProductCategory.SAAS.value, "Subscriptions", "49.99", "8.00"),
            ("PRD-000007", "SKU-SAAS-2003", "AI Copilot Developer Seat Annual", ProductCategory.SAAS.value, "Subscriptions", "240.00", "40.00"),
            ("PRD-000008", "SKU-APP-3001", "Water-Resistant Technical Jacket", ProductCategory.APPAREL.value, "Outerwear", "180.00", "70.00"),
            ("PRD-000009", "SKU-APP-3002", "Merino Wool Commuter Hoodie", ProductCategory.APPAREL.value, "Tops", "110.00", "42.00"),
            ("PRD-000010", "SKU-APP-3003", "Everyday Flex Chino Trousers", ProductCategory.APPAREL.value, "Bottoms", "85.00", "32.00"),
            ("PRD-000011", "SKU-HOME-4001", "Standing Desk Dual-Motor Frame", ProductCategory.HOME.value, "Office Furniture", "450.00", "230.00"),
            ("PRD-000012", "SKU-HOME-4002", "Ergonomic Lumbar Mesh Chair", ProductCategory.HOME.value, "Office Furniture", "320.00", "140.00"),
            ("PRD-000013", "SKU-HOME-4003", "Dimmable LED Monitor Lightbar", ProductCategory.HOME.value, "Lighting", "59.99", "22.00"),
            ("PRD-000014", "SKU-ACC-5001", "USB-C Multiport Thunderbolt Hub", ProductCategory.ACCESSORIES.value, "Adapters", "89.99", "35.00"),
            ("PRD-000015", "SKU-ACC-5002", "Magnetic Vegan Leather Desk Mat", ProductCategory.ACCESSORIES.value, "Desk Mats", "39.99", "12.00"),
            ("PRD-000016", "SKU-ACC-5003", "Braided Fast-Charging Cable 2M", ProductCategory.ACCESSORIES.value, "Cables", "19.99", "4.50"),
            ("PRD-000017", "SKU-ELEC-1005", "4K HDR Streaming Webcam", ProductCategory.ELECTRONICS.value, "Cameras", "139.99", "60.00"),
            ("PRD-000018", "SKU-HOME-4004", "Smart Temperature Heated Mug", ProductCategory.HOME.value, "Drinkware", "99.99", "45.00"),
            ("PRD-000019", "SKU-SAAS-2004", "Security & Compliance Vault Add-on", ProductCategory.SAAS.value, "Security", "360.00", "60.00"),
            ("PRD-000020", "SKU-ACC-5004", "Compact Aluminium Laptop Stand", ProductCategory.ACCESSORIES.value, "Stands", "49.99", "18.00"),
        ]

        created_ts = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat()
        self.products = [
            {
                "product_id": pid,
                "sku": sku,
                "name": name,
                "category": cat,
                "sub_category": subcat,
                "unit_price": Decimal(price),
                "cost_price": Decimal(cost),
                "is_active": True,
                "created_at": created_ts,
            }
            for pid, sku, name, cat, subcat, price, cost in catalog_defs
        ]

    def _generate_segment_rules(self):
        """Generate static master segment rules."""
        rule_defs = [
            (
                "SEG-2026-000001",
                SegmentCode.VIP_LOYALIST.value,
                "VIP Loyalists",
                "High spenders with frequent orders and high satisfaction.",
                json.dumps({"recency_days_max": 45, "frequency_min": 4, "monetary_min": 1000.0, "csat_min": 3.5}),
                True,
                1,
            ),
            (
                "SEG-2026-000002",
                SegmentCode.SERVICE_HEAVY_DISSATISFIED.value,
                "Service-Heavy / Dissatisfied",
                "Accounts with high support friction, elevated service costs, or poor CSAT.",
                json.dumps({"service_cost_min": 150.0, "has_open_critical": True, "csat_max": 2}),
                True,
                2,
            ),
            (
                "SEG-2026-000003",
                SegmentCode.AT_RISK_DORMANT.value,
                "At-Risk / Dormant",
                "Past buyers with no recent orders and dwindling digital engagement.",
                json.dumps({"recency_days_min": 90, "frequency_min": 1, "engagement_max": 15.0}),
                True,
                3,
            ),
            (
                "SEG-2026-000004",
                SegmentCode.HIGH_POTENTIAL.value,
                "High-Potential Growth",
                "Promising accounts with moderate spend and active digital engagement.",
                json.dumps({"recency_days_max": 60, "frequency_range": [1, 3], "monetary_min": 250.0, "engagement_min": 40.0}),
                False,
                4,
            ),
            (
                "SEG-2026-000005",
                SegmentCode.NEW_ONBOARDING.value,
                "New Onboarding",
                "Recent signups within the last 30 days starting their lifecycle journey.",
                json.dumps({"days_since_signup_max": 30, "frequency_max": 1}),
                True,
                5,
            ),
        ]

        created_ts = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat()
        self.segment_rules = [
            {
                "rule_id": rid,
                "segment_code": code,
                "segment_name": name,
                "criteria_description": desc,
                "criteria_json": crit,
                "is_exclusive": is_ex,
                "priority_rank": prio,
                "is_active": True,
                "created_at": created_ts,
            }
            for rid, code, name, desc, crit, is_ex, prio in rule_defs
        ]

    def _generate_action_catalog(self):
        """Generate static master action catalog."""
        action_defs = [
            (
                "ACTN-2026-000001",
                "VIP_CONCIERGE_REWARD",
                "VIP Executive Concierge & Reward Gift",
                SegmentCode.VIP_LOYALIST.value,
                ActionChannel.EMAIL.value,
                json.dumps({"required_consent": "EMAIL_MARKETING", "cooldown_days": 30, "suppress_if_open_critical": True}),
                "Provides dedicated account manager access and premium tier perks.",
            ),
            (
                "ACTN-2026-000002",
                "PROACTIVE_SUPPORT_ESCALATION",
                "Proactive Support Manager Outreach",
                SegmentCode.SERVICE_HEAVY_DISSATISFIED.value,
                ActionChannel.PHONE.value,
                json.dumps({"required_consent": None, "cooldown_days": 7, "priority": "HIGH"}),
                "Direct senior agent intervention to resolve high friction support issues.",
            ),
            (
                "ACTN-2026-000003",
                "WINBACK_DISCOUNT_OFFER",
                "Win-Back Re-activation Incentive",
                SegmentCode.AT_RISK_DORMANT.value,
                ActionChannel.EMAIL.value,
                json.dumps({"required_consent": "EMAIL_MARKETING", "cooldown_days": 14, "suppress_if_open_critical": True}),
                "Sends a personalized 25% discount voucher to re-engage lapsed customers.",
            ),
            (
                "ACTN-2026-000004",
                "CROSS_SELL_RECOMMENDATION",
                "Intelligent Complementary Cross-Sell",
                SegmentCode.HIGH_POTENTIAL.value,
                ActionChannel.EMAIL.value,
                json.dumps({"required_consent": "EMAIL_MARKETING", "cooldown_days": 10, "suppress_if_open_critical": False}),
                "Recommends tailored accessories or software extensions based on prior purchases.",
            ),
            (
                "ACTN-2026-000005",
                "PRODUCT_ONBOARDING_SERIES",
                "Lifecycle Welcome & Guided Onboarding",
                SegmentCode.NEW_ONBOARDING.value,
                ActionChannel.EMAIL.value,
                json.dumps({"required_consent": "EMAIL_MARKETING", "cooldown_days": 5, "suppress_if_open_critical": False}),
                "Educational step-by-step product walkthroughs to drive initial product adoption.",
            ),
        ]

        self.action_catalog = [
            {
                "action_id": aid,
                "action_code": code,
                "action_name": name,
                "target_segment_code": seg,
                "channel": ch,
                "suppression_rules_json": supp,
                "description": desc,
                "is_active": True,
            }
            for aid, code, name, seg, ch, supp, desc in action_defs
        ]

    def _generate_customers(self):
        """Generate customers with realistic names, emails, and signup dates."""
        first_names = [
            "Alexander", "Sophia", "Liam", "Olivia", "Noah", "Emma", "James", "Ava", "William", "Isabella",
            "Benjamin", "Mia", "Lucas", "Harper", "Henry", "Evelyn", "Theodore", "Abigail", "Jack", "Emily",
            "Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Aditya", "Neha", "Arjun", "Pooja",
            "Chen", "Wei", "Mei", "Jun", "Yuki", "Kenji", "Hana", "Sora", "Carlos", "Elena",
            "Mateo", "Camila", "Lucas", "Valeria", "Gabriel", "Isabella", "Lars", "Astrid", "Frederik", "Ingrid"
        ]
        last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
            "Patel", "Sharma", "Verma", "Rao", "Gupta", "Deshmukh", "Joshi", "Kulkarni", "Nair", "Reddy",
            "Zhang", "Wang", "Li", "Liu", "Chen", "Tanaka", "Sato", "Suzuki", "Takahashi", "Watanabe",
            "Mueller", "Schmidt", "Schneider", "Fischer", "Weber", "Dubois", "Moreau", "Laurent", "Simon", "Michel"
        ]

        stages = [
            LifecycleStage.ACTIVE.value,
            LifecycleStage.DORMANT.value,
            LifecycleStage.NEW.value,
            LifecycleStage.PROSPECT.value,
            LifecycleStage.CHURNED.value,
        ]
        stage_weights = [0.45, 0.25, 0.15, 0.10, 0.05]

        start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        total_days = (self.reference_date - start_date).days

        for i in range(1, self.num_customers + 1):
            cid = f"CUS-{i:06d}"
            fn = self.rng.choice(first_names)
            ln = self.rng.choice(last_names)
            email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
            phone = f"+1{self.rng.randint(200, 999)}{self.rng.randint(100, 999)}{self.rng.randint(1000, 9999)}"

            # Signup date distribution (uniform across last 2.8 years)
            days_offset = self.rng.randint(0, total_days)
            signup_dt = start_date + timedelta(days=days_offset, seconds=self.rng.randint(0, 86399))
            stage = self.rng.choices(stages, weights=stage_weights, k=1)[0]
            status = CustomerStatus.ACTIVE.value if stage != LifecycleStage.CHURNED.value else CustomerStatus.INACTIVE.value

            self.customers.append({
                "customer_id": cid,
                "first_name": fn,
                "last_name": ln,
                "email": email,
                "phone": phone,
                "lifecycle_stage": stage,
                "status": status,
                "signup_date": signup_dt.date().isoformat(),
                "created_at": signup_dt.isoformat(),
                "updated_at": (signup_dt + timedelta(days=self.rng.randint(0, 30))).isoformat(),
            })

    def _generate_consents(self):
        """Generate explicit channel-level consent records per customer."""
        channels = [
            ConsentChannel.EMAIL_MARKETING.value,
            ConsentChannel.SMS_MARKETING.value,
            ConsentChannel.PHONE_SALES.value,
            ConsentChannel.PUSH_NOTIFICATION.value,
        ]

        consent_counter = 0
        for cust in self.customers:
            cust_id = cust["customer_id"]
            signup_dt = datetime.fromisoformat(cust["created_at"])

            for ch in channels:
                consent_counter += 1
                con_id = f"CON-2026-{consent_counter:06d}"

                # 75% OPTED_IN, 15% OPTED_OUT, 10% REVOKED
                r = self.rng.random()
                if r < 0.75:
                    status = ConsentStatus.OPTED_IN.value
                    opted_in_at = signup_dt.isoformat()
                    revoked_at = None
                elif r < 0.90:
                    status = ConsentStatus.OPTED_OUT.value
                    opted_in_at = None
                    revoked_at = signup_dt.isoformat()
                else:
                    status = ConsentStatus.REVOKED.value
                    opted_in_at = signup_dt.isoformat()
                    revoked_dt = signup_dt + timedelta(days=self.rng.randint(1, 90))
                    revoked_at = min(revoked_dt, self.reference_date).isoformat()

                self.consents.append({
                    "consent_id": con_id,
                    "customer_id": cust_id,
                    "channel": ch,
                    "status": status,
                    "opted_in_at": opted_in_at,
                    "revoked_at": revoked_at,
                    "last_updated_at": (revoked_at or opted_in_at or cust["created_at"]),
                })

    # --- Dependent Transaction & Event Generators ---

    def _generate_orders_and_lines(self):
        """Generate orders and order lines with strictly reconciled arithmetic."""
        # Non-prospect customers can place orders
        eligible_custs = [c for c in self.customers if c["lifecycle_stage"] != LifecycleStage.PROSPECT.value]
        if not eligible_custs:
            eligible_custs = self.customers

        # Customer ordering distribution: Pareto (80/20 power law distribution)
        num_custs = len(eligible_custs)
        # Weight top 20% heavily
        cust_weights = [10.0 if i < (num_custs * 0.2) else 1.0 for i in range(num_custs)]

        line_counter = 0
        for i in range(1, self.num_orders + 1):
            order_id = f"ORD-2026-{i:06d}"
            cust = self.rng.choices(eligible_custs, weights=cust_weights, k=1)[0]
            cust_signup = datetime.fromisoformat(cust["created_at"])

            # Order date must be >= customer signup date and <= reference_date
            remaining_seconds = max(60, int((self.reference_date - cust_signup).total_seconds()))
            order_dt = cust_signup + timedelta(seconds=self.rng.randint(0, remaining_seconds))

            # Generate 1 to 4 lines
            num_lines = self.rng.choices([1, 2, 3, 4], weights=[0.55, 0.25, 0.15, 0.05], k=1)[0]
            chosen_products = self.rng.sample(self.products, k=min(num_lines, len(self.products)))

            lines = []
            order_subtotal = Decimal("0.00")
            order_refund = Decimal("0.00")
            has_return = False

            for idx, prod in enumerate(chosen_products, start=1):
                line_counter += 1
                line_id = f"LIN-{order_id}-{idx:02d}"
                qty = self.rng.choices([1, 2, 3], weights=[0.8, 0.15, 0.05], k=1)[0]
                uprice = Decimal(str(prod["unit_price"]))

                # 15% chance of line discount
                disc = Decimal("0.00")
                if self.rng.random() < 0.15:
                    disc = (uprice * Decimal(str(qty)) * Decimal("0.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                ltotal = (uprice * Decimal(str(qty))) - disc
                order_subtotal += ltotal

                # 8% return rate
                is_ret = False
                ret_amt = Decimal("0.00")
                if self.rng.random() < 0.08:
                    is_ret = True
                    has_return = True
                    ret_amt = ltotal
                    order_refund += ret_amt

                lines.append({
                    "order_line_id": line_id,
                    "order_id": order_id,
                    "product_id": prod["product_id"],
                    "quantity": qty,
                    "unit_price": uprice,
                    "discount_amount": disc,
                    "line_total": ltotal,
                    "is_returned": is_ret,
                    "return_amount": ret_amt,
                })

            self.order_lines.extend(lines)

            # Order-level aggregates
            order_discount = Decimal("0.00")
            tax = (order_subtotal * Decimal("0.08")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            shipping = Decimal("10.00") if order_subtotal < Decimal("100.00") else Decimal("0.00")
            total = order_subtotal - order_discount + tax + shipping
            net = total - order_refund

            if has_return:
                pay_status = PaymentStatus.REFUNDED.value if order_refund >= total else PaymentStatus.PARTIALLY_REFUNDED.value
                ful_status = FulfillmentStatus.RETURNED.value
            else:
                pay_status = PaymentStatus.PAID.value
                ful_status = FulfillmentStatus.DELIVERED.value

            self.orders.append({
                "order_id": order_id,
                "customer_id": cust["customer_id"],
                "order_date": order_dt.isoformat(),
                "subtotal": order_subtotal,
                "discount_amount": order_discount,
                "tax": tax,
                "shipping_fee": shipping,
                "total_amount": total,
                "refund_amount": order_refund,
                "net_amount": net,
                "payment_status": pay_status,
                "fulfillment_status": ful_status,
            })

    def _generate_engagement_events(self):
        """Generate high-volume clickstream and digital interaction events."""
        channels = [EventChannel.WEB.value, EventChannel.MOBILE_APP.value, EventChannel.EMAIL.value, EventChannel.PUSH.value]
        channel_weights = [0.50, 0.30, 0.15, 0.05]

        event_types = [
            EventType.PAGE_VIEW.value,
            EventType.PRODUCT_VIEW.value,
            EventType.CART_ADD.value,
            EventType.APP_LOGIN.value,
            EventType.EMAIL_OPEN.value,
            EventType.EMAIL_CLICK.value,
            EventType.UNSUBSCRIBE.value,
        ]
        type_weights = [0.45, 0.25, 0.12, 0.10, 0.05, 0.02, 0.01]

        for i in range(1, self.num_events + 1):
            eid = f"ENG-2026-{i:06d}"
            cust = self.rng.choice(self.customers)
            cust_signup = datetime.fromisoformat(cust["created_at"])

            rem_sec = max(60, int((self.reference_date - cust_signup).total_seconds()))
            event_dt = cust_signup + timedelta(seconds=self.rng.randint(0, rem_sec))

            ch = self.rng.choices(channels, weights=channel_weights, k=1)[0]
            et = self.rng.choices(event_types, weights=type_weights, k=1)[0]
            sid = f"SES-{self.rng.randint(100000, 999999)}"

            meta = json.dumps({
                "device": self.rng.choice(["iOS", "Android", "macOS", "Windows"]),
                "duration_sec": self.rng.randint(5, 300),
            })

            self.engagement_events.append({
                "event_id": eid,
                "customer_id": cust["customer_id"],
                "channel": ch,
                "event_type": et,
                "event_timestamp": event_dt.isoformat(),
                "session_id": sid,
                "metadata_json": meta,
            })

    def _generate_support_cases(self):
        """Generate customer support cases with realistic costs, categories, and CSAT."""
        categories = [
            SupportCategory.BILLING.value,
            SupportCategory.DEFECTIVE_PRODUCT.value,
            SupportCategory.DELIVERY_DELAY.value,
            SupportCategory.ACCOUNT_ACCESS.value,
            SupportCategory.FEATURE_REQUEST.value,
        ]
        priorities = [SupportPriority.LOW.value, SupportPriority.MEDIUM.value, SupportPriority.HIGH.value, SupportPriority.CRITICAL.value]
        priority_weights = [0.40, 0.35, 0.18, 0.07]

        channels = [SupportChannel.CHAT.value, SupportChannel.EMAIL.value, SupportChannel.TICKET.value, SupportChannel.PHONE.value]

        for i in range(1, self.num_cases + 1):
            case_id = f"CAS-2026-{i:06d}"
            cust = self.rng.choice(self.customers)
            cust_signup = datetime.fromisoformat(cust["created_at"])

            rem_sec = max(60, int((self.reference_date - cust_signup).total_seconds()))
            created_dt = cust_signup + timedelta(seconds=self.rng.randint(0, rem_sec))

            priority = self.rng.choices(priorities, weights=priority_weights, k=1)[0]
            category = self.rng.choice(categories)
            channel = self.rng.choice(channels)

            # 85% resolved, 15% open/escalated
            is_resolved = self.rng.random() < 0.85
            if is_resolved:
                status = SupportStatus.RESOLVED.value if self.rng.random() < 0.7 else SupportStatus.CLOSED.value
                resolve_hours = self.rng.randint(1, 120)
                resolved_dt = min(created_dt + timedelta(hours=resolve_hours), self.reference_date)
                csat = self.rng.choices([1, 2, 3, 4, 5], weights=[0.08, 0.12, 0.20, 0.35, 0.25], k=1)[0]
            else:
                status = SupportStatus.OPEN.value if self.rng.random() < 0.7 else SupportStatus.ESCALATED.value
                resolved_dt = None
                csat = None

            # Service cost ($15 base up to $300 based on priority and duration)
            cost_mult = 1.0 if priority == SupportPriority.LOW.value else (2.0 if priority == SupportPriority.MEDIUM.value else (4.0 if priority == SupportPriority.HIGH.value else 8.0))
            service_cost = (Decimal(str(self.rng.uniform(15.0, 35.0))) * Decimal(str(cost_mult))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            self.support_cases.append({
                "case_id": case_id,
                "customer_id": cust["customer_id"],
                "channel": channel,
                "priority": priority,
                "category": category,
                "status": status,
                "service_cost": service_cost,
                "csat_score": csat,
                "created_at": created_dt.isoformat(),
                "resolved_at": resolved_dt.isoformat() if resolved_dt else None,
            })

    # --- Analytics & Derived Entities ---

    def _generate_segment_memberships(self):
        """Derive RFM, engagement, and service burden metrics strictly from source tables and assign segments."""
        # Index orders by customer
        orders_by_cust: Dict[str, List[Dict[str, Any]]] = {}
        for o in self.orders:
            orders_by_cust.setdefault(o["customer_id"], []).append(o)

        # Index engagement events by customer
        events_by_cust: Dict[str, int] = {}
        for e in self.engagement_events:
            events_by_cust[e["customer_id"]] = events_by_cust.get(e["customer_id"], 0) + 1

        # Index support cases by customer
        cases_by_cust: Dict[str, List[Dict[str, Any]]] = {}
        for c in self.support_cases:
            cases_by_cust.setdefault(c["customer_id"], []).append(c)

        # Segment rules lookup
        rule_map = {r["segment_code"]: r["rule_id"] for r in self.segment_rules}

        for cust in self.customers:
            cid = cust["customer_id"]
            cust_signup = datetime.fromisoformat(cust["created_at"])
            days_since_signup = (self.reference_date - cust_signup).days

            cust_orders = orders_by_cust.get(cid, [])
            valid_orders = [o for o in cust_orders if o["fulfillment_status"] != FulfillmentStatus.CANCELLED.value]

            # 1. Recency
            if valid_orders:
                latest_order_dt = max(datetime.fromisoformat(o["order_date"]) for o in valid_orders)
                recency_days = max(0, (self.reference_date - latest_order_dt).days)
            else:
                recency_days = days_since_signup

            # 2. Frequency
            frequency_count = len(valid_orders)

            # 3. Monetary (Net spend: sum(net_amount))
            monetary_net_spend = sum((Decimal(str(o["net_amount"])) for o in valid_orders), Decimal("0.00"))

            # 4. Engagement score (0-100)
            event_count = events_by_cust.get(cid, 0)
            engagement_score = min(Decimal("100.00"), Decimal(str(event_count * 5.0)))

            # 5. Service burden index
            cust_cases = cases_by_cust.get(cid, [])
            service_burden = sum((Decimal(str(c["service_cost"])) for c in cust_cases), Decimal("0.00"))
            has_open_critical = any(c["priority"] == "CRITICAL" and c["status"] in ("OPEN", "ESCALATED") for c in cust_cases)
            avg_csat = (
                sum(c["csat_score"] for c in cust_cases if c["csat_score"] is not None) / len([c for c in cust_cases if c["csat_score"] is not None])
                if any(c["csat_score"] is not None for c in cust_cases)
                else 4.5
            )

            # Business segmentation evaluation (Priority order):
            # Rule 1: VIP Loyalist
            if recency_days <= 45 and frequency_count >= 4 and monetary_net_spend >= Decimal("1000.00") and avg_csat >= 3.5:
                assigned_code = SegmentCode.VIP_LOYALIST.value
                notes = f"Qualified VIP: Recency {recency_days}d <= 45d, Orders {frequency_count} >= 4, Net Spend ${monetary_net_spend} >= $1000, CSAT {avg_csat:.1f} >= 3.5."
            # Rule 2: Service-Heavy / Dissatisfied
            elif service_burden >= Decimal("150.00") or has_open_critical or avg_csat <= 2.0:
                assigned_code = SegmentCode.SERVICE_HEAVY_DISSATISFIED.value
                notes = f"Service Burden Alert: Support Cost ${service_burden} (threshold $150), Open Critical Ticket={has_open_critical}, Avg CSAT={avg_csat:.1f}."
            # Rule 3: At-Risk / Dormant
            elif recency_days >= 90 and frequency_count >= 1 and engagement_score <= Decimal("15.00"):
                assigned_code = SegmentCode.AT_RISK_DORMANT.value
                notes = f"Dormant Risk: Recency {recency_days}d >= 90d with no recent orders, low engagement score {engagement_score:.1f} <= 15."
            # Rule 4: New Onboarding
            elif days_since_signup <= 30 and frequency_count <= 1:
                assigned_code = SegmentCode.NEW_ONBOARDING.value
                notes = f"New Account: Signed up {days_since_signup}d ago <= 30d, onboarding lifecycle phase."
            # Rule 5: High-Potential Growth (Default active/growing segment)
            else:
                assigned_code = SegmentCode.HIGH_POTENTIAL.value
                notes = f"High Potential: Active customer, Net Spend ${monetary_net_spend}, Recency {recency_days}d, Engagement {engagement_score:.1f}."

            rule_id = rule_map[assigned_code]
            mem_id = f"MEM-{rule_id}-{cid}"

            self.segment_memberships.append({
                "membership_id": mem_id,
                "rule_id": rule_id,
                "customer_id": cid,
                "assigned_at": self.reference_date.isoformat(),
                "recency_days": recency_days,
                "frequency_count": frequency_count,
                "monetary_net_spend": monetary_net_spend,
                "engagement_score": engagement_score,
                "service_burden_index": service_burden,
                "explainability_notes": notes,
                "is_active": True,
            })

    def _generate_action_outcomes(self):
        """Recommend actions based on segment memberships, enforce consent guardrails, and record outcomes."""
        rule_to_code = {r["rule_id"]: r["segment_code"] for r in self.segment_rules}
        action_by_segment = {a["target_segment_code"]: a for a in self.action_catalog}

        # Index consents by customer: {cust_id: {channel: status}}
        consents_by_cust: Dict[str, Dict[str, str]] = {}
        for c in self.consents:
            consents_by_cust.setdefault(c["customer_id"], {})[c["channel"]] = c["status"]

        # Index open critical cases
        critical_custs = {
            c["customer_id"]
            for c in self.support_cases
            if c["priority"] == "CRITICAL" and c["status"] in ("OPEN", "ESCALATED")
        }

        outcome_counter = 0
        for mem in self.segment_memberships:
            outcome_counter += 1
            out_id = f"OUT-2026-{outcome_counter:06d}"
            rec_id = f"REC-2026-{outcome_counter:06d}"

            cust_id = mem["customer_id"]
            seg_code = rule_to_code.get(mem["rule_id"], SegmentCode.HIGH_POTENTIAL.value)
            action = action_by_segment.get(seg_code, self.action_catalog[0])
            action_id = action["action_id"]

            supp_rules = json.loads(action["suppression_rules_json"])
            req_consent = supp_rules.get("required_consent")
            suppress_if_critical = supp_rules.get("suppress_if_open_critical", False)

            # Evaluate suppression guardrails
            is_suppressed = False
            supp_reason = None

            cust_consents = consents_by_cust.get(cust_id, {})
            if req_consent and cust_consents.get(req_consent) in (ConsentStatus.OPTED_OUT.value, ConsentStatus.REVOKED.value):
                is_suppressed = True
                supp_reason = "CONSENT_REVOKED"
            elif suppress_if_critical and cust_id in critical_custs:
                is_suppressed = True
                supp_reason = "OPEN_CRITICAL_SUPPORT_CASE"

            exec_dt = self.reference_date - timedelta(days=self.rng.randint(1, 14), hours=self.rng.randint(0, 23))

            if is_suppressed:
                del_status = DeliveryStatus.SUPPRESSED.value
                eng_resp = None
                rev = None
                attr_order = None
                notes = f"Action suppressed by policy guardrail: {supp_reason}."
            else:
                del_status = DeliveryStatus.DELIVERED.value
                # Response likelihood based on engagement
                r = self.rng.random()
                if r < 0.40:
                    eng_resp = EngagementResponse.OPENED.value
                    rev = None
                    attr_order = None
                elif r < 0.65:
                    eng_resp = EngagementResponse.CLICKED.value
                    rev = None
                    attr_order = None
                elif r < 0.85:
                    eng_resp = EngagementResponse.CONVERTED.value
                    rev = Decimal(str(self.rng.choice([49.99, 99.99, 149.99, 299.99])))
                    attr_order = f"ORD-2026-{self.rng.randint(1, len(self.orders)):06d}" if self.orders else None
                elif r < 0.95:
                    eng_resp = EngagementResponse.IGNORED.value
                    rev = None
                    attr_order = None
                else:
                    eng_resp = EngagementResponse.UNSUBSCRIBED.value
                    rev = None
                    attr_order = None
                notes = "Action dispatched and tracked successfully."

            self.action_outcomes.append({
                "outcome_id": out_id,
                "recommendation_id": rec_id,
                "action_id": action_id,
                "customer_id": cust_id,
                "execution_timestamp": exec_dt.isoformat(),
                "delivery_status": del_status,
                "suppression_reason": supp_reason,
                "engagement_response": eng_resp,
                "conversion_revenue": rev,
                "attributed_order_id": attr_order,
                "notes": notes,
            })

    # --- Exporters ---

    def export_csv(self, output_dir: str):
        """Export all 11 tables and ground truth into separate CSV files."""
        os.makedirs(output_dir, exist_ok=True)
        tables = [
            ("customers.csv", self.customers),
            ("products.csv", self.products),
            ("orders.csv", self.orders),
            ("order_lines.csv", self.order_lines),
            ("engagement_events.csv", self.engagement_events),
            ("support_cases.csv", self.support_cases),
            ("consents.csv", self.consents),
            ("segment_rules.csv", self.segment_rules),
            ("segment_memberships.csv", self.segment_memberships),
            ("action_catalog.csv", self.action_catalog),
            ("action_outcomes.csv", self.action_outcomes),
            ("ground_truth.csv", [g.model_dump() for g in self.edge_injector.get_ground_truth()]),
        ]

        for fname, data in tables:
            path = os.path.join(output_dir, fname)
            if not data:
                continue
            fieldnames = list(data[0].keys())
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in data:
                    # Serialize Decimal and other non-primitives
                    cleaned_row = {
                        k: (float(v) if isinstance(v, Decimal) else v)
                        for k, v in row.items()
                    }
                    writer.writerow(cleaned_row)

    def export_json(self, output_dir: str):
        """Export dataset as structured JSON files."""
        os.makedirs(output_dir, exist_ok=True)
        tables = [
            ("customers.json", self.customers),
            ("products.json", self.products),
            ("orders.json", self.orders),
            ("order_lines.json", self.order_lines),
            ("engagement_events.json", self.engagement_events),
            ("support_cases.json", self.support_cases),
            ("consents.json", self.consents),
            ("segment_rules.json", self.segment_rules),
            ("segment_memberships.json", self.segment_memberships),
            ("action_catalog.json", self.action_catalog),
            ("action_outcomes.json", self.action_outcomes),
            ("ground_truth.json", [g.model_dump() for g in self.edge_injector.get_ground_truth()]),
        ]

        def default_serializer(o):
            if isinstance(o, (Decimal, date, datetime)):
                return str(o)
            return str(o)

        for fname, data in tables:
            path = os.path.join(output_dir, fname)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=default_serializer)

    def export_sqlite(self, db_path: str):
        """Export dataset into a self-contained SQLite database with foreign keys and indexes."""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        if os.path.exists(db_path):
            os.remove(db_path)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

        # Create Schema
        cur.executescript("""
        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            lifecycle_stage TEXT NOT NULL,
            status TEXT NOT NULL,
            signup_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE products (
            product_id TEXT PRIMARY KEY,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            sub_category TEXT NOT NULL,
            unit_price REAL NOT NULL,
            cost_price REAL NOT NULL,
            is_active INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            order_date TEXT NOT NULL,
            subtotal REAL NOT NULL,
            discount_amount REAL NOT NULL,
            tax REAL NOT NULL,
            shipping_fee REAL NOT NULL,
            total_amount REAL NOT NULL,
            refund_amount REAL NOT NULL,
            net_amount REAL NOT NULL,
            payment_status TEXT NOT NULL,
            fulfillment_status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE order_lines (
            order_line_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            discount_amount REAL NOT NULL,
            line_total REAL NOT NULL,
            is_returned INTEGER NOT NULL,
            return_amount REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        CREATE TABLE engagement_events (
            event_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL,
            metadata_json TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE support_cases (
            case_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            priority TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            service_cost REAL NOT NULL,
            csat_score INTEGER,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE consents (
            consent_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            opted_in_at TEXT,
            revoked_at TEXT,
            last_updated_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE segment_rules (
            rule_id TEXT PRIMARY KEY,
            segment_code TEXT NOT NULL UNIQUE,
            segment_name TEXT NOT NULL,
            criteria_description TEXT NOT NULL,
            criteria_json TEXT NOT NULL,
            is_exclusive INTEGER NOT NULL,
            priority_rank INTEGER NOT NULL,
            is_active INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE segment_memberships (
            membership_id TEXT PRIMARY KEY,
            rule_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            recency_days INTEGER NOT NULL,
            frequency_count INTEGER NOT NULL,
            monetary_net_spend REAL NOT NULL,
            engagement_score REAL NOT NULL,
            service_burden_index REAL NOT NULL,
            explainability_notes TEXT NOT NULL,
            is_active INTEGER NOT NULL,
            FOREIGN KEY (rule_id) REFERENCES segment_rules(rule_id),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE action_catalog (
            action_id TEXT PRIMARY KEY,
            action_code TEXT NOT NULL UNIQUE,
            action_name TEXT NOT NULL,
            target_segment_code TEXT NOT NULL,
            channel TEXT NOT NULL,
            suppression_rules_json TEXT NOT NULL,
            description TEXT NOT NULL,
            is_active INTEGER NOT NULL
        );

        CREATE TABLE action_outcomes (
            outcome_id TEXT PRIMARY KEY,
            recommendation_id TEXT NOT NULL,
            action_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            execution_timestamp TEXT NOT NULL,
            delivery_status TEXT NOT NULL,
            suppression_reason TEXT,
            engagement_response TEXT,
            conversion_revenue REAL,
            attributed_order_id TEXT,
            notes TEXT,
            FOREIGN KEY (action_id) REFERENCES action_catalog(action_id),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE ground_truth_anomalies (
            anomaly_id TEXT PRIMARY KEY,
            issue_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            injected_details TEXT NOT NULL,
            expected_behavior TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX idx_orders_customer ON orders(customer_id);
        CREATE INDEX idx_lines_order ON order_lines(order_id);
        CREATE INDEX idx_events_customer ON engagement_events(customer_id);
        CREATE INDEX idx_cases_customer ON support_cases(customer_id);
        CREATE INDEX idx_consents_customer ON consents(customer_id);
        CREATE INDEX idx_mem_customer ON segment_memberships(customer_id);
        CREATE INDEX idx_outcomes_customer ON action_outcomes(customer_id);
        """)

        # Insert Records
        def insert_rows(table_name: str, rows: List[Dict[str, Any]]):
            if not rows:
                return
            cols = list(rows[0].keys())
            placeholders = ", ".join(["?"] * len(cols))
            sql = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})"
            data = []
            for r in rows:
                row_vals = []
                for c in cols:
                    v = r[c]
                    if isinstance(v, Decimal):
                        v = float(v)
                    elif isinstance(v, bool):
                        v = 1 if v else 0
                    row_vals.append(v)
                data.append(row_vals)
            cur.executemany(sql, data)

        insert_rows("customers", self.customers)
        insert_rows("products", self.products)
        insert_rows("orders", self.orders)
        insert_rows("order_lines", self.order_lines)
        insert_rows("engagement_events", self.engagement_events)
        insert_rows("support_cases", self.support_cases)
        insert_rows("consents", self.consents)
        insert_rows("segment_rules", self.segment_rules)
        # Handle duplicate membership IDs if injected for anomaly simulation
        # In SQLite, insert or ignore or allow duplicate table
        cur.executemany(
            "INSERT OR REPLACE INTO segment_memberships VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                [
                    m["membership_id"],
                    m["rule_id"],
                    m["customer_id"],
                    m["assigned_at"],
                    m["recency_days"],
                    m["frequency_count"],
                    float(m["monetary_net_spend"]) if isinstance(m["monetary_net_spend"], Decimal) else m["monetary_net_spend"],
                    float(m["engagement_score"]) if isinstance(m["engagement_score"], Decimal) else m["engagement_score"],
                    float(m["service_burden_index"]) if isinstance(m["service_burden_index"], Decimal) else m["service_burden_index"],
                    m["explainability_notes"],
                    1 if m["is_active"] else 0,
                ]
                for m in self.segment_memberships
            ]
        )
        insert_rows("action_catalog", self.action_catalog)
        insert_rows("action_outcomes", self.action_outcomes)
        insert_rows("ground_truth_anomalies", [g.model_dump() for g in self.edge_injector.get_ground_truth()])

        conn.commit()
        conn.close()
