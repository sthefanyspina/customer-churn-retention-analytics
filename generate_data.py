
import pandas as pd
import numpy as np
import random
import os

from datetime import datetime, timedelta

# ============================================================
# CLOUDFLOW - CUSTOMER CHURN & RETENTION DATASET
# ============================================================

# Reproducibility
np.random.seed(42)
random.seed(42)

# ============================================================
# CONFIGURATION
# ============================================================

NUM_CUSTOMERS = 50000
NUM_SUBSCRIPTIONS = 65000
NUM_PAYMENTS = 600000
NUM_USAGE_METRICS = 1000000
NUM_SUPPORT_TICKETS = 150000
NUM_CANCELLATIONS = 15000

START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2025, 12, 31)

OUTPUT_DIR = "dataset"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def random_date(start, end):
    """Generate a random date between two dates."""

    if start > end:
        raise ValueError("Start date cannot be after end date.")

    delta = (end - start).days

    return start + timedelta(
        days=random.randint(0, delta)
    )


def save_dataset(dataframe, filename):
    """Save dataframe as CSV."""

    filepath = os.path.join(OUTPUT_DIR, filename)

    dataframe.to_csv(
        filepath,
        index=False
    )

    print(
        f"Generated: {filename} - "
        f"{len(dataframe):,} records"
    )


def validate_unique(df, column):
    """Validate primary key uniqueness."""

    if df[column].duplicated().any():
        raise ValueError(
            f"Duplicate values found in {column}"
        )


def validate_foreign_key(df, column, reference_df,
                         reference_column):
    """Validate foreign key relationships."""

    invalid = ~df[column].isin(
        reference_df[reference_column]
    )

    if invalid.any():
        raise ValueError(
            f"Invalid foreign keys in {column}: "
            f"{invalid.sum()} records"
        )


# ============================================================
# 1. PLANS TABLE
# ============================================================

plans = pd.DataFrame({

    "plan_id": [1, 2, 3, 4],

    "plan_name": [
        "Starter",
        "Professional",
        "Business",
        "Enterprise"
    ],

    "monthly_price": [
        29.90,
        59.90,
        119.90,
        249.90
    ]

})

# Annual subscription discount:
# 10 monthly payments instead of 12.

plans["annual_price"] = (
    plans["monthly_price"] * 10
).round(2)

# Revenue normalization

plans["monthly_mrr"] = (
    plans["monthly_price"]
)

plans["annual_mrr"] = (
    plans["annual_price"] / 12
).round(2)

plans["annual_arr"] = (
    plans["annual_price"]
).round(2)

save_dataset(plans, "plans.csv")


# ============================================================
# 2. CUSTOMERS TABLE
# ============================================================

regions = [
    "North America",
    "South America",
    "Europe",
    "Asia Pacific",
    "Middle East",
    "Africa"
]

industries = [
    "Technology",
    "Healthcare",
    "Finance",
    "Retail",
    "Manufacturing",
    "Education",
    "Logistics",
    "Consulting",
    "Real Estate",
    "Telecommunications"
]

customers = pd.DataFrame({

    "customer_id": range(
        1,
        NUM_CUSTOMERS + 1
    ),

    "region": np.random.choice(
        regions,
        NUM_CUSTOMERS,
        p=[0.30, 0.18, 0.22, 0.16, 0.08, 0.06]
    ),

    "industry": np.random.choice(
        industries,
        NUM_CUSTOMERS
    ),

    "registration_date": pd.to_datetime([
        random_date(START_DATE, END_DATE)
        for _ in range(NUM_CUSTOMERS)
    ])

})

save_dataset(customers, "customers.csv")


# ============================================================
# 3. SUBSCRIPTIONS TABLE
# ============================================================

customer_ids = customers["customer_id"].to_numpy()

customer_registration = customers.set_index(
    "customer_id"
)["registration_date"].to_dict()

subscription_rows = []

# Assign subscriptions to customers.
# Some customers will have multiple subscriptions.

subscription_distribution = np.random.choice(
    customer_ids,
    size=NUM_SUBSCRIPTIONS,
    replace=True
)

# Track the last cancellation date for each customer.

customer_last_cancellation = {}

