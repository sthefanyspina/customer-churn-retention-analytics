View 1 — Customer Churn Status
Identifica clientes cancelados e não cancelados.


sql

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
View 2 — Customer Subscription Details
Consolida informações de clientes, assinaturas e planos.


sql

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
View 3 — Customer Usage Summary
Consolida indicadores de utilização.


sql

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
Esta view pressupõe que features_used seja armazenado como texto separado por |, conforme o gerador de dataset apresentado anteriormente.

3. Análises SQL — Indicadores principais
1. Churn mensal
Calcula quantos clientes cancelaram em cada mês e a taxa de churn mensal.

A taxa será calculada usando como denominador os clientes com assinatura ativa no início do mês.


sql

WITH monthly_cancellations AS (

    SELECT
        DATE_TRUNC('month', cancellation_date)::date AS month,
        COUNT(DISTINCT customer_id) AS cancelled_customers

    FROM cancellations

    GROUP BY 1
),

monthly_base AS (

    SELECT
        m.month,

        COUNT(DISTINCT s.customer_id) AS active_at_start

    FROM generate_series(
        (SELECT MIN(DATE_TRUNC('month', start_date))
         FROM subscriptions),
        (SELECT MAX(DATE_TRUNC('month', start_date))
         FROM subscriptions),
        INTERVAL '1 month'
    ) AS m(month)

    LEFT JOIN subscriptions s
        ON s.start_date < m.month
        AND (
            s.end_date IS NULL
            OR s.end_date >= m.month
        )

    GROUP BY m.month
)

SELECT
    b.month,
    b.active_at_start,

    COALESCE(c.cancelled_customers, 0)
        AS cancelled_customers,

    ROUND(
        100.0 * COALESCE(c.cancelled_customers, 0)
        / NULLIF(b.active_at_start, 0),
        2
    ) AS monthly_churn_rate

FROM monthly_base b

LEFT JOIN monthly_cancellations c
    ON b.month = c.month

ORDER BY b.month;
2. Retenção mensal
Calcula o percentual de clientes que continuam ativos no final de cada mês em relação à base ativa no início daquele mês.


sql

WITH monthly_activity AS (

    SELECT
        m.month,

        COUNT(DISTINCT s.customer_id)
            FILTER (
                WHERE s.start_date < m.month
                  AND (
                      s.end_date IS NULL
                      OR s.end_date >= m.month
                  )
            ) AS active_start,

        COUNT(DISTINCT s.customer_id)
            FILTER (
                WHERE s.start_date < m.month + INTERVAL '1 month'
                  AND (
                      s.end_date IS NULL
                      OR s.end_date >= m.month + INTERVAL '1 month'
                  )
            ) AS active_end

    FROM generate_series(
        DATE '2023-01-01',
        DATE '2025-12-01',
        INTERVAL '1 month'
    ) AS m(month)

    CROSS JOIN subscriptions s

    GROUP BY m.month
)

SELECT
    month,
    active_start,
    active_end,

    ROUND(
        100.0 * active_end /
        NULLIF(active_start, 0),
        2
    ) AS retention_rate

FROM monthly_activity

ORDER BY month;
As datas acima são ilustrativas. Ajuste ao período real do dataset. Esta métrica considera assinaturas ativas no início e no final do mês, portanto não é exatamente a retenção da mesma coorte de clientes; essa será analisada na seção de Cohort.

3. MRR — Monthly Recurring Revenue
Calcula a receita recorrente mensal normalizada das assinaturas ativas.

Para planos anuais, a receita deve ser dividida por 12. Para planos mensais, permanece integral.

Premissa: a tabela subscriptions precisa possuir a coluna billing_cycle, com valores Monthly e Annual. A estrutura original informada não possui esse campo, então será necessário adicioná-lo ou adaptar a consulta.


sql

SELECT
    DATE_TRUNC('month', m.month)::date AS month,

    ROUND(
        SUM(
            CASE
                WHEN s.billing_cycle = 'Annual'
                    THEN p.monthly_price
                ELSE p.monthly_price
            END
        ),
        2
    ) AS mrr

FROM generate_series(
    DATE '2023-01-01',
    DATE '2025-12-01',
    INTERVAL '1 month'
) AS m(month)

JOIN subscriptions s
    ON s.start_date < m.month + INTERVAL '1 month'
    AND (
        s.end_date IS NULL
        OR s.end_date >= m.month + INTERVAL '1 month'
    )

JOIN plans p
    ON s.plan_id = p.plan_id

