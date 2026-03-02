with fact as (
    select * from {{ ref('int_transactions_enriched') }}
),

final as (
    select
        merchant_name,
        merchant_category,
        country,
        count(transaction_id)           as total_transactions,
        sum(amount_usd)                 as total_volume_usd,
        avg(amount_usd)                 as avg_transaction_usd,
        countif(is_flagged = true)      as flagged_transactions,
        round(
            countif(is_flagged = true) * 100.0 / count(transaction_id), 2
        )                               as fraud_rate_pct
    from fact
    where amount_usd is not null
    group by merchant_name, merchant_category, country
    order by total_volume_usd desc
)

select * from final