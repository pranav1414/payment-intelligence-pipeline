with source as (
    select * from {{ source('payments_raw', 'raw_fx_rates') }}
),

staged as (
    select
        cast(date as date)  as date,
        currency,
        rate_to_usd,
        current_timestamp() as _loaded_at
    from source
    where date is not null
    and rate_to_usd is not null
)

select * from staged