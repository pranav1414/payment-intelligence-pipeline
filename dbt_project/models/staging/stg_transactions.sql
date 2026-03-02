with source as (
    select * from {{ source('payments_raw', 'raw_transactions') }}
),

staged as (
    select
        transaction_id,
        transaction_date,
        transaction_time,
        customer_id,
        merchant_name,
        merchant_category,
        amount,
        currency,
        payment_method,
        lower(status)           as status,
        country,
        city,
        is_flagged,
        current_timestamp()     as _loaded_at
    from source
    where transaction_id is not null
)

select * from staged