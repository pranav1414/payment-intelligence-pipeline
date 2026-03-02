with transactions as (
    select * from {{ ref('stg_transactions') }}
),

fx_rates as (
    select * from {{ ref('stg_fx_rates') }}
),

enriched as (
    select
        t.transaction_id,
        t.transaction_date,
        t.transaction_time,
        t.customer_id,
        t.merchant_name,
        t.merchant_category,
        t.amount,
        t.currency,
        t.payment_method,
        t.status,
        t.country,
        t.city,
        t.is_flagged,
        f.rate_to_usd,
        round(t.amount / f.rate_to_usd, 2) as amount_usd
    from transactions t
    left join fx_rates f
        on t.currency = f.currency
        and t.transaction_date = f.date
)

select * from enriched