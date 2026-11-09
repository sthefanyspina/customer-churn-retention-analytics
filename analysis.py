import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ============================================================
# 1. CONFIGURATION
# ============================================================

DATA_DIR = "dataset"
OUTPUT_DIR = "outputs"

CHART_DIR = os.path.join(OUTPUT_DIR, "charts")
REPORT_DIR = os.path.join(OUTPUT_DIR, "reports")

os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

sns.set_theme(style="whitegrid", palette="Set2")

plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["axes.titlesize"] = 14


# ============================================================
# 2. LOAD DATASETS
# ============================================================

customers = pd.read_csv(
    os.path.join(DATA_DIR, "customers.csv")
)

subscriptions = pd.read_csv(
    os.path.join(DATA_DIR, "subscriptions.csv")
)

plans = pd.read_csv(
    os.path.join(DATA_DIR, "plans.csv")
)

payments = pd.read_csv(
    os.path.join(DATA_DIR, "payments.csv")
)

usage = pd.read_csv(
    os.path.join(DATA_DIR, "usage_metrics.csv")
)

support = pd.read_csv(
    os.path.join(DATA_DIR, "support_tickets.csv")
)

cancellations = pd.read_csv(
    os.path.join(DATA_DIR, "cancellations.csv")
)


# ============================================================
# 3. DATA PREPARATION
# ============================================================

date_columns = {
    "customers": (customers, ["registration_date"]),
    "subscriptions": (subscriptions, ["start_date", "end_date"]),
    "payments": (payments, ["payment_date"]),
    "usage": (usage, ["usage_date"]),
    "support": (support, ["created_at"]),
    "cancellations": (cancellations, ["cancellation_date"])
}

for dataframe, columns in date_columns.values():

    for column in columns:

        dataframe[column] = pd.to_datetime(
            dataframe[column],
            errors="coerce"
        )

analysis_date = max(
    df[column].max()
    for df, columns in date_columns.values()
    for column in columns
    if df[column].notna().any()
)

print("\nAnalysis Reference Date:", analysis_date.date())


# ============================================================
# 4. EXPLORATORY DATA ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("EXPLORATORY DATA ANALYSIS")
print("=" * 60)

datasets = {
    "Customers": customers,
    "Subscriptions": subscriptions,
    "Plans": plans,
    "Payments": payments,
    "Usage Metrics": usage,
    "Support Tickets": support,
    "Cancellations": cancellations
}

for name, df in datasets.items():

    print(f"\n{name}")
    print("-" * 40)

    print("Rows:", len(df))
    print("Columns:", len(df.columns))

    print("Missing Values:", df.isnull().sum().sum())

    print("Duplicate Rows:", df.duplicated().sum())

    print("\nData Types:")
    print(df.dtypes)


# Save statistical summaries

customers.describe(include="all").to_csv(
    os.path.join(REPORT_DIR, "customers_summary.csv")
)

payments.describe(include="all").to_csv(
    os.path.join(REPORT_DIR, "payments_summary.csv")
)

usage.describe(include="all").to_csv(
    os.path.join(REPORT_DIR, "usage_summary.csv")
)


# ============================================================
# 5. IDENTIFY ACTIVE AND CANCELLED CUSTOMERS
# ============================================================

print("\n" + "=" * 60)
print("CUSTOMER STATUS ANALYSIS")
print("=" * 60)

subscription_status = (
    subscriptions.groupby("customer_id")["status"]
    .apply(
        lambda x: "Active"
        if (x == "Active").any()
        else "Cancelled"
    )
    .reset_index(name="customer_status")
)

customer_status = customers.merge(
    subscription_status,
    on="customer_id",
    how="left"
)

customer_status["customer_status"] = (
    customer_status["customer_status"]
    .fillna("No Subscription")
)

status_counts = customer_status[
    "customer_status"
].value_counts()

print(status_counts)

status_counts.to_csv(
    os.path.join(REPORT_DIR, "customer_status.csv")
)