GROUP BY 1

ORDER BY 1;
Neste exemplo, monthly_price já representa o preço mensal equivalente, inclusive para planos anuais. Portanto, não dividimos novamente por 12.

4. ARR — Annual Recurring Revenue
O ARR representa o MRR multiplicado por 12.


sql

WITH monthly_revenue AS (

    SELECT
        SUM(p.monthly_price) AS mrr

    FROM subscriptions s

    JOIN plans p
        ON s.plan_id = p.plan_id

    WHERE s.start_date <= CURRENT_DATE

      AND (
          s.end_date IS NULL
          OR s.end_date > CURRENT_DATE
      )
)

SELECT
    ROUND(mrr, 2) AS current_mrr,

    ROUND(mrr * 12, 2) AS current_arr

FROM monthly_revenue;
5. Churn por plano
Identifica quais planos apresentam maior taxa de cancelamento.


sql

SELECT
    p.plan_name,

    COUNT(DISTINCT s.customer_id) AS total_customers,

    COUNT(DISTINCT ca.customer_id) AS cancelled_customers,

    ROUND(
        100.0 *
        COUNT(DISTINCT ca.customer_id)
        / NULLIF(COUNT(DISTINCT s.customer_id), 0),
        2
    ) AS churn_rate

FROM subscriptions s

JOIN plans p
    ON s.plan_id = p.plan_id

LEFT JOIN cancellations ca
    ON s.customer_id = ca.customer_id

GROUP BY p.plan_name

ORDER BY churn_rate DESC;
6. Churn por região
Identifica as regiões com maior concentração de cancelamentos.


sql

SELECT
    c.region,

    COUNT(DISTINCT c.customer_id) AS total_customers,

    COUNT(DISTINCT ca.customer_id) AS cancelled_customers,

    ROUND(
        100.0 *
        COUNT(DISTINCT ca.customer_id)
        / NULLIF(COUNT(DISTINCT c.customer_id), 0),
        2
    ) AS churn_rate

FROM customers c

LEFT JOIN cancellations ca
    ON c.customer_id = ca.customer_id

GROUP BY c.region

ORDER BY churn_rate DESC;
7. Tempo médio de permanência
Calcula o tempo médio entre o início e o encerramento das assinaturas.

Para clientes ainda ativos, a data de referência será a data atual.


sql

WITH customer_lifetime AS (

    SELECT
        customer_id,
        subscription_id,
        start_date,

        COALESCE(
            end_date,
            CURRENT_DATE
        ) AS reference_date,

        CASE
            WHEN end_date IS NULL THEN 0
            ELSE 1
        END AS churn_event

    FROM subscriptions
)

SELECT
    ROUND(
        AVG(
            reference_date - start_date
        ) / 30.44,
        2
    ) AS average_lifetime_months,

    ROUND(
        AVG(
            reference_date - start_date
        ),
        2
    ) AS average_lifetime_days

FROM customer_lifetime;
Observação: essa média simples não substitui uma análise de sobrevivência. Clientes ativos têm observações censuradas à direita e devem ser tratados como tais, não como cancelamentos.

8. Receita perdida com cancelamentos
Calcula a receita recorrente mensal perdida em decorrência dos cancelamentos.


sql

SELECT
    DATE_TRUNC(
        'month',
        ca.cancellation_date
    )::date AS cancellation_month,

    COUNT(DISTINCT ca.customer_id)
        AS cancelled_customers,

    ROUND(
        SUM(p.monthly_price),
        2
    ) AS lost_mrr,

    ROUND(
        SUM(p.monthly_price * 12),
        2
    ) AS lost_arr

FROM cancellations ca

JOIN subscriptions s
    ON ca.customer_id = s.customer_id

JOIN plans p
    ON s.plan_id = p.plan_id

WHERE s.start_date <= ca.cancellation_date

  AND (
      s.end_date IS NULL
      OR s.end_date >= ca.cancellation_date
  )

GROUP BY 1

ORDER BY 1;
Essa consulta considera a receita mensal equivalente perdida. Para evitar duplicidade, em clientes com múltiplas assinaturas será necessário associar cada cancelamento à assinatura específica correspondente, idealmente utilizando subscription_id na tabela cancellations.

9. Clientes com queda de utilização
Utiliza LAG() para comparar a utilização mensal atual com o mês anterior.

Consideraremos queda superior a 30%.


sql

WITH monthly_usage AS (

    SELECT
        customer_id,

        DATE_TRUNC(
            'month',
            usage_date
        )::date AS month,

        SUM(login_count) AS monthly_logins

    FROM usage_metrics

    GROUP BY 1, 2
),

