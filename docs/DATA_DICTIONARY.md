# Data Dictionary & Entity Relationship Specification

## 1. System Overview & Nomenclature Conventions
All entities in this system strictly follow deterministic, zero-padded identifier conventions:
- **Customer**: `CUS-000001`
- **Product**: `PRD-000001`
- **Order**: `ORD-YYYY-000001` (e.g., `ORD-2026-000001`)
- **OrderLine**: `LIN-ORD-YYYY-000001-NN` (e.g., `LIN-ORD-2026-000001-01`)
- **EngagementEvent**: `ENG-YYYY-000001` (e.g., `ENG-2026-000001`)
- **SupportCase**: `CAS-YYYY-000001` (e.g., `CAS-2026-000001`)
- **Consent**: `CON-YYYY-000001` (e.g., `CON-2026-000001`)
- **SegmentRule**: `SEG-YYYY-000001` (e.g., `SEG-2026-000001`)
- **SegmentMembership**: `MEM-<segment-id>-<customer-id>` (e.g., `MEM-SEG-2026-000001-CUS-000001`)
- **ActionCatalog**: `ACTN-YYYY-000001` (e.g., `ACTN-2026-000001`)
- **ActionOutcome**: `OUT-YYYY-000001` (e.g., `OUT-2026-000001`)

---

## 2. Entity Relational Model & Cardinality

| Parent Entity | Relationship | Child Entity | Cardinality | Enforced Foreign Key |
|:---|:---:|:---|:---:|:---|
| Customer | Places | Order | 1 : N | `Order.customer_id -> Customer.customer_id` |
| Order | Contains | OrderLine | 1 : N | `OrderLine.order_id -> Order.order_id` |
| Product | Referenced In | OrderLine | 1 : N | `OrderLine.product_id -> Product.product_id` |
| Customer | Generates | EngagementEvent | 1 : N | `EngagementEvent.customer_id -> Customer.customer_id` |
| Customer | Opens | SupportCase | 1 : N | `SupportCase.customer_id -> Customer.customer_id` |
| Customer | Grants / Revokes | Consent | 1 : N | `Consent.customer_id -> Customer.customer_id` |
| Customer + SegmentRule | Associated via Bridge | SegmentMembership | N : M | `SegmentMembership.customer_id -> Customer.customer_id`<br>`SegmentMembership.rule_id -> SegmentRule.rule_id` |
| ActionCatalog | Recommends & Produces | ActionOutcome | 1 : N | `ActionOutcome.action_id -> ActionCatalog.action_id` |
| Customer | Receives | ActionOutcome | 1 : N | `ActionOutcome.customer_id -> Customer.customer_id` |
| Order | Attributed from | ActionOutcome | 0/1 : 1 | `ActionOutcome.attributed_order_id -> Order.order_id` (Optional) |

---

## 3. Data Dictionary (Detailed Field Specifications)

### 3.1 Customer (`customers`)
Master entity representing individual registered customers and prospects.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---:|:---|:---|
| `customer_id` | VARCHAR(16) | Yes | Regex `^CUS-\d{6}$` | None | Primary Key | Must be globally unique | Immutable customer identifier |
| `first_name` | VARCHAR(64) | Yes | Standard string | None | No | Length 1-64 chars | Customer first name |
| `last_name` | VARCHAR(64) | Yes | Standard string | None | No | Length 1-64 chars | Customer last name / surname |
| `email` | VARCHAR(128) | Yes | Valid email format | None | Unique | Regex RFC 5322 email | Primary contact email address |
| `phone` | VARCHAR(24) | Yes | E.164 phone format | None | No | Starts with `+` | Customer contact phone number |
| `lifecycle_stage` | VARCHAR(20) | Yes | `PROSPECT`, `NEW`, `ACTIVE`, `DORMANT`, `CHURNED` | None | No | Enum check | Current customer lifecycle stage |
| `status` | VARCHAR(16) | Yes | `ACTIVE`, `INACTIVE`, `SUSPENDED` | None | No | Enum check | Account status |
| `signup_date` | DATE | Yes | YYYY-MM-DD | Date | No | `signup_date <= CURRENT_DATE` | Date customer enrolled |
| `created_at` | TIMESTAMP | Yes | ISO 8601 UTC | Timestamp | No | `created_at >= signup_date` | Record creation timestamp |
| `updated_at` | TIMESTAMP | Yes | ISO 8601 UTC | Timestamp | No | `updated_at >= created_at` | Record last modification timestamp |

---

