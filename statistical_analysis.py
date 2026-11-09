import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

from scipy.stats import chi2_contingency, mannwhitneyu, spearmanr

import statsmodels.api as sm
import statsmodels.formula.api as smf

from statsmodels.stats.multitest import multipletests


# ============================================================
# 1. CONFIGURATION
# ============================================================

DATA_DIR = "dataset"
OUTPUT_DIR = "outputs/statistical_analysis"

CHART_DIR = os.path.join(OUTPUT_DIR, "charts")
REPORT_DIR = os.path.join(OUTPUT_DIR, "reports")

os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

sns.set_theme(style="whitegrid")

ALPHA = 0.05


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
    "registration_date": customers,
    "start_date": subscriptions,
    "end_date": subscriptions,
    "payment_date": payments,
    "usage_date": usage,
    "created_at": support,
    "cancellation_date": cancellations
}

for column, dataframe in date_columns.items():

    dataframe[column] = pd.to_datetime(
        dataframe[column],
        errors="coerce"
    )


analysis_date = max(
    dataframe[column].max()
    for column, dataframe in date_columns.items()
    if dataframe[column].notna().any()
)

print("Analysis Reference Date:", analysis_date)


# ============================================================
# 4. CREATE CUSTOMER-LEVEL CHURN TARGET
# ============================================================

analysis = customers.copy()

cancelled_ids = cancellations[
    "customer_id"
].dropna().unique()

analysis["churn_flag"] = (
    analysis["customer_id"]
    .isin(cancelled_ids)
    .astype(int)
)

analysis["customer_status"] = np.where(
    analysis["churn_flag"] == 1,
    "Cancelled",
    "Not Cancelled"
)

print("\nCustomer Churn Distribution:")

print(
    analysis["customer_status"].value_counts()
)

print(
    "\nChurn Rate:",
    round(analysis["churn_flag"].mean() * 100, 2),
    "%"
)


# ============================================================
# 5. SUBSCRIPTION PLAN ANALYSIS
# ============================================================

latest_subscriptions = (
    subscriptions
    .sort_values("start_date")
    .drop_duplicates(
        subset="customer_id",
        keep="last"
    )
)

analysis = analysis.merge(
    latest_subscriptions[
        [
            "customer_id",
            "subscription_id",
            "plan_id",
            "start_date"
        ]
    ],
    on="customer_id",
    how="left"
)

analysis = analysis.merge(
    plans[
        ["plan_id", "plan_name", "monthly_price"]
    ],
    on="plan_id",
    how="left"
)

analysis["plan_name"] = (
    analysis["plan_name"].fillna("No Subscription")
)


# Chi-square test

plan_contingency = pd.crosstab(
    analysis["plan_name"],
    analysis["churn_flag"]
)

chi2, p_value, dof, expected = chi2_contingency(
    plan_contingency
)

n = plan_contingency.to_numpy().sum()

min_dimension = min(plan_contingency.shape) - 1

cramers_v = np.sqrt(
    chi2 / (n * min_dimension)
) if min_dimension > 0 else np.nan


print("\nPLAN ANALYSIS")

print(plan_contingency)

print("Chi-square:", round(chi2, 4))
print("P-value:", round(p_value, 6))
print("Cramer's V:", round(cramers_v, 4))


plan_results = pd.DataFrame({
    "test": ["Chi-square"],
    "chi_square": [chi2],
    "p_value": [p_value],
    "cramers_v": [cramers_v],
    "degrees_of_freedom": [dof]
})

plan_results.to_csv(
    os.path.join(REPORT_DIR, "plan_churn_test.csv"),
    index=False
)


# Churn rate by plan

plan_rates = (
    analysis.groupby("plan_name")
    .agg(
        customers=("customer_id", "count"),
        cancelled=("churn_flag", "sum"),
        churn_rate=("churn_flag", "mean")
    )
    .reset_index()
)

plan_rates["churn_rate"] *= 100


plt.figure(figsize=(10, 6))

sns.barplot(
    data=plan_rates,
    x="plan_name",
    y="churn_rate"
)

