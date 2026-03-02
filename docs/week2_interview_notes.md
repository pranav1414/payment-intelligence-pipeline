# Week 2 Interview Notes — dbt Transformations & Data Modeling
## Payment Intelligence Pipeline

---

## Table of Contents
1. What We Built This Week
2. What is dbt and Why We Use It
3. How dbt Fits Into Our Pipeline
4. Key Concepts Explained
5. The Three-Layer Architecture
6. Star Schema — Facts & Dimensions
7. YAML Files — What They Are and Why We Use Them
8. Setting Up dbt 
9. The Models We Built — Step by Step
10. CTEs — What They Are and Why We Use Them
11. Views vs Tables
12. source() vs ref()
13. Data Quality Tests
14. The Complete Pipeline
15. Interview Talking Points

---

## 1. What We Built This Week

This week we built a complete dbt transformation layer on top of our raw BigQuery data. By the end of the week our pipeline transformed raw payment data into clean, tested, analytics-ready tables.

**What we started with:**
- `payments_raw.raw_transactions` — 10,000 raw payment records in BigQuery
- `payments_raw.raw_fx_rates` — 240 rows of historical exchange rates

**What we ended up with:**
- 2 staging views (cleaned data)
- 1 intermediate view (enriched with USD conversion)
- 3 mart tables (business-level aggregations)
- 9 automated data quality tests — all passing

Everything was committed to GitHub at the end of the session.

---

## 2. What is dbt and Why We Use It

### The Core Problem dbt Solves

Once data lands in BigQuery, someone has to transform it into something useful. Without dbt, you write raw SQL scripts scattered across files, run them manually in the right order, and hope nothing breaks.

**Without dbt:**
- SQL scripts are scattered in files with no structure
- No dependency tracking — you manually figure out which script runs first
- No tests — bad data silently flows into dashboards
- No documentation — nobody knows what a column means
- Hard to version control cleanly

**With dbt:**
- Organized project structure with clear layers
- Automatic dependency management — dbt figures out the order
- Built-in data quality tests
- Auto-generated documentation and data catalog
- Pure SQL files that are Git-friendly

### The One-Line Definition
> dbt brings software engineering practices — testing, documentation, version control, and dependency management — to SQL transformations inside the data warehouse.

### What dbt Does NOT Do
dbt does not move data in or out of your warehouse. It only transforms data that already exists inside BigQuery. Your Python scripts handle extraction and loading — dbt only handles the T in ELT (Transform).

### The Five Real Reasons to Use dbt

**1. Dependency Management**
Your `int_transactions_enriched` model depends on `stg_transactions` and `stg_fx_rates`. dbt builds a DAG (Directed Acyclic Graph) of your models and figures out the correct execution order automatically. You never manually think about which script runs first.

**2. Testing**
You declare rules like "transaction_id should never be null" or "status must be one of: completed, failed, pending, refunded." dbt runs these every time you build and fails loudly if your data violates them. Without this, bad data silently reaches your dashboards.

**3. Documentation**
You write descriptions for models and columns in YAML files. dbt auto-generates a browsable data catalog. Anyone on the team can look up what `amount_usd` means and where it came from.

**4. Version Control Friendly**
Everything is just `.sql` and `.yml` files. Your entire transformation layer lives in Git — you get history, code review, and rollback for free.

**5. Lineage**
dbt generates a visual graph showing exactly how data flows from raw source → staging → intermediate → marts. When something breaks, you can trace it instantly.

---

## 3. How dbt Fits Into Our Pipeline

### Before dbt (Week 1)
```
[Python Scripts]
     │
     ▼
[Open Exchange Rates API] ──► [Google Cloud Storage (raw CSVs)]
[Faker (synthetic data)]              │
                                      ▼
                               [BigQuery raw tables]
                                      │
                                      ▼
                             [Ad-hoc SQL queries]
```

### After dbt (Week 2)
```
[Python Scripts]
     │
     ▼
[GCS] ──► [BigQuery: raw tables]
                    │
                    ▼
              [dbt Project]
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      staging   intermediate  marts
     (clean)    (enriched)  (business)
          │         │         │
          └─────────┴─────────┘
                    │
                    ▼
          [Tested, documented,
           analytics-ready tables]
```