### 3.2 Product (`products`)
Master catalog of merchandise, software subscriptions, or service items.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---:|:---|:---|
| `product_id` | VARCHAR(16) | Yes | Regex `^PRD-\d{6}$` | None | Primary Key | Must be globally unique | Master catalog product identifier |
| `sku` | VARCHAR(32) | Yes | Alphanumeric SKU | None | Unique | Length 6-32 chars | Stock Keeping Unit code |
| `name` | VARCHAR(128) | Yes | Standard text | None | No | Length 2-128 chars | Product display name |
| `category` | VARCHAR(32) | Yes | `Electronics`, `Apparel`, `Home`, `SaaS`, `Accessories` | None | No | Enum check | Top-level product category |
| `sub_category` | VARCHAR(32) | Yes | Standard text | None | No | Non-empty string | Granular product sub-category |
| `unit_price` | DECIMAL(10,2) | Yes | `> 0.00` | USD ($) | No | `unit_price > cost_price` | Recommended retail sale price |
| `cost_price` | DECIMAL(10,2) | Yes | `> 0.00` | USD ($) | No | `cost_price <= unit_price` | Inventory acquisition cost |
| `is_active` | BOOLEAN | Yes | `TRUE`, `FALSE` | Flag | No | Boolean check | Product availability flag |
| `created_at` | TIMESTAMP | Yes | ISO 8601 UTC | Timestamp | No | Valid timestamp | Catalog insertion timestamp |

---