# Customer status visualization

plt.figure()

sns.countplot(
    data=customer_status,
    x="customer_status",
    order=[
        "Active",
        "Cancelled",
        "No Subscription"
    ]
)

plt.title("Customer Distribution by Status")
plt.xlabel("Customer Status")
plt.ylabel("Number of Customers")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "customer_status.png")
)

plt.close()


# ============================================================
# 6. CANCELLATION DISTRIBUTION
# ============================================================

print("\n" + "=" * 60)
print("CANCELLATION DISTRIBUTION")
print("=" * 60)

cancellation_reasons = (
    cancellations["reason"].value_counts()
)

print("\nCancellation Reasons:")
print(cancellation_reasons)

cancellation_reasons.to_csv(
    os.path.join(REPORT_DIR, "cancellation_reasons.csv")
)


# Cancellation reasons visualization

plt.figure()

sns.countplot(
    data=cancellations,
    y="reason",
    order=cancellation_reasons.index
)

plt.title("Cancellation Distribution by Reason")
plt.xlabel("Number of Cancellations")
plt.ylabel("Cancellation Reason")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "cancellation_reasons.png")
)

plt.close()


# Monthly cancellations

monthly_cancellations = (
    cancellations
    .set_index("cancellation_date")
    .resample("ME")
    .size()
)

print("\nMonthly Cancellations:")
print(monthly_cancellations.tail(12))

monthly_cancellations.to_csv(
    os.path.join(REPORT_DIR, "monthly_cancellations.csv")
)


plt.figure()

monthly_cancellations.plot(
    kind="line",
    marker="o",
    color="red"
)

plt.title("Monthly Customer Cancellations")
plt.xlabel("Month")
plt.ylabel("Number of Cancellations")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "monthly_cancellations.png")
)

plt.close()


# ============================================================
# 7. CHURN RATE AND RETENTION RATE
# ============================================================

print("\n" + "=" * 60)
print("CHURN RATE ANALYSIS")
print("=" * 60)

total_customers = customers["customer_id"].nunique()

cancelled_customers = (
    cancellations["customer_id"].nunique()
)

churn_rate = (
    cancelled_customers / total_customers
) * 100

retention_rate = 100 - churn_rate

print("Total Customers:", total_customers)

print("Cancelled Customers:", cancelled_customers)

print(f"Churn Rate: {churn_rate:.2f}%")

print(f"Retention Rate: {retention_rate:.2f}%")


churn_summary = pd.DataFrame({

    "metric": [
        "Total Customers",
        "Cancelled Customers",
        "Churn Rate",
        "Retention Rate"
    ],

    "value": [
        total_customers,
        cancelled_customers,
        churn_rate,
        retention_rate
    ]

})

churn_summary.to_csv(
    os.path.join(REPORT_DIR, "churn_summary.csv"),
    index=False
)


# ============================================================
# 8. CUSTOMER USAGE ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("CUSTOMER USAGE ANALYSIS")
print("=" * 60)

usage_summary = usage.groupby(
    "customer_id"
).agg(

    total_logins=("login_count", "sum"),

    average_logins=("login_count", "mean"),

    total_active_minutes=("active_minutes", "sum"),

    average_active_minutes=("active_minutes", "mean"),

    active_days=("usage_date", "nunique")

).reset_index()


usage_summary["average_daily_minutes"] = (
    usage_summary["total_active_minutes"] /
    usage_summary["active_days"].replace(0, np.nan)
)

print(usage_summary.describe())

usage_summary.to_csv(
    os.path.join(REPORT_DIR, "customer_usage_summary.csv"),
    index=False
)


# Login distribution

plt.figure()

sns.histplot(
    usage["login_count"],
    bins=30,
    kde=True,
    color="royalblue"
)

plt.title("Distribution of Customer Login Counts")
plt.xlabel("Login Count")
plt.ylabel("Frequency")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "login_distribution.png")
)

plt.close()


# Active minutes distribution