for subscription_id, customer_id in enumerate(
    subscription_distribution,
    start=1
):

    registration_date = customer_registration[
        customer_id
    ]

    # New subscription cannot start before registration
    # or after a previous cancellation.

    earliest_start = registration_date

    if customer_id in customer_last_cancellation:

        earliest_start = max(
            earliest_start,
            customer_last_cancellation[customer_id]
            + pd.Timedelta(days=1)
        )

    if earliest_start > END_DATE:
        continue

    start_date = random_date(
        earliest_start.to_pydatetime()
        if isinstance(earliest_start, pd.Timestamp)
        else earliest_start,
        END_DATE
    )

    plan_id = random.choices(
        [1, 2, 3, 4],
        weights=[0.35, 0.35, 0.20, 0.10]
    )[0]

    billing_cycle = random.choices(
        ["Monthly", "Annual"],
        weights=[0.75, 0.25]
    )[0]

    # Synthetic churn probability.
    # This is a simulation parameter, not a causal relationship.

    is_cancelled = random.random() < 0.23

    if is_cancelled:

        end_date = random_date(
            start_date,
            END_DATE
        )

        status = "Cancelled"

        customer_last_cancellation[
            customer_id
        ] = end_date

    else:

        end_date = None
        status = "Active"

    subscription_rows.append({

        "subscription_id": subscription_id,

        "customer_id": customer_id,

        "plan_id": plan_id,

        "start_date": start_date,

        "end_date": end_date,

        "status": status,

        "billing_cycle": billing_cycle

    })


subscriptions = pd.DataFrame(
    subscription_rows
)

subscriptions["start_date"] = pd.to_datetime(
    subscriptions["start_date"]
)

subscriptions["end_date"] = pd.to_datetime(
    subscriptions["end_date"]
)

# Validate subscription dates.

assert (
    subscriptions["end_date"].isna()
    | (
        subscriptions["end_date"]
        >= subscriptions["start_date"]
    )
).all()

# Validate customer relationships.

validate_foreign_key(
    subscriptions,
    "customer_id",
    customers,
    "customer_id"
)

validate_foreign_key(
    subscriptions,
    "plan_id",
    plans,
    "plan_id"
)

validate_unique(
    subscriptions,
    "subscription_id"
)

save_dataset(
    subscriptions,
    "subscriptions.csv"
)


# ============================================================
# 4. CANCELLATIONS TABLE
# ============================================================

cancelled_subscriptions = subscriptions[
    subscriptions["status"] == "Cancelled"
].copy()

cancellation_reasons = [
    "High Pricing",
    "Poor Customer Support",
    "Lack of Features",
    "Low Product Usage",
    "Technical Issues",
    "Competitor Alternative",
    "Business Closure",
    "Budget Constraints"
]

cancellations = pd.DataFrame({

    "cancellation_id": range(
        1,
        len(cancelled_subscriptions) + 1
    ),

    "subscription_id":
        cancelled_subscriptions[
            "subscription_id"
        ].values,

    "customer_id":
        cancelled_subscriptions[
            "customer_id"
        ].values,

    "cancellation_date":
        cancelled_subscriptions[
            "end_date"
        ].values,

    "reason": np.random.choice(
        cancellation_reasons,
        len(cancelled_subscriptions),
        p=[
            0.18, 0.12, 0.14, 0.18,
            0.12, 0.12, 0.06, 0.08
        ]
    )

})

# Validate cancellation relationships.

validate_foreign_key(
    cancellations,
    "subscription_id",
    subscriptions,
    "subscription_id"
)

validate_unique(
    cancellations,
    "subscription_id"
)

# Validate cancellation dates.

assert (
    cancellations["cancellation_date"]
    .notna()
).all()

save_dataset(
    cancellations,
    "cancellations.csv"
)


# ============================================================
# 5. PAYMENTS TABLE
# ============================================================

payment_rows = []

subscription_lookup = subscriptions.set_index(
    "subscription_id"
)

plan_lookup = plans.set_index("plan_id")

# Generate payment dates within subscription lifetime.

