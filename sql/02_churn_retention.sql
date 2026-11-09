
CREATE OR REPLACE VIEW vw_subscription_details AS

SELECT
    s.subscription_id,
    s.customer_id,
    s.plan_id,
    p.plan_name,
    p.monthly_price,

    s.start_date,
    s.end_date,
    s.status,

    c.region,
    c.industry,
    c.registration_date

FROM subscriptions s

INNER JOIN customers c
    ON s.customer_id = c.customer_id

INNER JOIN plans p
    ON s.plan_id = p.plan_id;