plt.figure()

sns.histplot(
    usage["active_minutes"],
    bins=30,
    kde=True,
    color="green"
)

plt.title("Distribution of Active Minutes")
plt.xlabel("Active Minutes")
plt.ylabel("Frequency")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "active_minutes_distribution.png")
)

plt.close()


# ============================================================
# 9. USAGE COMPARISON: ACTIVE VS CANCELLED
# ============================================================

usage_status = usage_summary.merge(

    customer_status[
        ["customer_id", "customer_status"]
    ],

    on="customer_id",

    how="left"
)

usage_comparison = usage_status[
    usage_status["customer_status"].isin(
        ["Active", "Cancelled"]
    )
]


usage_comparison = usage_comparison.groupby(
    "customer_status"
).agg(

    average_logins=("average_logins", "mean"),

    average_active_minutes=(
        "average_active_minutes", "mean"
    ),

    average_active_days=("active_days", "mean")

).reset_index()


print("\nUsage Comparison:")
print(usage_comparison)

usage_comparison.to_csv(
    os.path.join(REPORT_DIR, "usage_by_customer_status.csv"),
    index=False
)


plt.figure()

sns.barplot(
    data=usage_comparison,
    x="customer_status",
    y="average_logins"
)

plt.title("Average Login Frequency by Customer Status")
plt.xlabel("Customer Status")
plt.ylabel("Average Login Count")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "usage_by_status.png")
)

plt.close()



# ============================================================
# 10. SUBSCRIPTION PLAN SEGMENTATION
# ============================================================

print("\n" + "=" * 60)
print("SUBSCRIPTION PLAN ANALYSIS")
print("=" * 60)

plan_analysis = subscriptions.merge(
    plans,
    on="plan_id",
    how="left"
)

plan_summary = plan_analysis.groupby(
    "plan_name"
).agg(

    total_subscriptions=("subscription_id", "count"),

    active_subscriptions=(
        "status",
        lambda x: (x == "Active").sum()
    ),

    cancelled_subscriptions=(
        "status",
        lambda x: (x == "Cancelled").sum()
    ),

    average_price=("monthly_price", "mean")

).reset_index()


plan_summary["plan_churn_rate"] = (
    plan_summary["cancelled_subscriptions"] /
    plan_summary["total_subscriptions"] * 100
)

print(plan_summary)

plan_summary.to_csv(
    os.path.join(REPORT_DIR, "plan_analysis.csv"),
    index=False
)


# Churn by subscription plan

plt.figure()

sns.barplot(
    data=plan_summary,
    x="plan_name",
    y="plan_churn_rate"
)

plt.title("Churn Rate by Subscription Plan")
plt.xlabel("Subscription Plan")
plt.ylabel("Churn Rate (%)")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "churn_by_plan.png")
)

plt.close()


# ============================================================
# 11. GEOGRAPHICAL SEGMENTATION
# ============================================================

print("\n" + "=" * 60)
print("GEOGRAPHICAL ANALYSIS")
print("=" * 60)

geo_analysis = customers.merge(

    customer_status[
        ["customer_id", "customer_status"]
    ],

    on="customer_id",

    how="left"
)


geo_summary = geo_analysis.groupby(
    "region"
).agg(

    total_customers=("customer_id", "nunique"),

    cancelled_customers=(
        "customer_status",
        lambda x: (x == "Cancelled").sum()
    ),

    active_customers=(
        "customer_status",
        lambda x: (x == "Active").sum()
    )

).reset_index()


geo_summary["churn_rate"] = (
    geo_summary["cancelled_customers"] /
    geo_summary["total_customers"] * 100
)

print(geo_summary)

geo_summary.to_csv(
    os.path.join(REPORT_DIR, "geographical_analysis.csv"),
    index=False
)


# Regional churn visualization

plt.figure()

sns.barplot(
    data=geo_summary,
    x="region",
    y="churn_rate"
)