for payment_id in range(1, NUM_PAYMENTS + 1):

    subscription_id = random.randint(
        1,
        len(subscriptions)
    )

    subscription = subscription_lookup.loc[
        subscription_id
    ]

    plan = plan_lookup.loc[
        subscription["plan_id"]
    ]

    start_date = subscription["start_date"]

    end_date = subscription["end_date"]

    # Payments cannot happen after cancellation.

    if pd.isna(end_date):
        payment_end = END_DATE
    else:
        payment_end = end_date

    if start_date > payment_end:
        continue

    payment_date = random_date(
        start_date.to_pydatetime(),
        payment_end.to_pydatetime()
        if isinstance(payment_end, pd.Timestamp)
        else payment_end
    )

    # Billing amount

    if subscription["billing_cycle"] == "Annual":

        amount = plan["annual_price"]

    else:

        amount = plan["monthly_price"]

    # Payment failures are synthetic exploratory signals.
    # They are not intended to represent real risk behavior.

    payment_status = random.choices(
        ["Paid", "Failed", "Pending"],
        weights=[0.90, 0.07, 0.03]
    )[0]

    payment_rows.append({

        "payment_id": payment_id,

        "subscription_id": subscription_id,

        "customer_id": subscription["customer_id"],

        "amount": round(amount, 2),

        "payment_date": payment_date,

        "status": payment_status,

        "billing_cycle":
            subscription["billing_cycle"],

        "is_synthetic": True

    })


payments = pd.DataFrame(payment_rows)

validate_foreign_key(
    payments,
    "subscription_id",
    subscriptions,
    "subscription_id"
)

save_dataset(
    payments,
    "payments.csv"
)


# ============================================================
# 6. USAGE METRICS TABLE
# ============================================================

feature_options = [
    "Dashboard",
    "Reports",
    "Inventory",
    "CRM",
    "Financial Management",
    "Human Resources",
    "Analytics",
    "Automation",
    "Integrations"
]

# Customer subscription periods.

customer_periods = {}

for customer_id, group in subscriptions.groupby(
    "customer_id"
):

    periods = []

    for _, subscription in group.iterrows():

        period_end = subscription["end_date"]

        if pd.isna(period_end):
            period_end = END_DATE

        periods.append((
            subscription["start_date"],
            period_end
        ))

    customer_periods[customer_id] = periods


def get_customer_active_date(customer_id):

    periods = customer_periods.get(
        customer_id,
        []
    )

    if not periods:
        return None

    valid_periods = [
        period for period in periods
        if period[0] <= period[1]
    ]

    if not valid_periods:
        return None

    start, end = random.choice(valid_periods)

    return random_date(
        start.to_pydatetime(),
        end.to_pydatetime()
    )


usage_rows = []

valid_customer_ids = list(
    customer_periods.keys()
)

for usage_id in range(
    1,
    NUM_USAGE_METRICS + 1
):

    customer_id = random.choice(
        valid_customer_ids
    )

    usage_date = get_customer_active_date(
        customer_id
    )

    if usage_date is None:
        continue

    login_count = np.random.poisson(8)

    active_minutes = np.random.randint(
        5,
        480
    )

    features_used = random.sample(
        feature_options,
        k=random.randint(1, 5)
    )

    usage_rows.append({

        "usage_id": usage_id,

        "customer_id": customer_id,

        "usage_date": usage_date,

        "login_count": login_count,

        "active_minutes": active_minutes,

        "features_used": "|".join(
            features_used
        ),

        "is_synthetic": True

    })


usage_metrics = pd.DataFrame(
    usage_rows
)

save_dataset(
    usage_metrics,
    "usage_metrics.csv"
)


# ============================================================
# 7. SUPPORT TICKETS TABLE
# ============================================================

ticket_categories = [
    "Technical Issue",
    "Billing",
    "Feature Request",
    "Account Management",
    "Integration",
    "Performance",
    "General Inquiry"
]

ticket_rows = []

for ticket_id in range(
    1,
    NUM_SUPPORT_TICKETS + 1
):

    customer_id = random.choice(
        valid_customer_ids
    )

    created_at = get_customer_active_date(
        customer_id
    )

    if created_at is None:
        continue

    resolution_time = round(
        np.random.exponential(scale=24),
        2
    )

    category = random.choice(
        ticket_categories
    )

    ticket_rows.append({

        "ticket_id": ticket_id,

        "customer_id": customer_id,

        "category": category,

        "created_at": created_at,

        "resolution_time": resolution_time,

        "is_synthetic": True

    })