usage_comparison AS (

    SELECT
        customer_id,
        month,
        monthly_logins,

        LAG(monthly_logins) OVER (
            PARTITION BY customer_id
            ORDER BY month
        ) AS previous_month_logins

    FROM monthly_usage
)

SELECT
    customer_id,
    month,
    previous_month_logins,
    monthly_logins,

    ROUND(
        100.0 *
        (
            previous_month_logins - monthly_logins
        ) /
        NULLIF(previous_month_logins, 0),
        2
    ) AS usage_drop_percentage

FROM usage_comparison

WHERE previous_month_logins > 0

  AND monthly_logins <
      previous_month_logins * 0.70

ORDER BY usage_drop_percentage DESC;
Essa consulta pode ajudar a identificar clientes com sinais de desengajamento antes do cancelamento.

10. Clientes com pagamentos atrasados
A estrutura original de payments não possui due_date (data de vencimento). Para uma análise real de atraso, precisamos adicionar essa informação.

A consulta abaixo considera pagamentos ainda não pagos e vencidos.


sql

SELECT
    p.payment_id,
    s.customer_id,
    s.subscription_id,

    p.payment_date,
    p.due_date,

    p.amount,
    p.status,

    CURRENT_DATE - p.due_date AS days_overdue

FROM payments p

JOIN subscriptions s
    ON p.subscription_id = s.subscription_id

WHERE p.due_date < CURRENT_DATE

  AND p.status IN ('Pending', 'Failed')

ORDER BY days_overdue DESC;
Para que essa consulta funcione, adicione due_date à tabela payments.


sql
ALTER TABLE payments
ADD COLUMN due_date DATE;
4. Análises avançadas
Agora vamos desenvolver as análises mais importantes para um projeto de Customer Churn Analytics.

Essas consultas são especialmente interessantes para demonstrar domínio de SQL analítico, métricas SaaS e análise de comportamento de clientes.

A. Churn Rate — Taxa de cancelamento
Vamos calcular o churn mensal considerando a base de clientes ativos no início do período.


sql

WITH monthly_churn AS (

    SELECT
        DATE_TRUNC(
            'month',
            cancellation_date
        )::date AS month,

        COUNT(DISTINCT customer_id) AS churned_customers

    FROM cancellations

    GROUP BY 1
),

monthly_customers AS (

    SELECT
        m.month,

        COUNT(DISTINCT s.customer_id) AS customers_at_start

    FROM generate_series(
        DATE '2023-01-01',
        DATE '2025-12-01',
        INTERVAL '1 month'
    ) AS m(month)

    LEFT JOIN subscriptions s
        ON s.start_date < m.month
        AND (
            s.end_date IS NULL
            OR s.end_date >= m.month
        )

    GROUP BY 1
)

SELECT
    mc.month,

    mc.customers_at_start,

    COALESCE(ch.churned_customers, 0)
        AS churned_customers,

    ROUND(
        100.0 *
        COALESCE(ch.churned_customers, 0)
        / NULLIF(mc.customers_at_start, 0),
        2
    ) AS churn_rate

FROM monthly_customers mc

LEFT JOIN monthly_churn ch
    ON mc.month = ch.month

ORDER BY mc.month;
Interpretação de negócio: permite identificar meses com maior volume de cancelamentos e avaliar se ações de retenção estão funcionando.

B. Retention Rate — Taxa de retenção
Aqui vamos calcular a retenção de uma coorte de clientes, acompanhando quantos permanecem ativos ao longo dos meses.


sql

WITH customer_cohorts AS (

    SELECT
        customer_id,

        DATE_TRUNC(
            'month',
            MIN(start_date)
        )::date AS cohort_month

    FROM subscriptions

    GROUP BY customer_id
),

customer_activity AS (

    SELECT DISTINCT
        customer_id,

        DATE_TRUNC(
            'month',
            start_date
        )::date AS activity_month

    FROM subscriptions

    UNION

    SELECT DISTINCT
        customer_id,

        DATE_TRUNC(
            'month',
            usage_date
        )::date AS activity_month

    FROM usage_metrics
),

