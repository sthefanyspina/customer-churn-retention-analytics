
import pandas as pd
import numpy as np
import random
import os

from datetime import datetime, timedelta

# =====================================================
# 1. CONFIGURAÇÕES
# =====================================================

SEED = 42

np.random.seed(SEED)
random.seed(SEED)

OUTPUT_DIR = "cloudflow_dataset"

os.makedirs(OUTPUT_DIR, exist_ok=True)

N_CUSTOMERS = 50_000
N_SUBSCRIPTIONS = 65_000
N_PAYMENTS = 600_000
N_USAGE = 1_000_000
N_TICKETS = 150_000
N_CANCELLATIONS = 15_000

START_DATE = pd.Timestamp("2023-01-01")
END_DATE = pd.Timestamp("2025-12-31")

DATE_RANGE_DAYS = (END_DATE - START_DATE).days

# =====================================================
# 2. PLANOS
# =====================================================

plans = pd.DataFrame({
    "plan_id": [1, 2, 3, 4],
    "plan_name": [
        "Basic",
        "Professional",
        "Business",
        "Enterprise"
    ],
    "monthly_price": [49.90, 99.90, 199.90, 499.90]
})

plans["annual_price"] = plans["monthly_price"] * 10

# =====================================================
# 3. CUSTOMERS
# =====================================================

regions = [
    "Southeast",
    "South",
    "Northeast",
    "Central-West",
    "North"
]

industries = [
    "Technology",
    "Retail",
    "Healthcare",
    "Finance",
    "Education",
    "Manufacturing",
    "Logistics",
    "Consulting",
    "Food",
    "Construction"
]

customers = pd.DataFrame({
    "customer_id": np.arange(1, N_CUSTOMERS + 1),

    "region": np.random.choice(
        regions,
        N_CUSTOMERS,
        p=[0.45, 0.20, 0.15, 0.12, 0.08]
    ),

    "industry": np.random.choice(
        industries,
        N_CUSTOMERS
    ),

    "registration_date": START_DATE +
        pd.to_timedelta(
            np.random.randint(
                0,
                DATE_RANGE_DAYS + 1,
                N_CUSTOMERS
            ),
            unit="D"
        )
})

# =====================================================
# 4. SUBSCRIPTIONS
# =====================================================

subscription_customers = np.random.choice(
    customers["customer_id"],
    N_SUBSCRIPTIONS,
    replace=True
)

subscription_start = (
    customers.set_index("customer_id")
    .loc[subscription_customers, "registration_date"]
    .reset_index(drop=True)
)

plan_ids = np.random.choice(
    [1, 2, 3, 4],
    N_SUBSCRIPTIONS,
    p=[0.35, 0.35, 0.20, 0.10]
)

billing_cycles = np.random.choice(
    ["Monthly", "Annual"],
    N_SUBSCRIPTIONS,
    p=[0.75, 0.25]
)

subscription_end = [
    min(
        START_DATE + pd.Timedelta(days=DATE_RANGE_DAYS),
        start + pd.Timedelta(
            days=int(np.random.randint(30, 1000))
        )
    )
    for start in subscription_start
]

subscriptions = pd.DataFrame({
    "subscription_id": np.arange(1, N_SUBSCRIPTIONS + 1),
    "customer_id": subscription_customers,
    "plan_id": plan_ids,
    "billing_cycle": billing_cycles,
    "start_date": subscription_start,
    "end_date": subscription_end
})

subscriptions["status"] = np.where(
    subscriptions["end_date"] < END_DATE,
    "Cancelled",
    "Active"
)

# =====================================================
# 5. CANCELLATIONS
# =====================================================

cancelled_customers = np.random.choice(
    customers["customer_id"],
    N_CANCELLATIONS,
    replace=False
)

cancellation_reasons = [
    "High Price",
    "Poor Customer Support",
    "Low Usage",
    "Missing Features",
    "Financial Problems",
    "Competitor",
    "Technical Issues"
]

reason_probabilities = [
    0.20, 0.15, 0.25, 0.12, 0.10, 0.10, 0.08
]

cancellations = pd.DataFrame({
    "cancellation_id": np.arange(
        1, N_CANCELLATIONS + 1
    ),

    "customer_id": cancelled_customers,

    "cancellation_date": START_DATE +
        pd.to_timedelta(
            np.random.randint(
                30,
                DATE_RANGE_DAYS + 1,
                N_CANCELLATIONS
            ),
            unit="D"
        ),

    "reason": np.random.choice(
        cancellation_reasons,
        N_CANCELLATIONS,
        p=reason_probabilities
    )
})