support_tickets = pd.DataFrame(
    ticket_rows
)

save_dataset(
    support_tickets,
    "support_tickets.csv"
)


# ============================================================
# 8. SUBSCRIPTION FINANCIAL METRICS
# ============================================================

subscription_metrics = subscriptions.merge(
    plans,
    on="plan_id",
    how="left"
)

# Normalize recurring revenue.

subscription_metrics["mrr"] = np.where(
    subscription_metrics["billing_cycle"] == "Annual",
    subscription_metrics["annual_price"] / 12,
    subscription_metrics["monthly_price"]
)

subscription_metrics["arr"] = (
    subscription_metrics["mrr"] * 12
).round(2)

subscription_metrics["mrr"] = (
    subscription_metrics["mrr"].round(2)
)

# Payment metrics by subscription.

payment_agg = payments.groupby(
    "subscription_id"
).agg(

    total_payments=("payment_id", "count"),

    total_paid=(
        "amount",
        lambda x: x[
            payments.loc[x.index, "status"] == "Paid"
        ].sum()
    ),

    failed_payments=(
        "status",
        lambda x: (x == "Failed").sum()
    )

).reset_index()

subscription_metrics = subscription_metrics.merge(
    payment_agg,
    on="subscription_id",
    how="left"
)

subscription_metrics[
    ["total_payments", "total_paid", "failed_payments"]
] = subscription_metrics[
    ["total_payments", "total_paid", "failed_payments"]
].fillna(0)

subscription_metrics["payment_failure_rate"] = np.where(
    subscription_metrics["total_payments"] > 0,
    subscription_metrics["failed_payments"]
    / subscription_metrics["total_payments"],
    0
)

# Usage metrics by customer.

usage_agg = usage_metrics.groupby(
    "customer_id"
).agg(

    total_usage_records=("usage_id", "count"),

    total_logins=("login_count", "sum"),

    total_active_minutes=("active_minutes", "sum")

).reset_index()

subscription_metrics = subscription_metrics.merge(
    usage_agg,
    on="customer_id",
    how="left"
)

# Support metrics by customer.

support_agg = support_tickets.groupby(
    "customer_id"
).agg(

    total_tickets=("ticket_id", "count"),

    avg_resolution_time=("resolution_time", "mean")

).reset_index()

subscription_metrics = subscription_metrics.merge(
    support_agg,
    on="customer_id",
    how="left"
)

# Fill missing activity.

metric_columns = [
    "total_usage_records",
    "total_logins",
    "total_active_minutes",
    "total_tickets"
]

subscription_metrics[metric_columns] = (
    subscription_metrics[metric_columns].fillna(0)
)

subscription_metrics["avg_resolution_time"] = (
    subscription_metrics["avg_resolution_time"].fillna(0)
)

subscription_metrics["is_churned"] = (
    subscription_metrics["status"] == "Cancelled"
).astype(int)

subscription_metrics["is_synthetic"] = True

save_dataset(
    subscription_metrics,
    "subscription_metrics.csv"
)


# ============================================================
# 9. CUSTOMER-LEVEL METRICS
# ============================================================

customer_metrics = subscriptions.groupby(
    "customer_id"
).agg(

    total_subscriptions=("subscription_id", "count"),

    cancelled_subscriptions=(
        "is_churned",
        "sum"
    ) if "is_churned" in subscriptions.columns else (
        "status",
        lambda x: (x == "Cancelled").sum()
    ),

    active_subscriptions=(
        "status",
        lambda x: (x == "Active").sum()
    )

).reset_index()

customer_metrics["has_ever_churned"] = (
    customer_metrics["cancelled_subscriptions"] > 0
).astype(int)

customer_metrics = customers.merge(
    customer_metrics,
    on="customer_id",
    how="left"
)

customer_metrics["total_subscriptions"] = (
    customer_metrics["total_subscriptions"].fillna(0)
)