cohort_activity AS (

    SELECT
        cc.cohort_month,

        ca.activity_month,

        (
            EXTRACT(YEAR FROM ca.activity_month) -
            EXTRACT(YEAR FROM cc.cohort_month)
        ) * 12 +

        (
            EXTRACT(MONTH FROM ca.activity_month) -
            EXTRACT(MONTH FROM cc.cohort_month)
        ) AS month_number,

        COUNT(DISTINCT cc.customer_id)
            AS retained_customers

    FROM customer_cohorts cc

    JOIN customer_activity ca
        ON cc.customer_id = ca.customer_id

    JOIN subscriptions s
        ON cc.customer_id = s.customer_id
        AND s.start_date <= ca.activity_month
        AND (
            s.end_date IS NULL
            OR s.end_date >= ca.activity_month
        )

    GROUP BY
        cc.cohort_month,
        ca.activity_month
),

cohort_size AS (

    SELECT
        cohort_month,

        COUNT(*) AS total_customers

    FROM customer_cohorts

    GROUP BY cohort_month
)

SELECT
    ca.cohort_month,

    ca.month_number,

    cs.total_customers,

    ca.retained_customers,

    ROUND(
        100.0 * ca.retained_customers /
        NULLIF(cs.total_customers, 0),
        2
    ) AS retention_rate

FROM cohort_activity ca

JOIN cohort_size cs
    ON ca.cohort_month = cs.cohort_month

WHERE ca.month_number >= 0

ORDER BY
    ca.cohort_month,
    ca.month_number;
Interpretação de negócio: permite descobrir se os clientes adquiridos em determinados meses apresentam maior ou menor retenção.

Para uma análise de retenção contratual rigorosa, a atividade deve ser definida pela vigência da assinatura, não apenas por login ou utilização.

C. MRR — Receita recorrente mensal por assinatura
Nesta versão, calculamos o MRR individual de cada assinatura, considerando o ciclo de cobrança.


sql

WITH subscription_mrr AS (

    SELECT
        s.subscription_id,
        s.customer_id,
        s.plan_id,

        s.start_date,
        s.end_date,

        s.billing_cycle,

        p.plan_name,
        p.monthly_price,

        CASE
            WHEN s.billing_cycle = 'Annual'
                THEN p.monthly_price

            WHEN s.billing_cycle = 'Monthly'
                THEN p.monthly_price

            ELSE 0
        END AS normalized_mrr

    FROM subscriptions s

    JOIN plans p
        ON s.plan_id = p.plan_id
)

SELECT
    subscription_id,
    customer_id,
    plan_name,
    billing_cycle,

    monthly_price,

    normalized_mrr,

    ROUND(
        normalized_mrr * 12,
        2
    ) AS normalized_arr

FROM subscription_mrr

ORDER BY normalized_mrr DESC;
Aqui consideramos que monthly_price representa o preço mensal equivalente do plano. Se o campo armazenar o valor efetivamente cobrado anualmente, a normalização deverá ser monthly_price / 12.

D. Customer Lifetime — Análise de sobrevivência
Uma análise mais avançada é utilizar o conceito de survival analysis.

Diferentemente da média simples, ela considera que alguns clientes ainda estão ativos no encerramento do período de observação.

Vamos preparar uma tabela de duração e evento:

duration_days: tempo de permanência.

event_observed: 1 para cancelamento e 0 para cliente ainda ativo.

Clientes ativos são considerados observações censuradas.


sql

WITH customer_lifetime AS (

    SELECT
        s.customer_id,
        s.subscription_id,

        s.start_date,

        CASE
            WHEN s.end_date IS NOT NULL
                THEN s.end_date
            ELSE CURRENT_DATE
        END AS observation_end,

        CASE
            WHEN s.end_date IS NOT NULL
                THEN 1
            ELSE 0
        END AS event_observed

    FROM subscriptions s
)

SELECT
    customer_id,
    subscription_id,

    start_date,
    observation_end,

    observation_end - start_date
        AS duration_days,

    ROUND(
        (
            observation_end - start_date
        ) / 30.44,
        2
    ) AS duration_months,

    event_observed

FROM customer_lifetime

ORDER BY duration_days DESC;
Essa consulta prepara os dados para aplicar o estimador de Kaplan-Meier em Python, utilizando a biblioteca lifelines.

Exemplo de visualização esperada:

Customer churn. Investigating customer churn using… | by Hans Weda | rond blog | Medium
 
A curva mostra a proporção estimada de clientes que continuam sem cancelar ao longo do tempo.

E. Cohort Retention — Matriz de retenção
Agora vamos transformar os dados em uma matriz de coortes, muito utilizada em empresas SaaS.


sql