dbt only lives inside BigQuery. It takes your raw tables and produces transformed views and tables through pure SQL, but with software engineering best practices layered on top.

---

## 4. Key Concepts Explained

### What is a YAML file?

YAML (`.yml`) is a configuration file format. It is machine-readable — meaning the tool (dbt, Airflow, etc.) reads it and uses it to make decisions at runtime. It is also human-readable, making it easy to write and review.

**YAML vs JSON — same data, different format:**
```json
{ "name": "payment_intelligence", "version": "1.0.0" }
```
```yaml
name: payment_intelligence
version: 1.0.0
```

YAML uses indentation (2 spaces) to show hierarchy/nesting. No curly braces, no quotes, no commas.

**Why dbt uses YAML:**
- Configuration is separated from logic (a core software engineering principle)
- If you hardcode settings inside SQL, you have to change them everywhere when something changes
- With YAML, you change one file and everything that depends on it picks up the change automatically
- This is the same reason we used a `.env` file in Week 1 instead of hardcoding API keys

**YAML is not just a dbt thing.** You will see it in:
- Airflow (`docker-compose.yml`)
- GitHub Actions (CI/CD pipelines)
- Kubernetes (infrastructure definitions)
- Great Expectations (data quality configs)

**Key insight:** A YAML file is not just a document for humans to read. It is active — the tool parses it at runtime and behaves according to what it finds. Think of it like a settings panel — you change the settings, the tool behaves differently.

### What is a CTE?

CTE stands for Common Table Expression. It is a named chunk of SQL logic that exists only during query execution, in memory. It never gets stored anywhere — not even temporarily.

**Syntax:**
```sql
with cte_name as (
    select * from some_table
    where condition = true
)
select * from cte_name
```

**Why we use CTEs — organization and readability:**

Without CTEs, complex queries become one giant unreadable block. CTEs let you break a query into named steps that tell a story:

```sql
-- Step 1: where does the raw data come from?
with source as (
    select * from raw_transactions
),

-- Step 2: how are we cleaning it?
staged as (
    select
        transaction_id,
        lower(status) as status
    from source
    where transaction_id is not null
)

-- Step 3: final output
select * from staged
```

**CTEs do NOT create tables.** They are purely organizational. The database treats a query with CTEs identically to one big query — same performance, same result. The only benefit is readability and maintainability, which matters enormously in team environments.

**The standard dbt CTE pattern:**
In dbt, the convention is always:
1. `source` CTE — pulls raw data
2. `staged/enriched/final` CTE — applies transformations
3. `select * from [last cte]` — final output

### What is a View?

A view is a saved SQL query that is stored as a permanent object in the database, just like a table. Anyone connected to the database can query it at any time.

**Creating a view (what dbt does for you automatically):**
```sql
create or replace view stg_transactions as (
    select * from raw_transactions
    where transaction_id is not null
)
```

After this runs, `stg_transactions` appears in BigQuery alongside your tables. Anyone can run `select * from stg_transactions` just like querying a table.

**Key difference from a table:** A view does not store data. Every time you query a view, it runs the underlying SQL against the source table and returns fresh results. This means:
- No storage cost
- Always fresh data
- Changes to the source table are immediately reflected

**Why we use views for staging and intermediate layers:**
- Zero storage cost — perfect for cleaning/transformation logic
- Always reflect the latest raw data
- Lightweight and fast to create

### View vs CTE — Critical Distinction

| | CTE | View |
|---|---|---|
| Lives... | In memory during one query | In BigQuery permanently |
| Visible to others? | No | Yes |
| Gone after query? | Yes | No |
| Like... | Scratch paper | A notebook entry |

CTEs are steps inside a SQL file. Views are the output that dbt saves to BigQuery from that SQL file.

### What is a Table (Materialized)?

When dbt materializes a model as a `table`, it physically copies the query results into BigQuery storage. This is different from a view, which just saves the SQL.

