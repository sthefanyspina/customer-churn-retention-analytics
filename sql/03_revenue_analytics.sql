
CREATE OR REPLACE VIEW vw_customer_usage AS

SELECT
    customer_id,

    COUNT(*) AS usage_records,

    SUM(login_count) AS total_logins,

    AVG(login_count) AS avg_daily_logins,

    SUM(active_minutes) AS total_active_minutes,

    AVG(active_minutes) AS avg_active_minutes,

    AVG(features_used_count) AS avg_features_used

FROM (
    SELECT
        customer_id,
        usage_date,
        login_count,
        active_minutes,

        CASE
            WHEN features_used IS NULL
                 OR features_used = ''
            THEN 0
            ELSE cardinality(
                string_to_array(features_used, '|')
            )
        END AS features_used_count

    FROM usage_metrics
) u

GROUP BY customer_id;