customer_metrics["cancelled_subscriptions"] = (
    customer_metrics["cancelled_subscriptions"].fillna(0)
)

customer_metrics["active_subscriptions"] = (
    customer_metrics["active_subscriptions"].fillna(0)
)

customer_metrics["has_ever_churned"] = (
    customer_metrics["has_ever_churned"].fillna(0)
)

save_dataset(
    customer_metrics,
    "customer_metrics.csv"
)


# ============================================================
# 10. DATA VALIDATION
# ============================================================

print("\n==========================================")
print("CLOUDFLOW DATA VALIDATION")
print("==========================================")

# Primary keys

validate_unique(customers, "customer_id")

validate_unique(subscriptions, "subscription_id")

validate_unique(payments, "payment_id")

validate_unique(cancellations, "cancellation_id")

validate_unique(usage_metrics, "usage_id")

validate_unique(support_tickets, "ticket_id")


# Foreign keys

validate_foreign_key(
    subscriptions,
    "customer_id",
    customers,
    "customer_id"
)

validate_foreign_key(
    payments,
    "subscription_id",
    subscriptions,
    "subscription_id"
)

validate_foreign_key(
    cancellations,
    "subscription_id",
    subscriptions,
    "subscription_id"
)

validate_foreign_key(
    usage_metrics,
    "customer_id",
    customers,
    "customer_id"
)

validate_foreign_key(
    support_tickets,
    "customer_id",
    customers,
    "customer_id"
)


# Temporal consistency

assert (
    subscriptions["end_date"].isna()
    | (
        subscriptions["end_date"]
        >= subscriptions["start_date"]
    )
).all()

assert (
    cancellations["cancellation_date"]
    >= subscriptions.set_index(
        "subscription_id"
    ).loc[
        cancellations["subscription_id"],
        "start_date"
    ].reset_index(drop=True)
).all()

# Cancellation status consistency

assert (
    subscriptions["status"] == "Cancelled"
).sum() == len(cancellations)

# Payment date consistency

payment_check = payments.merge(
    subscriptions[
        ["subscription_id", "start_date", "end_date"]
    ],
    on="subscription_id",
    how="left"
)

assert (
    payment_check["payment_date"]
    >= payment_check["start_date"]
).all()

assert (
    payment_check["end_date"].isna()
    | (
        payment_check["payment_date"]
        <= payment_check["end_date"]
    )
).all()


# ============================================================
# 11. DATASET SUMMARY
# ============================================================

print("\n==========================================")
print("CLOUDFLOW DATASET GENERATION COMPLETED")
print("==========================================")

datasets = {

    "Customers": customers,

    "Subscriptions": subscriptions,

    "Plans": plans,

    "Payments": payments,

    "Usage Metrics": usage_metrics,

    "Support Tickets": support_tickets,

    "Cancellations": cancellations,

    "Subscription Metrics": subscription_metrics,

    "Customer Metrics": customer_metrics

}

for name, df in datasets.items():

    print(
        f"{name}: {len(df):,} rows"
    )


# ============================================================
# 12. CHURN INDICATORS
# ============================================================

total_subscriptions = len(subscriptions)

total_customers = len(customers)

cancelled_count = (
    subscriptions["status"] == "Cancelled"
).sum()

active_count = (
    subscriptions["status"] == "Active"
).sum()

subscription_churn_rate = (
    cancelled_count / total_subscriptions
    if total_subscriptions else 0
)

customer_churn_rate = (
    customer_metrics["has_ever_churned"].mean()
)

print("\n==========================================")
print("CHURN INDICATORS")
print("==========================================")

print(
    f"Total Customers: {total_customers:,}"
)

print(
    f"Total Subscriptions: {total_subscriptions:,}"
)

print(
    f"Cancelled Subscriptions: {cancelled_count:,}"
)

print(
    f"Active Subscriptions: {active_count:,}"
)

print(
    f"Subscription Churn Rate: "
    f"{subscription_churn_rate:.2%}"
)

print(
    f"Customers with at least one cancellation: "
    f"{customer_churn_rate:.2%}"
)

print("\nOutput directory:", OUTPUT_DIR)

print("\nAll datasets successfully generated!")