**Why we use tables for marts:**
- Mart tables are queried constantly by dashboards and analysts
- Storing the results means fast query times (no need to recompute)
- We pay a small storage cost in exchange for speed
- Staging and intermediate are views (cheap, always fresh); marts are tables (fast, pre-computed)

---

## 5. The Three-Layer Architecture

This is the most important dbt concept for interviews. Every professional dbt project follows this pattern:

### Layer 1: Staging (`stg_`)
- One-to-one with your raw source tables
- Only cleaning: rename columns, cast types, filter nulls, standardize values
- No business logic whatsoever
- Materialized as **views**
- Example: `stg_transactions` — clean version of `raw_transactions`

### Layer 2: Intermediate (`int_`)
- Joins and enrichment across staging models
- Prepares data for business use but still no final metrics
- Materialized as **views**
- Example: `int_transactions_enriched` — joins transactions with fx rates to add `amount_usd`

### Layer 3: Marts (`mart_`)
- Business-level aggregations and final tables
- What analysts and dashboards consume
- Materialized as **tables** (for query performance)
- Example: `mart_daily_summary` — daily payment volumes by currency

### The Interview Answer
> "I used dbt to implement a three-layer transformation architecture on top of BigQuery — staging for cleaning raw data, intermediate models for enrichment like currency conversion, and marts for business aggregations. Every model is tested and documented, and dbt handles the dependency graph so transformations always run in the correct order."

---

## 6. Star Schema — Facts & Dimensions

Star schema is a data warehouse design pattern for structuring your final tables. It lives inside the marts layer.

### Fact Tables
- Store measurable events/transactions
- Each row is something that happened
- Contains numeric measures and foreign keys
- Long and narrow — many rows, few columns
- Example: `fct_transactions` — one row per payment

### Dimension Tables
- Store descriptive context about entities
- Each row describes something
- Short and wide — fewer rows, many descriptive columns
- Example: `dim_merchants` — merchant name, category, country
- Example: `dim_dates` — date, day of week, month, is_weekend

### How It Relates to dbt Layers
```
staging/        → cleaned raw data
intermediate/   → joins, enrichment
marts/
  ├── fct_transactions.sql      ← fact table
  ├── dim_merchants.sql         ← dimension table
  └── mart_daily_payment_volume ← aggregate report
```

### Star Schema vs Snowflake Schema
- **Star schema** — dimension tables connect directly to fact table (one join level)
- **Snowflake schema** — dimensions are further normalized into sub-dimensions (multiple join levels)
- Star schema is faster for BI queries; snowflake schema uses less storage

---

## 7. Setting Up dbt — Every Step Explained

### Step 1: Install dbt-bigquery
```bash
pip install dbt-bigquery
```
This installs both dbt Core and the BigQuery adapter. The adapter is what allows dbt to talk to BigQuery specifically.

### Step 2: Authentication — Why We Used OAuth Instead of a Keyfile

In Week 1, the plan was to use a service account JSON keyfile for authentication. However, our GCP organization had the policy `iam.disableServiceAccountKeyCreation` enforced, which blocked keyfile creation.

**Solution: Application Default Credentials (ADC)**

ADC is actually the more modern and secure authentication method. Instead of a JSON file, you log in via gcloud and credentials are stored locally on your machine.

```bash
gcloud auth application-default login
```

This stores credentials at:
```
C:\Users\Pranav\AppData\Roaming\gcloud\application_default_credentials.json
```

dbt uses these automatically when `method: oauth` is set in `profiles.yml`. No keyfile path needed.

### Step 3: dbt_project.yml — The Main Config File

```yaml
name: 'payment_intelligence'
version: '1.0.0'
config-version: 2

profile: 'payment_intelligence'

model-paths: ["models"]
test-paths: ["tests"]
clean-targets: ["target", "dbt_packages"]

models:
  payment_intelligence:
    staging:
      +materialized: view
    intermediate:
      +materialized: view
    marts:
      +materialized: table
```

**What each line does:**
- `name` — your project name, used internally by dbt
- `profile` — points to your BigQuery connection in `profiles.yml`
- `model-paths` — tells dbt where to find your SQL models
- `materialized: view` — staging and intermediate build as views (no storage cost)
- `materialized: table` — marts build as physical tables (fast for dashboards)

