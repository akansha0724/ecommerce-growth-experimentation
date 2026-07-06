-- =============================================================================
-- E-commerce Growth — MySQL schema
-- Source: UCI Online Retail II (cleaned), one row per invoice line item
-- =============================================================================

CREATE DATABASE IF NOT EXISTS ecommerce
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ecommerce;

CREATE TABLE IF NOT EXISTS transactions (
    row_id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    invoice       VARCHAR(20),
    stock_code    VARCHAR(20),
    description   VARCHAR(255),
    quantity      INT,
    invoice_date  DATETIME,
    price         DECIMAL(12,2),
    customer_id   INT,
    country       VARCHAR(60),
    revenue       DECIMAL(14,2),
    PRIMARY KEY (row_id),
    KEY ix_customer (customer_id),
    KEY ix_date (invoice_date)
) ENGINE=InnoDB;