plt.title("Customer Churn Rate by Region")
plt.xlabel("Region")
plt.ylabel("Churn Rate (%)")

plt.xticks(rotation=30)

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "churn_by_region.png")
)

plt.close()


# ============================================================
# 12. PAYMENT DEFAULT ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("PAYMENT DEFAULT ANALYSIS")
print("=" * 60)

payment_summary = payments.groupby(
    "status"
).agg(

    total_transactions=("payment_id", "count"),

    total_amount=("amount", "sum")

).reset_index()


print(payment_summary)

payment_summary.to_csv(
    os.path.join(REPORT_DIR, "payment_analysis.csv"),
    index=False
)


payment_failure_rate = (
    (payments["status"] == "Failed").sum() /
    len(payments)
) * 100

print(
    f"\nPayment Failure Rate: {payment_failure_rate:.2f}%"
)


# Payment status visualization

plt.figure()

sns.countplot(
    data=payments,
    x="status",
    order=["Paid", "Failed", "Pending"]
)

plt.title("Payment Status Distribution")
plt.xlabel("Payment Status")
plt.ylabel("Number of Transactions")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "payment_status.png")
)

plt.close()


# Payment failures by subscription

subscription_payment = payments.groupby(
    "subscription_id"
).agg(

    total_payments=("payment_id", "count"),

    failed_payments=(
        "status",
        lambda x: (x == "Failed").sum()
    )

).reset_index()


subscription_payment["failure_rate"] = (
    subscription_payment["failed_payments"] /
    subscription_payment["total_payments"] * 100
)


payment_customer = subscription_payment.merge(

    subscriptions[
        ["subscription_id", "customer_id"]
    ],

    on="subscription_id",

    how="left"
)


customer_payment = payment_customer.groupby(
    "customer_id"
).agg(

    total_failed_payments=("failed_payments", "sum"),

    average_failure_rate=("failure_rate", "mean")

).reset_index()


customer_payment = customer_payment.merge(

    customer_status[
        ["customer_id", "customer_status"]
    ],

    on="customer_id",

    how="left"
)


payment_by_status = customer_payment.groupby(
    "customer_status"
).agg(

    average_failed_payments=(
        "total_failed_payments", "mean"
    ),

    average_failure_rate=(
        "average_failure_rate", "mean"
    )

).reset_index()


print("\nPayment Failures by Customer Status:")
print(payment_by_status)

payment_by_status.to_csv(
    os.path.join(REPORT_DIR, "payment_failures_by_status.csv"),
    index=False
)


# ============================================================
# 13. LOGIN FREQUENCY ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("LOGIN FREQUENCY ANALYSIS")
print("=" * 60)

login_frequency = usage.groupby(
    "customer_id"
).agg(

    total_logins=("login_count", "sum"),

    usage_days=("usage_date", "nunique")

).reset_index()


login_frequency["average_logins_per_day"] = (
    login_frequency["total_logins"] /
    login_frequency["usage_days"].replace(0, np.nan)
)


login_frequency["access_category"] = pd.cut(

    login_frequency["average_logins_per_day"],

    bins=[-np.inf, 2, 5, 10, np.inf],

    labels=[
        "Low Access",
        "Medium Access",
        "High Access",
        "Very High Access"
    ]

)


frequency_summary = (
    login_frequency["access_category"]
    .value_counts()
    .reset_index()
)

frequency_summary.columns = [
    "access_category",
    "customers"
]

print(frequency_summary)

frequency_summary.to_csv(
    os.path.join(REPORT_DIR, "login_frequency.csv"),
    index=False
)


# Login frequency visualization

plt.figure()

sns.countplot(
    data=login_frequency,
    x="access_category",
    order=[
        "Low Access",
        "Medium Access",
        "High Access",
        "Very High Access"
    ]
)

plt.title("Customer Segmentation by Login Frequency")
plt.xlabel("Login Frequency")
plt.ylabel("Number of Customers")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "login_frequency.png")
)

plt.close()


