
import pandas as pd
import numpy as np
import random
import os

from datetime import datetime, timedelta

# ============================================================
# CLOUDFLOW - CUSTOMER CHURN & RETENTION DATASET GENERATOR
# ============================================================

# Reproducibility
np.random.seed(42)
random.seed(42)

# Configuration
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
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def save_dataset(dataframe, filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    dataframe.to_csv(filepath, index=False)
    print(f"Generated: {filename} - {len(dataframe):,} records")


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
    "monthly_price": [29.90, 59.90, 119.90, 249.90]
})

plans["annual_price"] = plans["monthly_price"] * 10

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
    "customer_id": range(1, NUM_CUSTOMERS + 1),
    "region": np.random.choice(
        regions,
        NUM_CUSTOMERS,
        p=[0.30, 0.18, 0.22, 0.16, 0.08, 0.06]
    ),
    "industry": np.random.choice(industries, NUM_CUSTOMERS),
    "registration_date": [
        random_date(START_DATE, END_DATE).date()
        for _ in range(NUM_CUSTOMERS)
    ]
})

save_dataset(customers, "customers.csv")


# ============================================================
# 3. SUBSCRIPTIONS TABLE
# ============================================================

customer_ids = customers["customer_id"].tolist()

subscription_rows = []

for subscription_id in range(1, NUM_SUBSCRIPTIONS + 1):

    customer_id = random.choice(customer_ids)

    plan_id = random.choices(
        [1, 2, 3, 4],
        weights=[0.35, 0.35, 0.20, 0.10]
    )[0]

    start_date = random_date(START_DATE, END_DATE)

    billing_cycle = random.choice(["Monthly", "Annual"])

    is_cancelled = random.random() < 0.23

    if is_cancelled:
        end_date = random_date(start_date, END_DATE)
        status = "Cancelled"
    else:
        end_date = None
        status = "Active"

    subscription_rows.append({
        "subscription_id": subscription_id,
        "customer_id": customer_id,
        "plan_id": plan_id,
        "start_date": start_date.date(),
        "end_date": end_date.date() if end_date else None,
        "status": status,
        "billing_cycle": billing_cycle
    })

subscriptions = pd.DataFrame(subscription_rows)

save_dataset(subscriptions, "subscriptions.csv")


# ============================================================
# 4. CANCELLATIONS TABLE
# ============================================================

cancelled_subscriptions = subscriptions[
    subscriptions["status"] == "Cancelled"
].copy()

cancelled_subscriptions = cancelled_subscriptions.drop_duplicates(
    subset=["customer_id"]
)

cancelled_subscriptions = cancelled_subscriptions.head(
    NUM_CANCELLATIONS
)

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
        1, len(cancelled_subscriptions) + 1
    ),
    "customer_id": cancelled_subscriptions["customer_id"].values,
    "cancellation_date": cancelled_subscriptions["end_date"].values,
    "reason": np.random.choice(
        cancellation_reasons,
        len(cancelled_subscriptions),
        p=[0.18, 0.12, 0.14, 0.18, 0.12, 0.12, 0.06, 0.08]
    )
})

save_dataset(cancellations, "cancellations.csv")


# ============================================================
# 5. PAYMENTS TABLE
# ============================================================

payment_rows = []

subscription_lookup = subscriptions.set_index("subscription_id")

for payment_id in range(1, NUM_PAYMENTS + 1):

    subscription_id = random.randint(1, NUM_SUBSCRIPTIONS)

    subscription = subscription_lookup.loc[subscription_id]

    plan_id = subscription["plan_id"]
    billing_cycle = subscription["billing_cycle"]

    monthly_price = plans.loc[
        plans["plan_id"] == plan_id,
        "monthly_price"
    ].iloc[0]

    amount = monthly_price * 12 if billing_cycle == "Annual" else monthly_price

    payment_date = random_date(START_DATE, END_DATE)

    payment_status = random.choices(
        ["Paid", "Failed", "Pending"],
        weights=[0.90, 0.07, 0.03]
    )[0]

    if payment_status == "Failed":
        amount = round(amount, 2)
    else:
        amount = round(amount, 2)

    payment_rows.append({
        "payment_id": payment_id,
        "subscription_id": subscription_id,
        "amount": amount,
        "payment_date": payment_date.date(),
        "status": payment_status
    })

payments = pd.DataFrame(payment_rows)

save_dataset(payments, "payments.csv")


# ============================================================
# 6. USAGE METRICS TABLE
# ============================================================

usage_rows = []

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

for _ in range(NUM_USAGE_METRICS):

    customer_id = random.choice(customer_ids)

    usage_date = random_date(START_DATE, END_DATE)

    login_count = np.random.poisson(8)

    active_minutes = np.random.randint(5, 480)

    features_used = random.sample(
        feature_options,
        k=random.randint(1, 5)
    )

    usage_rows.append({
        "customer_id": customer_id,
        "usage_date": usage_date.date(),
        "login_count": login_count,
        "active_minutes": active_minutes,
        "features_used": "|".join(features_used)
    })

usage_metrics = pd.DataFrame(usage_rows)

save_dataset(usage_metrics, "usage_metrics.csv")


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

for ticket_id in range(1, NUM_SUPPORT_TICKETS + 1):

    customer_id = random.choice(customer_ids)

    created_at = random_date(START_DATE, END_DATE)

    resolution_time = round(
        np.random.exponential(scale=24), 2
    )

    category = random.choice(ticket_categories)

    ticket_rows.append({
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "category": category,
        "created_at": created_at,
        "resolution_time": resolution_time
    })

support_tickets = pd.DataFrame(ticket_rows)

save_dataset(support_tickets, "support_tickets.csv")


# ============================================================
# 8. DATASET VALIDATION
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
    "Cancellations": cancellations
}

for name, df in datasets.items():
    print(f"{name}: {len(df):,} rows")

print("\nOutput directory:", OUTPUT_DIR)

print("\nDataset files successfully generated!")