**Why this file exists (not hardcoded in SQL):**
Configuration is separated from logic. Change materialization once here and every model in that folder picks it up. This also allows you to run the same models against dev vs production by just switching profiles.

### Step 4: profiles.yml — The Connection File

```yaml
payment_intelligence:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: payment-intelligence-488700
      dataset: payment_intelligence
      location: US
      threads: 4
```

**What each line does:**
- `target: dev` — we're running in the dev environment
- `method: oauth` — use ADC credentials (no keyfile)
- `project` — your GCP project ID
- `dataset` — where dbt will create your models in BigQuery (`payment_intelligence` dataset)
- `threads: 4` — run up to 4 models in parallel

### Step 5: Verify Connection
```bash
dbt debug
```
Output confirms:
- profiles.yml found and valid
- dbt_project.yml found and valid
- Connection test: OK

---

## 8. The Models We Built — Step by Step

### sources.yml — Declaring Raw Data Sources

Location: `models/staging/sources.yml`

```yaml
version: 2

sources:
  - name: payments_raw
    database: payment-intelligence-488700
    schema: payments_raw
    tables:
      - name: raw_transactions
        description: "Raw payment transactions generated by Faker"
      - name: raw_fx_rates
        description: "Historical FX rates from Open Exchange Rates API"
```

**Why this file exists:**
This is what makes `{{ source('payments_raw', 'raw_transactions') }}` work in your SQL models. Without this declaration, dbt doesn't know what `payments_raw` refers to. It also means if your dataset ever gets renamed, you change it here once and all models update automatically.

---

### stg_transactions.sql

Location: `models/staging/stg_transactions.sql`
Materialized as: **view**

```sql
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
```