# ============================================================
# 14. CUSTOMER SUPPORT ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("CUSTOMER SUPPORT ANALYSIS")
print("=" * 60)

support_summary = support.groupby(
    "category"
).agg(

    total_tickets=("ticket_id", "count"),

    average_resolution_time=(
        "resolution_time", "mean"
    )

).reset_index()


print(support_summary)

support_summary.to_csv(
    os.path.join(REPORT_DIR, "support_analysis.csv"),
    index=False
)


# Support tickets by category

plt.figure()

sns.barplot(
    data=support_summary,
    x="category",
    y="total_tickets"
)

plt.title("Support Tickets by Category")
plt.xlabel("Ticket Category")
plt.ylabel("Number of Tickets")

plt.xticks(rotation=30)

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "support_tickets.png")
)

plt.close()


# ============================================================
# 15. CORRELATION ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("CORRELATION ANALYSIS")
print("=" * 60)


correlation_data = usage_summary.merge(

    customer_payment[
        [
            "customer_id",
            "total_failed_payments",
            "average_failure_rate"
        ]
    ],

    on="customer_id",

    how="left"
)


support_customer = support.groupby(
    "customer_id"
).agg(

    total_tickets=("ticket_id", "count"),

    avg_resolution_time=("resolution_time", "mean")

).reset_index()


correlation_data = correlation_data.merge(

    support_customer,

    on="customer_id",

    how="left"
)


correlation_data = correlation_data.merge(

    customer_status[
        ["customer_id", "customer_status"]
    ],

    on="customer_id",

    how="left"
)


correlation_data["churn_flag"] = (
    correlation_data["customer_status"] == "Cancelled"
).astype(int)


numeric_columns = [

    "total_logins",

    "average_logins",

    "total_active_minutes",

    "average_active_minutes",

    "total_failed_payments",

    "average_failure_rate",

    "total_tickets",

    "avg_resolution_time",

    "churn_flag"

]


correlation_matrix = correlation_data[
    numeric_columns
].fillna(0).corr()


plt.figure(figsize=(12, 8))

sns.heatmap(
    correlation_matrix,
    annot=True,
    cmap="coolwarm",
    fmt=".2f"
)

plt.title("Customer Churn Correlation Matrix")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "correlation_matrix.png")
)

plt.close()


# ============================================================
# 16. FINAL BUSINESS SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("CLOUDFLOW EDA FINAL SUMMARY")
print("=" * 60)


print(f"""
Total Customers: {total_customers:,}

Cancelled Customers: {cancelled_customers:,}

Churn Rate: {churn_rate:.2f}%

Retention Rate: {retention_rate:.2f}%

Payment Failure Rate: {payment_failure_rate:.2f}%

Total Subscriptions: {len(subscriptions):,}

Total Payments: {len(payments):,}

Total Usage Records: {len(usage):,}

Total Support Tickets: {len(support):,}

Total Cancellations: {len(cancellations):,}
""")


# ============================================================
# 17. EXPORT FINAL REPORT
# ============================================================

final_report = pd.DataFrame({

    "metric": [

        "Total Customers",

        "Cancelled Customers",

        "Churn Rate (%)",

        "Retention Rate (%)",

        "Payment Failure Rate (%)",

        "Total Subscriptions",

        "Total Payments",

        "Total Usage Records",

        "Total Support Tickets",

        "Total Cancellations"

    ],

    "value": [

        total_customers,

        cancelled_customers,

        round(churn_rate, 2),

        round(retention_rate, 2),

        round(payment_failure_rate, 2),

        len(subscriptions),

        len(payments),

        len(usage),

        len(support),

        len(cancellations)

    ]

})


final_report.to_csv(

    os.path.join(REPORT_DIR, "final_business_report.csv"),

    index=False

)


# ============================================================
# END OF CLOUDFLOW EDA
# ============================================================

print("\nEDA successfully completed!")

print("Charts saved in:", CHART_DIR)

print("Reports saved in:", REPORT_DIR)
