"""
Domain entity models and data contracts for YottaFlex AI Segmentation & Action System.
Strictly defines schemas for all 11 core entities, validation rules, and enums.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


# --- Enums ---

class LifecycleStage(str, Enum):
    PROSPECT = "PROSPECT"
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    DORMANT = "DORMANT"
    CHURNED = "CHURNED"


class CustomerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class ProductCategory(str, Enum):
    ELECTRONICS = "Electronics"
    APPAREL = "Apparel"
    HOME = "Home"
    SAAS = "SaaS"
    ACCESSORIES = "Accessories"


class PaymentStatus(str, Enum):
    PAID = "PAID"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    FAILED = "FAILED"


class FulfillmentStatus(str, Enum):
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


class EventChannel(str, Enum):
    EMAIL = "EMAIL"
    WEB = "WEB"
    MOBILE_APP = "MOBILE_APP"
    SMS = "SMS"
    PUSH = "PUSH"


class EventType(str, Enum):
    PAGE_VIEW = "PAGE_VIEW"
    PRODUCT_VIEW = "PRODUCT_VIEW"
    EMAIL_OPEN = "EMAIL_OPEN"
    EMAIL_CLICK = "EMAIL_CLICK"
    CART_ADD = "CART_ADD"
    APP_LOGIN = "APP_LOGIN"
    UNSUBSCRIBE = "UNSUBSCRIBE"


class SupportChannel(str, Enum):
    CHAT = "CHAT"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    TICKET = "TICKET"


class SupportPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SupportCategory(str, Enum):
    BILLING = "BILLING"
    DEFECTIVE_PRODUCT = "DEFECTIVE_PRODUCT"
    DELIVERY_DELAY = "DELIVERY_DELAY"
    ACCOUNT_ACCESS = "ACCOUNT_ACCESS"
    FEATURE_REQUEST = "FEATURE_REQUEST"


class SupportStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ConsentChannel(str, Enum):
    EMAIL_MARKETING = "EMAIL_MARKETING"
    SMS_MARKETING = "SMS_MARKETING"
    PHONE_SALES = "PHONE_SALES"
    PUSH_NOTIFICATION = "PUSH_NOTIFICATION"


class ConsentStatus(str, Enum):
    OPTED_IN = "OPTED_IN"
    OPTED_OUT = "OPTED_OUT"
    REVOKED = "REVOKED"


class SegmentCode(str, Enum):
    VIP_LOYALIST = "VIP_LOYALIST"
    HIGH_POTENTIAL = "HIGH_POTENTIAL"
    AT_RISK_DORMANT = "AT_RISK_DORMANT"
    SERVICE_HEAVY_DISSATISFIED = "SERVICE_HEAVY_DISSATISFIED"
    NEW_ONBOARDING = "NEW_ONBOARDING"


class ActionChannel(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PHONE = "PHONE"
    IN_APP = "IN_APP"


class DeliveryStatus(str, Enum):
    DELIVERED = "DELIVERED"
    SUPPRESSED = "SUPPRESSED"
    BOUNCED = "BOUNCED"
    FAILED = "FAILED"


class EngagementResponse(str, Enum):
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    IGNORED = "IGNORED"
    UNSUBSCRIBED = "UNSUBSCRIBED"
    CONVERTED = "CONVERTED"


class AnomalyType(str, Enum):
    CONFLICTING_EXCLUSIVE_SEGMENTS = "conflicting_exclusive_segments"
    ACTION_VIOLATES_CONSENT = "action_violates_consent"
    RETURN_NOT_NETTED_FROM_SPEND = "return_not_netted_from_spend"
    OUTCOME_ATTRIBUTED_TO_WRONG_ACTION = "outcome_attributed_to_wrong_action"


# --- 11 Core Entities ---

class Customer(BaseModel):
    customer_id: str = Field(..., pattern=r"^CUS-\d{6}$", description="Zero-padded customer ID")
    first_name: str = Field(..., min_length=1, max_length=64)
    last_name: str = Field(..., min_length=1, max_length=64)
    email: str = Field(..., min_length=5, max_length=128)
    phone: str = Field(..., min_length=7, max_length=24)
    lifecycle_stage: LifecycleStage
    status: CustomerStatus = CustomerStatus.ACTIVE
    signup_date: date
    created_at: datetime
    updated_at: datetime


class Product(BaseModel):
    product_id: str = Field(..., pattern=r"^PRD-\d{6}$")
    sku: str = Field(..., min_length=4, max_length=32)
    name: str = Field(..., min_length=2, max_length=128)
    category: ProductCategory
    sub_category: str
    unit_price: Decimal = Field(..., gt=Decimal("0.00"))
    cost_price: Decimal = Field(..., gt=Decimal("0.00"))
    is_active: bool = True
    created_at: datetime


class OrderLine(BaseModel):
    order_line_id: str = Field(..., pattern=r"^LIN-ORD-\d{4}-\d{6}-\d{2}$")
    order_id: str = Field(..., pattern=r"^ORD-\d{4}-\d{6}$")
    product_id: str = Field(..., pattern=r"^PRD-\d{6}$")
    quantity: int = Field(..., ge=1)
    unit_price: Decimal = Field(..., gt=Decimal("0.00"))
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    line_total: Decimal = Field(..., ge=Decimal("0.00"))
    is_returned: bool = False
    return_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class Order(BaseModel):
    order_id: str = Field(..., pattern=r"^ORD-\d{4}-\d{6}$")
    customer_id: str = Field(..., pattern=r"^CUS-\d{6}$")
    order_date: datetime
    subtotal: Decimal = Field(..., ge=Decimal("0.00"))
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    tax: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    shipping_fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    total_amount: Decimal = Field(..., ge=Decimal("0.00"))
    refund_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    net_amount: Decimal
    payment_status: PaymentStatus
    fulfillment_status: FulfillmentStatus


class EngagementEvent(BaseModel):
    event_id: str = Field(..., pattern=r"^ENG-\d{4}-\d{6}$")
    customer_id: str = Field(..., pattern=r"^CUS-\d{6}$")
    channel: EventChannel
    event_type: EventType
    event_timestamp: datetime
    session_id: str
    metadata_json: Optional[str] = "{}"


class SupportCase(BaseModel):
    case_id: str = Field(..., pattern=r"^CAS-\d{4}-\d{6}$")
    customer_id: str = Field(..., pattern=r"^CUS-\d{6}$")
    channel: SupportChannel
    priority: SupportPriority
    category: SupportCategory
    status: SupportStatus
    service_cost: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    csat_score: Optional[int] = Field(default=None, ge=1, le=5)
    created_at: datetime
    resolved_at: Optional[datetime] = None


class Consent(BaseModel):
    consent_id: str = Field(..., pattern=r"^CON-\d{4}-\d{6}$")
    customer_id: str = Field(..., pattern=r"^CUS-\d{6}$")
    channel: ConsentChannel
    status: ConsentStatus
    opted_in_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    last_updated_at: datetime


class SegmentRule(BaseModel):
    rule_id: str = Field(..., pattern=r"^SEG-\d{4}-\d{6}$")
    segment_code: SegmentCode
    segment_name: str
    criteria_description: str
    criteria_json: str
    is_exclusive: bool = True
    priority_rank: int = Field(..., ge=1)
    is_active: bool = True
    created_at: datetime


class SegmentMembership(BaseModel):
    membership_id: str = Field(..., pattern=r"^MEM-SEG-\d{4}-\d{6}-CUS-\d{6}$")
    rule_id: str = Field(..., pattern=r"^SEG-\d{4}-\d{6}$")
    customer_id: str = Field(..., pattern=r"^CUS-\d{6}$")
    assigned_at: datetime
    recency_days: int = Field(..., ge=0)
    frequency_count: int = Field(..., ge=0)
    monetary_net_spend: Decimal
    engagement_score: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("100.00"))
    service_burden_index: Decimal = Field(..., ge=Decimal("0.00"))
    explainability_notes: str
    is_active: bool = True


class ActionCatalog(BaseModel):
    action_id: str = Field(..., pattern=r"^ACTN-\d{4}-\d{6}$")
    action_code: str
    action_name: str
    target_segment_code: SegmentCode
    channel: ActionChannel
    suppression_rules_json: str
    description: str
    is_active: bool = True


class ActionOutcome(BaseModel):
    outcome_id: str = Field(..., pattern=r"^OUT-\d{4}-\d{6}$")
    recommendation_id: str = Field(..., pattern=r"^REC-\d{4}-\d{6}$")
    action_id: str = Field(..., pattern=r"^ACTN-\d{4}-\d{6}$")
    customer_id: str = Field(..., pattern=r"^CUS-\d{6}$")
    execution_timestamp: datetime
    delivery_status: DeliveryStatus
    suppression_reason: Optional[str] = None
    engagement_response: Optional[EngagementResponse] = None
    conversion_revenue: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    attributed_order_id: Optional[str] = None
    notes: Optional[str] = None


# --- Ground Truth Anomaly Record ---

class GroundTruthAnomaly(BaseModel):
    anomaly_id: str = Field(..., pattern=r"^ANOM-\d{6}$")
    issue_type: AnomalyType
    entity_type: str
    entity_id: str
    customer_id: str
    injected_details: str
    expected_behavior: str
    created_at: datetime