WITH cohorts AS (

    SELECT
        customer_id,

        DATE_TRUNC(
            'month',
            MIN(start_date)
        )::date AS cohort_month

    FROM subscriptions

    GROUP BY customer_id
),

monthly_status AS (

    SELECT DISTINCT
        c.customer_id,
        c.cohort_month,

        DATE_TRUNC(
            'month',
            m.month
        )::date AS activity_month

    FROM cohorts c

    CROSS JOIN generate_series(
        DATE '2023-01-01',
        DATE '2025-12-01',
        INTERVAL '1 month'
    ) AS m(month)

    WHERE m.month >= c.cohort_month

      AND EXISTS (

          SELECT 1

          FROM subscriptions s

          WHERE s.customer_id = c.customer_id

            AND s.start_date < m.month + INTERVAL '1 month'

            AND (
                s.end_date IS NULL
                OR s.end_date >= m.month + INTERVAL '1 month'
            )
      )
),

cohort_retention AS (

    SELECT
        cohort_month,

        (
            EXTRACT(YEAR FROM activity_month) -
            EXTRACT(YEAR FROM cohort_month)
        ) * 12 +

        (
            EXTRACT(MONTH FROM activity_month) -
            EXTRACT(MONTH FROM cohort_month)
        ) AS month_number,

        COUNT(DISTINCT customer_id)
            AS retained_customers

    FROM monthly_status

    GROUP BY 1, 2
),

cohort_sizes AS (

    SELECT
        cohort_month,

        COUNT(DISTINCT customer_id)
            AS cohort_size

    FROM cohorts

    GROUP BY 1
)

SELECT
    cr.cohort_month,

    cr.month_number,

    cs.cohort_size,

    cr.retained_customers,

    ROUND(
        100.0 * cr.retained_customers /
        NULLIF(cs.cohort_size, 0),
        2
    ) AS retention_percentage

FROM cohort_retention cr

JOIN cohort_sizes cs
    ON cr.cohort_month = cs.cohort_month

ORDER BY
    cr.cohort_month,
    cr.month_number;
A matriz pode ser organizada no Power BI ou Python para produzir um heatmap:

Cohort analysis (with examples) | Hex
 
Exemplo ilustrativo:

Cohort

Month 0

Month 1

Month 2

Month 3

Jan/2023

100%

85%

78%

72%

Feb/2023

100%

88%

80%

75%

Mar/2023

100%

82%

70%

65%

Essa análise permite avaliar a qualidade da aquisição de clientes e identificar em quais períodos a empresa teve maior dificuldade de retenção.

F. Análise estatística — Utilização e cancelamento
SQL será utilizado para preparar os dados necessários aos testes estatísticos.

Vamos investigar se existe associação entre:

Quantidade de logins e churn.

Tempo ativo e churn.

Quantidade de funcionalidades e churn.

Frequência de utilização e churn.

Primeiro, criamos uma view analítica:


sql

CREATE OR REPLACE VIEW vw_churn_usage_statistics AS

WITH customer_usage AS (

    SELECT
        customer_id,

        COUNT(DISTINCT usage_date)
            AS active_days,

        SUM(login_count)
            AS total_logins,

        AVG(login_count)
            AS avg_daily_logins,

        SUM(active_minutes)
            AS total_active_minutes,

        AVG(active_minutes)
            AS avg_active_minutes,

        AVG(
            CASE
                WHEN features_used IS NULL
                     OR features_used = ''
                THEN 0
                ELSE cardinality(
                    string_to_array(features_used, '|')
                )
            END
        ) AS avg_features_used

    FROM usage_metrics

    GROUP BY customer_id
)

SELECT
    c.customer_id,

    c.region,

    COALESCE(u.active_days, 0)
        AS active_days,

    COALESCE(u.total_logins, 0)
        AS total_logins,

    COALESCE(u.avg_daily_logins, 0)
        AS avg_daily_logins,

    COALESCE(u.total_active_minutes, 0)
        AS total_active_minutes,

    COALESCE(u.avg_active_minutes, 0)
        AS avg_active_minutes,

    COALESCE(u.avg_features_used, 0)
        AS avg_features_used,

    CASE
        WHEN ca.customer_id IS NOT NULL THEN 1
        ELSE 0
    END AS churn_flag

FROM customers c

LEFT JOIN customer_usage u
    ON c.customer_id = u.customer_id

LEFT JOIN cancellations ca
    ON c.customer_id = ca.customer_id;
Agora podemos consultar a base para exportar ao Python:


sql

SELECT *

FROM vw_churn_usage_statistics

ORDER BY customer_id;
