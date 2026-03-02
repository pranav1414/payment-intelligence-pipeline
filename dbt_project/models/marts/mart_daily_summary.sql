with fact as (
    select * from {{ ref('int_transactions_enriched') }}
),

final as (
    select
        transaction_date,
        currency,
        count(transaction_id)           as total_transactions,
        sum(amount_usd)                 as total_volume_usd,
        avg(amount_usd)                 as avg_transaction_usd,
        countif(is_flagged = true)      as flagged_transactions,
        countif(status = 'completed')   as completed_transactions
    from fact
    where amount_usd is not null
    group by transaction_date, currency
    order by transaction_date desc
)

select * from final