plt.title("Churn Rate by Subscription Plan")
plt.xlabel("Subscription Plan")
plt.ylabel("Churn Rate (%)")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "plan_churn_analysis.png")
)

plt.close()


# ============================================================
# 6. SUBSCRIPTION TENURE ANALYSIS
# ============================================================

first_subscriptions = (
    subscriptions
    .groupby("customer_id")["start_date"]
    .min()
    .reset_index(name="first_subscription_date")
)

analysis = analysis.merge(
    first_subscriptions,
    on="customer_id",
    how="left"
)

analysis["first_subscription_date"] = (
    analysis["first_subscription_date"]
    .fillna(analysis["registration_date"])
)


customer_cancellations = (
    cancellations
    .groupby("customer_id")["cancellation_date"]
    .min()
    .reset_index(name="event_date")
)

analysis = analysis.merge(
    customer_cancellations,
    on="customer_id",
    how="left"
)

analysis["event_date"] = (
    analysis["event_date"].fillna(analysis_date)
)


# Correct invalid date sequences

invalid_tenure = (
    analysis["event_date"] <
    analysis["first_subscription_date"]
)

analysis.loc[
    invalid_tenure,
    "first_subscription_date"
] = analysis.loc[
    invalid_tenure,
    "registration_date"
]


analysis["tenure_months"] = (
    (
        analysis["event_date"] -
        analysis["first_subscription_date"]
    ).dt.days / 30.44
).clip(lower=0)


# Separate customer groups

active_tenure = analysis.loc[
    analysis["churn_flag"] == 0,
    "tenure_months"
].dropna()

churned_tenure = analysis.loc[
    analysis["churn_flag"] == 1,
    "tenure_months"
].dropna()


# Mann-Whitney U test

u_stat, p_value = mannwhitneyu(
    active_tenure,
    churned_tenure,
    alternative="two-sided"
)


print("\nSUBSCRIPTION TENURE ANALYSIS")

print(
    "Average tenure - Not Cancelled:",
    round(active_tenure.mean(), 2),
    "months"
)

print(
    "Average tenure - Cancelled:",
    round(churned_tenure.mean(), 2),
    "months"
)

print("Mann-Whitney U:", round(u_stat, 4))
print("P-value:", round(p_value, 6))


tenure_results = pd.DataFrame({
    "metric": [
        "Not Cancelled Average Tenure",
        "Cancelled Average Tenure",
        "Mann-Whitney U",
        "P-value"
    ],
    "value": [
        active_tenure.mean(),
        churned_tenure.mean(),
        u_stat,
        p_value
    ]
})

tenure_results.to_csv(
    os.path.join(REPORT_DIR, "tenure_analysis.csv"),
    index=False
)


# Visualization

plt.figure(figsize=(9, 6))

sns.boxplot(
    data=analysis,
    x="customer_status",
    y="tenure_months"
)

plt.title("Subscription Tenure by Customer Status")
plt.xlabel("Customer Status")
plt.ylabel("Subscription Tenure (Months)")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "tenure_by_churn.png")
)

plt.close()


# ============================================================
# 7. USAGE FREQUENCY ANALYSIS
# ============================================================

usage_frequency = usage.groupby(
    "customer_id"
).agg(
    total_logins=("login_count", "sum"),
    usage_days=("usage_date", "nunique"),
    average_daily_logins=("login_count", "mean"),
    total_active_minutes=("active_minutes", "sum"),
    average_active_minutes=("active_minutes", "mean")
).reset_index()


analysis = analysis.merge(
    usage_frequency,
    on="customer_id",
    how="left"
)


usage_columns = [
    "total_logins",
    "usage_days",
    "average_daily_logins",
    "total_active_minutes",
    "average_active_minutes"
]

analysis[usage_columns] = (
    analysis[usage_columns].fillna(0)
)


active_usage = analysis.loc[
    analysis["churn_flag"] == 0,
    "average_daily_logins"
]

churned_usage = analysis.loc[
    analysis["churn_flag"] == 1,
    "average_daily_logins"
]