### 3.3 Order (`orders`)
Transaction header record for purchases placed by customers.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---:|:---|:---|
| `order_id` | VARCHAR(24) | Yes | Regex `^ORD-\d{4}-\d{6}$` | None | Primary Key | Must be globally unique | Transaction master order ID |
| `customer_id` | VARCHAR(16) | Yes | Regex `^CUS-\d{6}$` | None | No | FK -> `customers.customer_id` | Purchasing customer |
| `order_date` | TIMESTAMP | Yes | ISO 8601 UTC | Timestamp | No | `order_date >= customer.signup_date` | Timestamp when order was placed |
| `subtotal` | DECIMAL(12,2) | Yes | `>= 0.00` | USD ($) | No | Arithmetic sum of child lines | Total before tax, discount, shipping |
| `discount_amount`| DECIMAL(12,2) | Yes | `>= 0.00` | USD ($) | No | `discount_amount <= subtotal` | Promo and voucher discounts applied |
| `tax` | DECIMAL(12,2) | Yes | `>= 0.00` | USD ($) | No | Standard rate (e.g. 7-10% of subtotal) | Sales tax assessment |
| `shipping_fee` | DECIMAL(10,2) | Yes | `>= 0.00` | USD ($) | No | Non-negative decimal | Shipping and handling cost |
| `total_amount` | DECIMAL(12,2) | Yes | `>= 0.00` | USD ($) | No | `subtotal - discount_amount + tax + shipping_fee` | Gross invoiced total |
| `refund_amount` | DECIMAL(12,2) | Yes | `>= 0.00` | USD ($) | No | `refund_amount <= total_amount` | Total amount refunded / returned |
| `net_amount` | DECIMAL(12,2) | Yes | Real number | USD ($) | No | `net_amount == total_amount - refund_amount` | Actual retained monetary revenue |
| `payment_status` | VARCHAR(20) | Yes | `PAID`, `REFUNDED`, `PARTIALLY_REFUNDED`, `FAILED` | None | No | Enum check | Payment processing status |
| `fulfillment_status` | VARCHAR(20) | Yes | `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `RETURNED` | None | No | Enum check | Logistics delivery state |

---

### 3.4 OrderLine (`order_lines`)
Individual line item in an order linking to specific product catalog rows.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---|:---|:---|
| `order_line_id` | VARCHAR(32) | Yes | Regex `^LIN-ORD-\d{4}-\d{6}-\d{2}$` | None | Primary Key | Must be globally unique | Line item unique ID |
| `order_id` | VARCHAR(24) | Yes | Regex `^ORD-\d{4}-\d{6}$` | None | No | FK -> `orders.order_id` | Parent order reference |
| `product_id` | VARCHAR(16) | Yes | Regex `^PRD-\d{6}$` | None | No | FK -> `products.product_id` | Catalog item purchased |
| `quantity` | INTEGER | Yes | `>= 1` | Items | No | Integer check | Quantity ordered |
| `unit_price` | DECIMAL(10,2) | Yes | `> 0.00` | USD ($) | No | Matches product price at sale | Sale price per unit |
| `discount_amount`| DECIMAL(10,2) | Yes | `>= 0.00` | USD ($) | No | `discount_amount <= (unit_price * quantity)` | Line item discount |
| `line_total` | DECIMAL(12,2) | Yes | `>= 0.00` | USD ($) | No | `(unit_price * quantity) - discount_amount` | Net line total |
| `is_returned` | BOOLEAN | Yes | `TRUE`, `FALSE` | Flag | No | Boolean check | Return flag |
| `return_amount`| DECIMAL(12,2) | Yes | `>= 0.00` | USD ($) | No | `is_returned ? <= line_total : == 0.00` | Refunded amount on this line |

---

### 3.5 EngagementEvent (`engagement_events`)
High-volume behavioral clickstream, web, app, and email interactions.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---|:---|:---|
| `event_id` | VARCHAR(24) | Yes | Regex `^ENG-\d{4}-\d{6}$` | None | Primary Key | Must be globally unique | Behavioral event identifier |
| `customer_id` | VARCHAR(16) | Yes | Regex `^CUS-\d{6}$` | None | No | FK -> `customers.customer_id` | Performing customer |
| `channel` | VARCHAR(20) | Yes | `EMAIL`, `WEB`, `MOBILE_APP`, `SMS`, `PUSH` | None | No | Enum check | Ingestion / interaction channel |
| `event_type` | VARCHAR(24) | Yes | `PAGE_VIEW`, `PRODUCT_VIEW`, `EMAIL_OPEN`, `EMAIL_CLICK`, `CART_ADD`, `APP_LOGIN`, `UNSUBSCRIBE` | None | No | Enum check | Behavioral action type |
| `event_timestamp`| TIMESTAMP | Yes | ISO 8601 UTC | Timestamp | No | `event_timestamp >= customer.signup_date` | Timestamp when event occurred |
| `session_id` | VARCHAR(36) | Yes | UUID or session string | None | No | Format check | Digital session identifier |
| `metadata_json` | TEXT | Optional | Valid JSON object | None | No | JSON validity check | Contextual attributes (URL, OS, duration) |

---

### 3.6 SupportCase (`support_cases`)
Customer service, billing, and technical support interactions.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---|:---|:---|
| `case_id` | VARCHAR(24) | Yes | Regex `^CAS-\d{4}-\d{6}$` | None | Primary Key | Must be globally unique | Service ticket identifier |
| `customer_id` | VARCHAR(16) | Yes | Regex `^CUS-\d{6}$` | None | No | FK -> `customers.customer_id` | Customer requesting support |
| `channel` | VARCHAR(16) | Yes | `CHAT`, `PHONE`, `EMAIL`, `TICKET` | None | No | Enum check | Contact support channel |
| `priority` | VARCHAR(16) | Yes | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | None | No | Enum check | Urgency tier |
| `category` | VARCHAR(24) | Yes | `BILLING`, `DEFECTIVE_PRODUCT`, `DELIVERY_DELAY`, `ACCOUNT_ACCESS`, `FEATURE_REQUEST` | None | No | Enum check | Issue topic categorization |
| `status` | VARCHAR(16) | Yes | `OPEN`, `IN_PROGRESS`, `ESCALATED`, `RESOLVED`, `CLOSED` | None | No | Enum check | Ticket lifecycle state |
| `service_cost` | DECIMAL(8,2) | Yes | `>= 0.00` | USD ($) | No | Financial burden metric | Cost incurred to service ticket |
| `csat_score` | INTEGER | Optional | `1, 2, 3, 4, 5` | Rating (1-5) | No | Valid only if resolved/closed | Customer satisfaction feedback |
| `created_at` | TIMESTAMP | Yes | ISO 8601 UTC | Timestamp | No | `created_at >= customer.signup_date` | Ticket intake timestamp |
| `resolved_at` | TIMESTAMP | Optional | ISO 8601 UTC | Timestamp | No | `resolved_at >= created_at` | Closure / resolution timestamp |

---

### 3.7 Consent (`consents`)
Explicit privacy, opt-in/opt-out preferences, and regulatory compliance records.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---|:---|:---|
| `consent_id` | VARCHAR(24) | Yes | Regex `^CON-\d{4}-\d{6}$` | None | Primary Key | Must be globally unique | Consent tracking identifier |
| `customer_id` | VARCHAR(16) | Yes | Regex `^CUS-\d{6}$` | None | No | FK -> `customers.customer_id` | Customer granting/revoking consent |
| `channel` | VARCHAR(24) | Yes | `EMAIL_MARKETING`, `SMS_MARKETING`, `PHONE_SALES`, `PUSH_NOTIFICATION` | None | No | Enum check | Regulated outreach channel |
| `status` | VARCHAR(16) | Yes | `OPTED_IN`, `OPTED_OUT`, `REVOKED` | None | No | Enum check | Current consent posture |
| `opted_in_at` | TIMESTAMP | Optional | ISO 8601 UTC | Timestamp | No | Valid timestamp | When consent was initially granted |
| `revoked_at` | TIMESTAMP | Optional | ISO 8601 UTC | Timestamp | No | `revoked_at >= opted_in_at` | When consent was rescinded |
| `last_updated_at`| TIMESTAMP| Yes | ISO 8601 UTC | Timestamp | No | Timestamp check | Audit timestamp |

---

### 3.8 SegmentRule (`segment_rules`)
Business criteria, RFM thresholds, and definitions governing segmentation.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---|:---|:---|
| `rule_id` | VARCHAR(24) | Yes | Regex `^SEG-\d{4}-\d{6}$` | None | Primary Key | Must be globally unique | Segment definition ID |
| `segment_code` | VARCHAR(32) | Yes | `VIP_LOYALIST`, `HIGH_POTENTIAL`, `AT_RISK_DORMANT`, `SERVICE_HEAVY_DISSATISFIED`, `NEW_ONBOARDING` | None | Unique | Alphanumeric uppercase | Distinct system segment key |
| `segment_name` | VARCHAR(64) | Yes | Human-readable name | None | No | Non-empty string | Commercial business segment label |
| `criteria_description`| TEXT | Yes | Natural language text | None | No | Non-empty string | Plain English rule explanation |
| `criteria_json` | TEXT | Yes | JSON formatted logic | None | No | Valid JSON schema | Structured threshold filters |
| `is_exclusive` | BOOLEAN | Yes | `TRUE`, `FALSE` | Flag | No | Boolean check | True if customer cannot overlap with conflicting tiers |
| `priority_rank` | INTEGER | Yes | `1, 2, 3, 4, 5` | Rank | No | Positive integer | Precedence order for rule evaluation |
| `is_active` | BOOLEAN | Yes | `TRUE`, `FALSE` | Flag | No | Boolean check | Active rule toggle |
| `created_at` | TIMESTAMP | Yes | ISO 8601 UTC | Timestamp | No | Valid timestamp | Definition creation timestamp |

---

### 3.9 SegmentMembership (`segment_memberships`)
Bridge table persisting customer assignment to segments along with computed metrics and explainability notes.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---|:---|:---|
| `membership_id` | VARCHAR(48) | Yes | `MEM-<segment-id>-<customer-id>` | None | Primary Key | Composite deterministic pattern | Unique membership assignment key |
| `rule_id` | VARCHAR(24) | Yes | Regex `^SEG-\d{4}-\d{6}$` | None | No | FK -> `segment_rules.rule_id` | Assigned segment rule |
| `customer_id` | VARCHAR(16) | Yes | Regex `^CUS-\d{6}$` | None | No | FK -> `customers.customer_id` | Segmented customer |
| `assigned_at` | TIMESTAMP | Yes | ISO 8601 UTC | Timestamp | No | Valid timestamp | Assignment calculation timestamp |
| `recency_days` | INTEGER | Yes | `>= 0` | Days | No | Computed from latest order | Days elapsed since last order |
| `frequency_count`| INTEGER | Yes | `>= 0` | Orders | No | Count of non-cancelled orders | Total historical purchases |
| `monetary_net_spend`| DECIMAL(12,2)| Yes | Real number | USD ($) | No | `sum(total_amount) - sum(refund_amount)` | Net monetary value |
| `engagement_score`| DECIMAL(5,2)| Yes | `0.00` to `100.00` | Score (0-100)| No | Derived from event velocity | Digital interaction score |
| `service_burden_index`| DECIMAL(8,2)| Yes| `>= 0.00` | Cost ($) | No | Derived from support ticket volume & cost | Support cost load |
| `explainability_notes`| TEXT | Yes | Transparent rationale | None | No | Human-readable explanation | Exact reasons why customer qualified |
| `is_active` | BOOLEAN | Yes | `TRUE`, `FALSE` | Flag | No | Boolean check | Active segment status flag |

---

### 3.10 ActionCatalog (`action_catalog`)
Master registry of marketing campaigns, support workflows, and engagement actions.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---|:---|:---|
| `action_id` | VARCHAR(24) | Yes | Regex `^ACTN-\d{4}-\d{6}$` | None | Primary Key | Must be globally unique | Master action identifier |
| `action_code` | VARCHAR(32) | Yes | `VIP_CONCIERGE_REWARD`, `WINBACK_DISCOUNT_OFFER`, `PROACTIVE_SUPPORT_ESCALATION`, `PRODUCT_ONBOARDING_SERIES`, `CROSS_SELL_RECOMMENDATION` | None | Unique | Alphanumeric uppercase | Action unique lookup key |
| `action_name` | VARCHAR(64) | Yes | Natural language title | None | No | Non-empty string | Business campaign/action name |
| `target_segment_code`| VARCHAR(32)| Yes | Matches `segment_rules.segment_code` | None | No | FK -> `segment_rules.segment_code` | Primary target audience segment |
| `channel` | VARCHAR(20) | Yes | `EMAIL`, `SMS`, `PHONE`, `IN_APP` | None | No | Enum check | Outreach execution medium |
| `suppression_rules_json`| TEXT| Yes | JSON rules | None | No | Valid JSON | Consent requirements, cooldown periods, exclusions |
| `description` | TEXT | Yes | Plain text | None | No | Non-empty string | Detailed action execution description |
| `is_active` | BOOLEAN | Yes | `TRUE`, `FALSE` | Flag | No | Boolean check | Active campaign toggle |

---

### 3.11 ActionOutcome (`action_outcomes`)
Execution log of dispatched actions, policy decisions (including suppressions), and measurable downstream results.

| Field Name | Type | Required | Allowed Values / Format | Units | Uniqueness | Validation Rule & Foreign Key | Description |
|:---|:---|:---:|:---|:---:|:---|:---|:---|
| `outcome_id` | VARCHAR(24) | Yes | Regex `^OUT-\d{4}-\d{6}$` | None | Primary Key | Must be globally unique | Action delivery / outcome identifier |
| `recommendation_id`| VARCHAR(24)| Yes| Regex `^REC-\d{4}-\d{6}$` | None | No | Decision audit reference | System recommendation run reference |
| `action_id` | VARCHAR(24) | Yes | Regex `^ACTN-\d{4}-\d{6}$` | None | No | FK -> `action_catalog.action_id` | Triggered action |
| `customer_id` | VARCHAR(16) | Yes | Regex `^CUS-\d{6}$` | None | No | FK -> `customers.customer_id` | Target customer |
| `execution_timestamp`| TIMESTAMP| Yes| ISO 8601 UTC | Timestamp | No | Valid timestamp | Dispatch attempt timestamp |
| `delivery_status` | VARCHAR(20) | Yes | `DELIVERED`, `SUPPRESSED`, `BOUNCED`, `FAILED` | None | No | Enum check | Dispatch delivery result |
| `suppression_reason`| VARCHAR(64)| Optional| Enum string or null | None | No | Non-null if `delivery_status == SUPPRESSED` | Reason (e.g. `CONSENT_REVOKED`, `OPEN_CRITICAL_CASE`, `COOLDOWN_ACTIVE`) |
| `engagement_response`| VARCHAR(20)| Optional| `OPENED`, `CLICKED`, `IGNORED`, `UNSUBSCRIBED`, `CONVERTED` | None | No | Enum check | Customer interaction response |
| `conversion_revenue`| DECIMAL(12,2)| Optional| `>= 0.00` | USD ($) | No | Attribution amount | Measurable monetary output generated |
| `attributed_order_id`| VARCHAR(24)| Optional| Regex `^ORD-\d{4}-\d{6}$` | None | No | FK -> `orders.order_id` | Order tied directly to action conversion |
| `notes` | TEXT | Optional | Explanatory text | None | No | Free text | Traceability notes and anomaly flags |

---

## 4. Injected Edge Cases & Ground Truth Anomaly Schema

When deliberate anomalies are injected, they are logged in a separate, isolated `ground_truth.json` / `ground_truth.csv` without leaking into input model features:

| Field Name | Type | Description |
|:---|:---|:---|
| `anomaly_id` | VARCHAR(24) | Unique anomaly record ID (`ANOM-000001`) |
| `issue_type` | VARCHAR(48) | One of: `conflicting_exclusive_segments`, `action_violates_consent`, `return_not_netted_from_spend`, `outcome_attributed_to_wrong_action` |
| `entity_type` | VARCHAR(24) | Target entity (`SegmentMembership`, `ActionOutcome`, `Order`, `Customer`) |
| `entity_id` | VARCHAR(48) | ID of corrupted / anomalous record |
| `customer_id`| VARCHAR(16) | Associated customer ID |
| `injected_details`| TEXT | Specific discrepancy injected (e.g., "Marketing email sent despite consent REVOKED on 2026-03-01") |
| `expected_behavior`| TEXT | Documented rule-based behavior that should have occurred |