**What each part does:**
- `{{ source('payments_raw', 'raw_transactions') }}` — dbt template syntax that compiles to the full BigQuery table path at runtime. Uses `source()` because this is a raw table outside dbt.
- `source` CTE — pulls all raw data
- `staged` CTE — cleans the data: lowercases status, filters nulls, adds `_loaded_at` timestamp
- `where transaction_id is not null` — removes records with no ID (they're useless)
- `current_timestamp() as _loaded_at` — audit column so you know when the view was last queried
- Final `select * from staged` — this is what becomes the view in BigQuery

**What this produces in BigQuery:** A view called `stg_transactions` in the `payment_intelligence` dataset.

---

### stg_fx_rates.sql

Location: `models/staging/stg_fx_rates.sql`
Materialized as: **view**

```sql
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
```

**Key detail — the cast:**
The `date` column in `raw_fx_rates` was stored as a STRING in BigQuery. Our `int_transactions_enriched` model joins on date, and you cannot join a DATE to a STRING directly. The fix was `cast(date as date)` which converts the string to a proper DATE type.

This is a real-world data engineering problem — raw data often has wrong data types and staging is where you fix them.

---

### int_transactions_enriched.sql

Location: `models/intermediate/int_transactions_enriched.sql`
Materialized as: **view**

```sql
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
```

**What this does:**
Joins cleaned transactions with FX rates to calculate `amount_usd` — the transaction amount converted to US dollars. This is the key enrichment step that makes all downstream analysis currency-agnostic.

**Why `ref()` instead of `source()`:**
`ref()` is used when referencing another dbt model (something dbt created). `source()` is used when referencing raw tables that exist outside dbt. Since `stg_transactions` and `stg_fx_rates` are dbt models, we use `ref()`.

**Why `ref()` matters beyond syntax:**
When you use `ref()`, dbt knows that `int_transactions_enriched` depends on `stg_transactions` and `stg_fx_rates`. It adds these to the dependency graph (DAG) and always builds staging models before intermediate models. The order is automatic.

**Why LEFT JOIN:**
A left join keeps all transactions even if no matching FX rate is found for that date/currency combination. An inner join would silently drop transactions with no rate match, which would be a data loss bug.

---

### mart_daily_summary.sql

Location: `models/marts/mart_daily_summary.sql`
Materialized as: **table**

```sql
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
```

**What this produces:** 234 rows — one row per date/currency combination showing daily payment volume, averages, and fraud counts.

---

### mart_merchant_analytics.sql

Location: `models/marts/mart_merchant_analytics.sql`
Materialized as: **table**

```sql
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
```

**What this produces:** 847 rows — one row per merchant showing total volume, transaction counts, and fraud rate percentage.

---

### mart_currency_breakdown.sql

Location: `models/marts/mart_currency_breakdown.sql`
Materialized as: **table**

```sql
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
```

**What this produces:** 8 rows — one row per currency showing volume distribution and fraud rates across currencies.

---

## 9. source() vs ref() — Complete Explanation

This is frequently asked in interviews.

| | `source()` | `ref()` |
|---|---|---|
| Used for... | Raw tables outside dbt | dbt models you created |
| Example | `raw_transactions` in `payments_raw` | `stg_transactions` in `payment_intelligence` |
| Defined in... | `sources.yml` | The model's `.sql` filename |
| Tracks dependencies? | No | Yes — builds DAG |

**The rule:**
- Data comes from outside dbt (raw tables) → `source()`
- Data comes from another dbt model → `ref()`

**Why ref() builds the DAG:**
When dbt sees `ref('stg_transactions')`, it knows `int_transactions_enriched` cannot run until `stg_transactions` is complete. This is how dbt builds the execution order automatically without you specifying it.

---

## 10. Data Quality Tests

### What We Tested

Location: `models/staging/schema.yml`

```yaml
version: 2

models:
  - name: stg_transactions
    description: "Cleaned payment transactions"
    columns:
      - name: transaction_id
        tests:
          - not_null
          - unique
      - name: status
        tests:
          - not_null
          - accepted_values:
              values: ['completed', 'failed', 'pending', 'refunded']
      - name: amount
        tests:
          - not_null
      - name: currency
        tests:
          - not_null

  - name: stg_fx_rates
    description: "Cleaned FX rates"
    columns:
      - name: date
        tests:
          - not_null
      - name: currency
        tests:
          - not_null
      - name: rate_to_usd
        tests:
          - not_null
```

### The Three Test Types

**`not_null`** — checks that no rows have a NULL value in this column. If any NULLs exist, the test fails.

**`unique`** — checks that every value in this column appears exactly once. Used on `transaction_id` to ensure no duplicate transactions.

**`accepted_values`** — checks that every value in the column is one of the specified list. Used on `status` to ensure no unexpected values like typos or new statuses sneak in.

### Running Tests
```bash
dbt test
```

**Result: PASS=9 WARN=0 ERROR=0** — all 9 tests passed, confirming:
- No duplicate transaction IDs
- No null values in critical columns
- All status values are valid

### Why Testing Matters for Interviews

> "I implemented dbt tests at the staging layer — uniqueness and not_null checks on key columns, and accepted_values tests on categorical fields like status. These run automatically every time the pipeline executes, so bad data gets caught before it reaches the marts that analysts and dashboards consume."

This is a senior-level answer to "how do you ensure data quality?"

---

## 11. The Complete Pipeline Architecture

```
RAW LAYER (payments_raw dataset)
├── raw_transactions     10,000 rows, loaded from GCS
└── raw_fx_rates         240 rows, loaded from local CSV

STAGING LAYER (payment_intelligence dataset) — views
├── stg_transactions     cleaned transactions, nulls removed, status lowercased
└── stg_fx_rates         cleaned rates, date cast to DATE type

INTERMEDIATE LAYER (payment_intelligence dataset) — views
└── int_transactions_enriched    joined with FX rates, amount_usd calculated

MARTS LAYER (payment_intelligence dataset) — tables
├── mart_daily_summary         234 rows, daily volume by currency
├── mart_merchant_analytics    847 rows, per-merchant performance + fraud rate
└── mart_currency_breakdown    8 rows, per-currency volume distribution
```

### Execution Order (dbt DAG)
```
stg_transactions ──┐
                   ├──► int_transactions_enriched ──► mart_daily_summary
stg_fx_rates ──────┘                              ──► mart_merchant_analytics
                                                  ──► mart_currency_breakdown
```

dbt runs this in the correct order automatically based on `ref()` dependencies.

---

## 12. Key Commands Reference

```bash
# Verify dbt connection to BigQuery
dbt debug

# Run all models
dbt run

# Run only staging models
dbt run --select staging

# Run only intermediate models
dbt run --select intermediate

# Run specific model
dbt run --select stg_transactions

# Run all tests
dbt test

# Run models and tests together
dbt build
```

---

## 13. Interview Talking Points

### "Walk me through your data pipeline"
> "I built an end-to-end ELT pipeline for payment transaction analytics. Python scripts extract synthetic transaction data and real FX rates, load them into Google Cloud Storage, then into BigQuery. From there, dbt handles the transformation layer using a three-tier architecture — staging for cleaning, intermediate for enrichment like currency conversion, and marts for business aggregations. Every model is tested with dbt's built-in quality checks."

### "What is dbt and why did you use it?"
> "dbt is a transformation tool that brings software engineering practices to SQL. I used it because it gives you dependency management through a DAG, built-in data quality tests, auto-generated documentation, and clean version control. Without it, SQL transformations are just scattered scripts with no structure or reliability."

### "How do you ensure data quality?"
> "I implemented dbt tests at the staging layer — uniqueness checks on transaction IDs to catch duplicates, not_null checks on critical columns, and accepted_values tests on categorical fields like payment status. These run automatically every pipeline execution, catching issues before they reach downstream consumers."

### "What's the difference between a view and a table in your pipeline?"
> "Staging and intermediate models are views — they have no storage cost and always reflect the latest raw data. Marts are materialized as tables because dashboards query them constantly and need fast response times. We accept the storage cost at the mart layer in exchange for query performance."

### "How do you handle different environments — dev vs production?"
> "In dbt, the code stays the same. Only the profiles.yml changes — pointing dev to a development dataset and prod to the production dataset. This separation means you can test transformations safely without touching production data."

### "What is a DAG in the context of dbt?"
> "DAG stands for Directed Acyclic Graph. In dbt, it's the dependency map of all your models. When you use ref() to reference another model, dbt adds that dependency to the graph and ensures models always build in the correct order. You can visualize this in dbt's auto-generated documentation."

### "What's the difference between source() and ref() in dbt?"
> "source() references raw tables that exist outside dbt — loaded by your ingestion scripts. ref() references other dbt models. The key difference is that ref() creates a dependency in the DAG, so dbt knows to build that model first before the one that references it."

---

## 14. Things That Went Wrong and How We Fixed Them

### Problem 1: venv activation failed on Windows
`venv\Scripts\activate` failed because PowerShell interpreted `venv` as a module name.

**Fix:** Use `.\` prefix: `.\.venv\Scripts\activate`

**Lesson:** On Windows PowerShell, always prefix local script paths with `.\`

### Problem 2: Service account keyfile creation blocked
GCP organization policy `iam.disableServiceAccountKeyCreation` blocked JSON key download.

**Fix:** Used `gcloud auth application-default login` (OAuth/ADC) instead. Set `method: oauth` in profiles.yml.

**Lesson:** ADC is actually the more modern, secure authentication method. Many enterprise environments block keyfiles for security reasons.

### Problem 3: raw_fx_rates missing from BigQuery
The `extract_fx_rates.py` script only saved to a local CSV — it never uploaded to BigQuery.

**Fix:** Loaded the local CSV directly using the BigQuery Python client with `load_table_from_dataframe()`.

**Lesson:** Always verify that data actually landed in the destination, not just that the script ran without errors.

### Problem 4: DATE vs STRING type mismatch on join
`int_transactions_enriched` failed because `raw_fx_rates.date` was a STRING but `transaction_date` was a DATE.

**Fix:** Added `cast(date as date)` in `stg_fx_rates.sql`.

**Lesson:** Raw data often has wrong data types. The staging layer is where you fix them. Always check column types before writing join conditions.

### Problem 5: pyarrow not installed
`load_table_from_dataframe()` requires pyarrow but it wasn't installed.

**Fix:** `pip install pyarrow`

**Lesson:** Always check library dependencies when using new BigQuery client methods.