# Mann-Whitney U test

u_stat, p_value = mannwhitneyu(
    active_usage,
    churned_usage,
    alternative="two-sided"
)


print("\nUSAGE FREQUENCY ANALYSIS")

print(
    "Average daily logins - Not Cancelled:",
    round(active_usage.mean(), 2)
)

print(
    "Average daily logins - Cancelled:",
    round(churned_usage.mean(), 2)
)

print("Mann-Whitney U:", round(u_stat, 4))
print("P-value:", round(p_value, 6))


usage_results = pd.DataFrame({
    "metric": [
        "Not Cancelled Average Logins",
        "Cancelled Average Logins",
        "Mann-Whitney U",
        "P-value"
    ],
    "value": [
        active_usage.mean(),
        churned_usage.mean(),
        u_stat,
        p_value
    ]
})

usage_results.to_csv(
    os.path.join(REPORT_DIR, "usage_frequency_test.csv"),
    index=False
)


# Visualization

plt.figure(figsize=(9, 6))

sns.boxplot(
    data=analysis,
    x="customer_status",
    y="average_daily_logins"
)

plt.title("Usage Frequency by Customer Status")
plt.xlabel("Customer Status")
plt.ylabel("Average Daily Logins")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "usage_frequency_churn.png")
)

plt.close()



# ============================================================
# 8. SUPPORT TICKET ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("SUPPORT TICKET ANALYSIS")
print("=" * 60)

support_summary = support.groupby(
    "customer_id"
).agg(
    total_tickets=("ticket_id", "count"),
    average_resolution_time=("resolution_time", "mean")
).reset_index()


analysis = analysis.merge(
    support_summary,
    on="customer_id",
    how="left"
)

analysis["total_tickets"] = (
    analysis["total_tickets"].fillna(0)
)

analysis["average_resolution_time"] = (
    analysis["average_resolution_time"].fillna(0)
)


# Compare customer groups

active_tickets = analysis.loc[
    analysis["churn_flag"] == 0,
    "total_tickets"
]

churned_tickets = analysis.loc[
    analysis["churn_flag"] == 1,
    "total_tickets"
]


# Mann-Whitney U test

u_stat, p_value = mannwhitneyu(
    active_tickets,
    churned_tickets,
    alternative="two-sided"
)


print("\nSUPPORT TICKET RESULTS")

print(
    "Average tickets - Not Cancelled:",
    round(active_tickets.mean(), 2)
)

print(
    "Average tickets - Cancelled:",
    round(churned_tickets.mean(), 2)
)

print("Mann-Whitney U:", round(u_stat, 4))
print("P-value:", round(p_value, 6))


support_results = pd.DataFrame({
    "metric": [
        "Not Cancelled Average Tickets",
        "Cancelled Average Tickets",
        "Mann-Whitney U",
        "P-value"
    ],
    "value": [
        active_tickets.mean(),
        churned_tickets.mean(),
        u_stat,
        p_value
    ]
})

support_results.to_csv(
    os.path.join(REPORT_DIR, "support_churn_test.csv"),
    index=False
)


# Visualization

plt.figure(figsize=(9, 6))

sns.boxplot(
    data=analysis,
    x="customer_status",
    y="total_tickets"
)

plt.title("Support Tickets by Customer Status")
plt.xlabel("Customer Status")
plt.ylabel("Total Support Tickets")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "support_tickets_churn.png")
)

plt.close()


# ============================================================
# 9. PAYMENT DEFAULT ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("PAYMENT DEFAULT ANALYSIS")
print("=" * 60)


payment_summary = payments.groupby(
    "subscription_id"
).agg(
    total_payments=("payment_id", "count"),

    failed_payments=(
        "status",
        lambda x: (x == "Failed").sum()
    )

).reset_index()


payment_summary["failure_rate"] = (
    payment_summary["failed_payments"] /
    payment_summary["total_payments"]
)


# Connect payments with customers

