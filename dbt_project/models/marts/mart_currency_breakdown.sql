with fact as (
    select * from {{ ref('int_transactions_enriched') }}
),

final as (
    select
        currency,
        count(transaction_id)           as total_transactions,
        sum(amount_usd)                 as total_volume_usd,
        avg(amount_usd)                 as avg_transaction_usd,
        min(amount_usd)                 as min_transaction_usd,
        max(amount_usd)                 as max_transaction_usd,
        countif(is_flagged = true)      as flagged_transactions,
        round(
            countif(is_flagged = true) * 100.0 / count(transaction_id), 2
        )                               as fraud_rate_pct
    from fact
    where amount_usd is not null
    group by currency
    order by total_volume_usd desc
)

select * from final