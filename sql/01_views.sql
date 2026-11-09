CREATE OR REPLACE VIEW vw_customer_churn AS

SELECT
    c.customer_id,
    c.region,
    c.industry,
    c.registration_date,

    CASE
        WHEN EXISTS (
            SELECT 1
            FROM cancellations ca
            WHERE ca.customer_id = c.customer_id
        )
        THEN 1
        ELSE 0
    END AS churn_flag,

    (
        SELECT MIN(ca.cancellation_date)
        FROM cancellations ca
        WHERE ca.customer_id = c.customer_id
    ) AS cancellation_date

FROM customers c;
