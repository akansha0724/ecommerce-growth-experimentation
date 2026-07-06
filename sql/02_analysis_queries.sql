-- =============================================================================
-- E-commerce Growth — analytical query set
-- Run: mysql ecommerce < sql/02_analysis_queries.sql
-- =============================================================================
USE ecommerce;

-- Q1. Monthly revenue trend
SELECT DATE_FORMAT(invoice_date, '%Y-%m') AS month,
       COUNT(DISTINCT invoice)     AS orders,
       COUNT(DISTINCT customer_id) AS active_customers,
       ROUND(SUM(revenue), 0)      AS revenue
FROM transactions
GROUP BY month
ORDER BY month;

-- Q2. Revenue by country (top 10)
SELECT country,
       COUNT(DISTINCT customer_id) AS customers,
       ROUND(SUM(revenue), 0)      AS revenue
FROM transactions
GROUP BY country
ORDER BY revenue DESC
LIMIT 10;

-- Q3. Per-customer RFM with quintile scores (window function NTILE)
WITH cust AS (
    SELECT customer_id,
           DATEDIFF((SELECT MAX(invoice_date) FROM transactions), MAX(invoice_date)) AS recency_days,
           COUNT(DISTINCT invoice) AS frequency,
           SUM(revenue)            AS monetary
    FROM transactions
    GROUP BY customer_id
)
SELECT customer_id, recency_days, frequency, ROUND(monetary,0) AS monetary,
       6 - NTILE(5) OVER (ORDER BY recency_days)      AS r_score,
       NTILE(5) OVER (ORDER BY frequency)             AS f_score,
       NTILE(5) OVER (ORDER BY monetary)              AS m_score
FROM cust
ORDER BY monetary DESC
LIMIT 15;

-- Q4. Revenue Pareto: cumulative revenue share by customer rank (window function)
WITH cust AS (
    SELECT customer_id, SUM(revenue) AS monetary
    FROM transactions GROUP BY customer_id
),
ranked AS (
    SELECT customer_id, monetary,
           SUM(monetary) OVER (ORDER BY monetary DESC
                               ROWS UNBOUNDED PRECEDING) AS cum_rev,
           SUM(monetary) OVER ()                          AS total_rev,
           PERCENT_RANK() OVER (ORDER BY monetary DESC)   AS cust_pct
    FROM cust
)
SELECT ROUND(cust_pct * 100, 0) AS top_pct_customers,
       ROUND(MIN(cum_rev) / MIN(total_rev) * 100, 1) AS pct_of_revenue
FROM ranked
WHERE cust_pct IN (0.1, 0.2, 0.5)
   OR cust_pct BETWEEN 0.099 AND 0.101
   OR cust_pct BETWEEN 0.199 AND 0.201
   OR cust_pct BETWEEN 0.499 AND 0.501
GROUP BY top_pct_customers;

-- Q5. New customers acquired per month (cohort sizes)
SELECT cohort_month, COUNT(*) AS new_customers
FROM (
    SELECT customer_id,
           DATE_FORMAT(MIN(invoice_date), '%Y-%m') AS cohort_month
    FROM transactions
    GROUP BY customer_id
) c
GROUP BY cohort_month
ORDER BY cohort_month;