payment_customer = (
    payment_summary
    .merge(
        subscriptions[
            ["subscription_id", "customer_id"]
        ],
        on="subscription_id",
        how="left"
    )
    .groupby("customer_id")
    .agg(
        total_failed_payments=("failed_payments", "sum"),
        average_failure_rate=("failure_rate", "mean")
    )
    .reset_index()
)


analysis = analysis.merge(
    payment_customer,
    on="customer_id",
    how="left"
)


analysis["total_failed_payments"] = (
    analysis["total_failed_payments"].fillna(0)
)

analysis["average_failure_rate"] = (
    analysis["average_failure_rate"].fillna(0)
)


# Define payment failure indicator

analysis["delinquent_flag"] = (
    analysis["total_failed_payments"] > 0
).astype(int)


# Chi-square test

payment_contingency = pd.crosstab(
    analysis["delinquent_flag"],
    analysis["churn_flag"]
)

chi2, p_value, dof, expected = chi2_contingency(
    payment_contingency
)

n = payment_contingency.to_numpy().sum()

min_dimension = min(payment_contingency.shape) - 1

cramers_v = np.sqrt(
    chi2 / (n * min_dimension)
) if min_dimension > 0 else np.nan


print("\nPAYMENT DEFAULT RESULTS")

print(payment_contingency)

print("Chi-square:", round(chi2, 4))
print("P-value:", round(p_value, 6))
print("Cramer's V:", round(cramers_v, 4))


payment_results = pd.DataFrame({
    "chi_square": [chi2],
    "p_value": [p_value],
    "cramers_v": [cramers_v],
    "degrees_of_freedom": [dof]
})

payment_results.to_csv(
    os.path.join(REPORT_DIR, "payment_default_test.csv"),
    index=False
)


# Visualization

plt.figure(figsize=(8, 6))

sns.countplot(
    data=analysis,
    x="delinquent_flag",
    hue="churn_flag"
)

plt.title("Payment Failures vs Customer Churn")

plt.xlabel("Payment Failure")

plt.ylabel("Number of Customers")

plt.xticks(
    [0, 1],
    ["No Failed Payments", "Failed Payments"]
)

plt.legend(
    title="Customer Status",
    labels=["Not Cancelled", "Cancelled"]
)

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "payment_default_churn.png")
)

plt.close()


# ============================================================
# 10. FEATURE USAGE ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("FEATURE USAGE ANALYSIS")
print("=" * 60)


# Split the features_used column

feature_data = usage[
    ["customer_id", "features_used"]
].copy()


feature_data["features_used"] = (
    feature_data["features_used"]
    .fillna("")
    .str.split("|")
)


feature_data = feature_data.explode(
    "features_used"
)

feature_data["features_used"] = (
    feature_data["features_used"].str.strip()
)

feature_data = feature_data[
    feature_data["features_used"] != ""
]


# Count unique features used by each customer

feature_count = feature_data.groupby(
    "customer_id"
).agg(
    unique_features_used=(
        "features_used", "nunique"
    )
).reset_index()


analysis = analysis.merge(
    feature_count,
    on="customer_id",
    how="left"
)

analysis["unique_features_used"] = (
    analysis["unique_features_used"].fillna(0)
)


# Compare feature usage between customer groups

active_features = analysis.loc[
    analysis["churn_flag"] == 0,
    "unique_features_used"
]

churned_features = analysis.loc[
    analysis["churn_flag"] == 1,
    "unique_features_used"
]


u_stat, p_value = mannwhitneyu(
    active_features,
    churned_features,
    alternative="two-sided"
)


print("\nFEATURE USAGE COMPARISON")

print(
    "Average features - Not Cancelled:",
    round(active_features.mean(), 2)
)

print(
    "Average features - Cancelled:",
    round(churned_features.mean(), 2)
)

print("Mann-Whitney U:", round(u_stat, 4))

print("P-value:", round(p_value, 6))


# Individual feature association tests

feature_churn_data = feature_data[
    ["customer_id", "features_used"]
].drop_duplicates()


