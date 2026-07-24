{{ config(materialized='ephemeral') }}
SELECT * FROM customers