# Atualiza o status das assinaturas dos clientes cancelados
cancelled_ids = set(cancelled_customers)

subscriptions.loc[
    subscriptions["customer_id"].isin(cancelled_ids),
    "status"
] = "Cancelled"

# =====================================================
# 6. PAYMENTS
# =====================================================

payment_subscriptions = np.random.choice(
    subscriptions["subscription_id"],
    N_PAYMENTS
)

subscription_lookup = subscriptions.set_index(
    "subscription_id"
)

payment_plan_ids = subscription_lookup.loc[
    payment_subscriptions, "plan_id"
].to_numpy()

payment_cycles = subscription_lookup.loc[
    payment_subscriptions, "billing_cycle"
].to_numpy()

price_lookup = plans.set_index("plan_id")["monthly_price"]

payment_prices = np.array([
    price_lookup.loc[plan_id]
    for plan_id in payment_plan_ids
])

payment_amounts = np.where(
    payment_cycles == "Annual",
    payment_prices * 10,
    payment_prices
)

payment_dates = START_DATE + pd.to_timedelta(
    np.random.randint(
        0,
        DATE_RANGE_DAYS + 1,
        N_PAYMENTS
    ),
    unit="D"
)

payment_status = np.random.choice(
    ["Paid", "Failed", "Pending"],
    N_PAYMENTS,
    p=[0.90, 0.07, 0.03]
)

payments = pd.DataFrame({
    "payment_id": np.arange(1, N_PAYMENTS + 1),
    "subscription_id": payment_subscriptions,
    "amount": np.round(payment_amounts, 2),
    "payment_date": payment_dates,
    "status": payment_status
})

# =====================================================
# 7. USAGE METRICS
# =====================================================

usage_customers = np.random.choice(
    customers["customer_id"],
    N_USAGE
)

usage_dates = START_DATE + pd.to_timedelta(
    np.random.randint(
        0,
        DATE_RANGE_DAYS + 1,
        N_USAGE
    ),
    unit="D"
)

# Clientes possuem diferentes níveis de utilização
login_count = np.random.poisson(
    lam=5,
    size=N_USAGE
)

active_minutes = np.random.gamma(
    shape=2,
    scale=30,
    size=N_USAGE
).astype(int)

features_used = np.random.poisson(
    lam=4,
    size=N_USAGE
)

usage_metrics = pd.DataFrame({
    "customer_id": usage_customers,
    "usage_date": usage_dates,
    "login_count": login_count,
    "active_minutes": active_minutes,
    "features_used": features_used
})

# =====================================================
# 8. SUPPORT TICKETS
# =====================================================

ticket_customers = np.random.choice(
    customers["customer_id"],
    N_TICKETS
)

ticket_categories = [
    "Technical Issue",
    "Billing",
    "Account Access",
    "Feature Request",
    "Bug Report",
    "Integration"
]

ticket_created_dates = START_DATE + pd.to_timedelta(
    np.random.randint(
        0,
        DATE_RANGE_DAYS + 1,
        N_TICKETS
    ),
    unit="D"
)

resolution_times = np.random.gamma(
    shape=2,
    scale=12,
    size=N_TICKETS
).astype(int)

support_tickets = pd.DataFrame({
    "ticket_id": np.arange(1, N_TICKETS + 1),

    "customer_id": ticket_customers,

    "category": np.random.choice(
        ticket_categories,
        N_TICKETS,
        p=[0.25, 0.20, 0.15, 0.12, 0.18, 0.10]
    ),

    "created_at": ticket_created_dates,

    "resolution_time": resolution_times
})

# =====================================================
# 9. EXPORTAÇÃO DOS DATASETS
# =====================================================

tables = {
    "customers": customers,
    "subscriptions": subscriptions,
    "plans": plans,
    "payments": payments,
    "usage_metrics": usage_metrics,
    "support_tickets": support_tickets,
    "cancellations": cancellations
}

for table_name, dataframe in tables.items():

    filepath = os.path.join(
        OUTPUT_DIR,
        f"{table_name}.csv"
    )

    dataframe.to_csv(
        filepath,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"{table_name}: "
        f"{len(dataframe):,} registros gerados"
    )

# =====================================================
# 10. RESUMO FINAL
# =====================================================

print("\n===================================")
print("CLOUDFLOW DATASET GERADO!")
print("===================================")

for name, df in tables.items():
    print(f"{name}: {len(df):,} registros")

print("\nArquivos salvos em:", OUTPUT_DIR)