feature_churn_data = feature_churn_data.merge(
    analysis[
        ["customer_id", "churn_flag"]
    ],
    on="customer_id",
    how="inner"
)


feature_results = []

for feature in sorted(
    feature_churn_data["features_used"].unique()
):

    feature_customers = set(
        feature_churn_data.loc[
            feature_churn_data["features_used"] == feature,
            "customer_id"
        ]
    )

    feature_table = analysis[
        ["customer_id", "churn_flag"]
    ].copy()

    feature_table["uses_feature"] = (
        feature_table["customer_id"]
        .isin(feature_customers)
    )

    contingency = pd.crosstab(
        feature_table["uses_feature"],
        feature_table["churn_flag"]
    )

    contingency = contingency.reindex(
        index=[False, True],
        columns=[0, 1],
        fill_value=0
    )

    chi2, p_value, dof, expected = chi2_contingency(
        contingency
    )

    n = contingency.to_numpy().sum()

    cramers_v = np.sqrt(chi2 / n)

    feature_results.append({
        "feature": feature,
        "chi_square": chi2,
        "p_value": p_value,
        "cramers_v": cramers_v,
        "customers_using_feature": len(feature_customers)
    })


feature_results = pd.DataFrame(feature_results)


# Multiple testing correction

if len(feature_results) > 0:

    reject, adjusted_pvalues, _, _ = multipletests(
        feature_results["p_value"],
        alpha=ALPHA,
        method="fdr_bh"
    )

    feature_results["adjusted_p_value"] = (
        adjusted_pvalues
    )

    feature_results["statistically_significant"] = (
        reject
    )


feature_results.to_csv(
    os.path.join(REPORT_DIR, "feature_usage_tests.csv"),
    index=False
)


# Feature usage visualization

feature_plot = (
    feature_data.groupby("features_used")["customer_id"]
    .nunique()
    .sort_values(ascending=False)
    .reset_index()
)


plt.figure(figsize=(12, 6))

sns.barplot(
    data=feature_plot,
    x="features_used",
    y="customer_id"
)

plt.title("Most Used CloudFlow Features")

plt.xlabel("Feature")

plt.ylabel("Number of Customers")

plt.xticks(
    rotation=35,
    ha="right"
)

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "feature_usage_distribution.png")
)

plt.close()


# ============================================================
# 11. SPEARMAN CORRELATION ANALYSIS
# ============================================================

print("\n" + "=" * 60)
print("SPEARMAN CORRELATION ANALYSIS")
print("=" * 60)


correlation_variables = [
    "tenure_months",
    "average_daily_logins",
    "total_tickets",
    "total_failed_payments",
    "unique_features_used",
    "churn_flag"
]


spearman_matrix = analysis[
    correlation_variables
].corr(method="spearman")


plt.figure(figsize=(11, 8))

sns.heatmap(
    spearman_matrix,
    annot=True,
    cmap="coolwarm",
    center=0,
    fmt=".2f"
)

plt.title("Spearman Correlation - Customer Churn")

plt.tight_layout()

plt.savefig(
    os.path.join(CHART_DIR, "spearman_correlation.png")
)

plt.close()


# Individual correlation tests

spearman_results = []

for variable in correlation_variables[:-1]:

    rho, p_value = spearmanr(
        analysis[variable],
        analysis["churn_flag"]
    )

    spearman_results.append({

        "variable": variable,

        "spearman_rho": rho,

        "p_value": p_value

    })


spearman_results = pd.DataFrame(
    spearman_results
)


# Multiple testing correction

reject, adjusted_pvalues, _, _ = multipletests(
    spearman_results["p_value"],
    alpha=ALPHA,
    method="fdr_bh"
)

spearman_results["adjusted_p_value"] = (
    adjusted_pvalues
)

spearman_results["statistically_significant"] = (
    reject
)


spearman_results.to_csv(
    os.path.join(REPORT_DIR, "spearman_tests.csv"),
    index=False
)


print("\nSpearman Results:")

print(spearman_results)


# ============================================================
# 12. LOGISTIC REGRESSION
# ============================================================

print("\n" + "=" * 60)
print("LOGISTIC REGRESSION ANALYSIS")
print("=" * 60)


model_data = analysis[
    [
        "churn_flag",
        "plan_name",
        "tenure_months",
        "average_daily_logins",
        "total_tickets",
        "delinquent_flag",
        "unique_features_used"
    ]
].copy()


# Remove customers without a subscription plan

model_data = model_data[
    model_data["plan_name"] != "No Subscription"
].dropna()


# Logistic regression formula

formula = """
churn_flag ~
C(plan_name) +
tenure_months +
average_daily_logins +
total_tickets +
delinquent_flag +
unique_features_used
"""


# Fit the logistic regression model

logit_model = smf.glm(
    formula=formula,
    data=model_data,
    family=sm.families.Binomial()
).fit()


print("\nLOGISTIC REGRESSION SUMMARY")

print(logit_model.summary())


# Export coefficients and odds ratios

confidence_intervals = logit_model.conf_int()

coefficients = pd.DataFrame({

    "variable": logit_model.params.index,

    "coefficient": logit_model.params.values,

    "p_value": logit_model.pvalues.values,

    "odds_ratio": np.exp(
        logit_model.params.values
    ),

    "ci_lower": np.exp(
        confidence_intervals[0].values
    ),

    "ci_upper": np.exp(
        confidence_intervals[1].values
    )

})


coefficients["statistically_significant"] = (
    coefficients["p_value"] < ALPHA
)


coefficients.to_csv(
    os.path.join(
        REPORT_DIR,
        "logistic_regression_results.csv"
    ),
    index=False
)


# ============================================================
# 13. FINAL STATISTICAL SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("CLOUDFLOW STATISTICAL ANALYSIS SUMMARY")
print("=" * 60)


print("\nTotal Customers:", len(analysis))

print(
    "Cancelled Customers:",
    analysis["churn_flag"].sum()
)

print(
    "Churn Rate:",
    round(analysis["churn_flag"].mean() * 100, 2),
    "%"
)


print("\nSTATISTICAL TEST RESULTS")

print("\nPlan Association:")

print(
    "P-value:",
    round(plan_results["p_value"].iloc[0], 6)
)


print("\nSubscription Tenure:")

print(
    "P-value:",
    round(tenure_results["value"].iloc[3], 6)
)


print("\nUsage Frequency:")

print(
    "P-value:",
    round(usage_results["value"].iloc[3], 6)
)


print("\nSupport Tickets:")

print(
    "P-value:",
    round(support_results["value"].iloc[3], 6)
)


print("\nPayment Default:")

print(
    "P-value:",
    round(payment_results["p_value"].iloc[0], 6)
)


print("\nFeature Usage:")

print(
    feature_results[
        [
            "feature",
            "adjusted_p_value",
            "statistically_significant"
        ]
    ]
)


# ============================================================
# 14. EXPORT FINAL RESULTS
# ============================================================

final_results = pd.DataFrame({

    "metric": [
        "Total Customers",
        "Cancelled Customers",
        "Churn Rate",
        "Plan Association P-value",
        "Tenure P-value",
        "Usage Frequency P-value",
        "Support Tickets P-value",
        "Payment Default P-value"
    ],

    "value": [

        len(analysis),

        analysis["churn_flag"].sum(),

        analysis["churn_flag"].mean() * 100,

        plan_results["p_value"].iloc[0],

        tenure_results["value"].iloc[3],

        usage_results["value"].iloc[3],

        support_results["value"].iloc[3],

        payment_results["p_value"].iloc[0]

    ]

})


final_results.to_csv(
    os.path.join(
        REPORT_DIR,
        "final_statistical_summary.csv"
    ),
    index=False
)


# ============================================================
# 15. COMPLETION
# ============================================================

print("\n" + "=" * 60)

print("STATISTICAL ANALYSIS COMPLETED SUCCESSFULLY!")

print("=" * 60)

print("\nReports saved in:", REPORT_DIR)

print("Charts saved in:", CHART_DIR)
