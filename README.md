# 💳 Payment Intelligence Pipeline

> An end-to-end production-grade data engineering pipeline for payments analytics — built on a fully free, cloud-native stack.

![Pipeline Status](https://img.shields.io/badge/pipeline-passing-brightgreen) ![dbt](https://img.shields.io/badge/dbt-1.7-orange) ![Airflow](https://img.shields.io/badge/Airflow-2.8-blue) ![BigQuery](https://img.shields.io/badge/BigQuery-GCP-blue) ![Python](https://img.shields.io/badge/Python-3.12-yellow)

---

## 📌 Project Overview

This project simulates a real-world payments data platform used in fintech — ingesting transaction and FX rate data, transforming it through a multi-layer warehouse, orchestrating it with Airflow, and surfacing insights in a live Looker Studio dashboard.

**The problem it solves:** Payment companies process transactions in 8+ currencies across hundreds of merchants. Understanding true USD-equivalent volume, fraud rates by merchant, and daily trends requires a reliable, automated pipeline — not manual SQL queries.

**What this pipeline delivers:**
- Automated daily ingestion of synthetic transactions (10,000 rows) + real FX rates
- Currency-normalised analytics (`amount_usd`) enabling cross-currency comparisons
- Merchant-level fraud rate tracking and daily volume summaries
- Fully orchestrated via Airflow with 8-task DAG and retry logic
- Live Looker Studio dashboard connected directly to BigQuery mart tables

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PAYMENT INTELLIGENCE PIPELINE                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   DATA SOURCES          INGESTION           STORAGE          TRANSFORM  │
│                                                                         │
│  ┌──────────────┐    ┌────────────────┐   ┌─────────┐   ┌───────────┐   │
│  │ Python Faker │───▶│extract_trans.. │──▶│   GCS   │──▶│             │  │
│  │ (synthetic   │    │(10k rows/day)  │   │ Bucket  │   │ BigQuery  │  │
│  │  payments)   │    └────────────────┘   └────┬────┘   │           │  │
│  └──────────────┘                              │        │ payments  │  │
│                                                │        │   _raw    │  │
│  ┌──────────────┐    ┌────────────────┐        │        │           │  │
│  │Open Exchange │───▶│extract_fx_rates│────────┘        └─────┬─────┘  │
│  │  Rates API   │    │  (real rates)  │                       │        │
│  └──────────────┘    └────────────────┘                       ▼        │
│                                                         ┌───────────┐  │
│                                                         │    dbt    │  │
│   ORCHESTRATION       DATA QUALITY       SERVING        │           │  │
│                                                         │ staging → │  │
│  ┌──────────────┐    ┌────────────────┐   ┌─────────┐  │  inter  → │  │
│  │   Airflow    │───▶│  dbt tests     │──▶│ Looker  │  │  marts    │  │
│  │  8-task DAG  │    │ (not_null,     │   │ Studio  │  │           │  │
│  │  daily @6am  │    │  unique, etc.) │   │dashboard│  └─────┬─────┘  │
│  └──────────────┘    └────────────────┘   └────┬────┘        │        │
│                                                └────────────-─┘        │
└─────────────────────────────────────────────────────────────────────────┘

---

## 🛠️ Tech Stack

| Layer | Tool | Version | Why This Tool |
|-------|------|---------|---------------|
| Ingestion | Python + Faker | 3.12 / 24.0 | Realistic synthetic data generation |
| FX Rates | Open Exchange Rates API | — | Free real FX data, 1000 calls/month |
| Storage | Google Cloud Storage | — | Raw file persistence, replay capability |
| Warehouse | Google BigQuery | — | Serverless, scalable, free 10GB/month |
| Transformation | dbt Core (BigQuery adapter) | 1.7 | SQL-based lineage, testing, documentation |
| Orchestration | Apache Airflow | 2.8 | Industry-standard DAG orchestration |
| Visualisation | Looker Studio | — | Native BigQuery connector, free |
| Version Control | GitHub | — | All code, configs, and docs versioned |
| Dev Environment | WSL2 / Ubuntu on Windows | — | Linux-native Airflow without Docker RAM overhead |

---

## 📂 Repository Structure

```
<img width="690" height="798" alt="image" src="https://github.com/user-attachments/assets/cbec5f60-2962-43e4-89d2-678f66a5523f" />


## 🗄️ Data Model

### Raw Layer (`payments_raw` dataset)
| Table | Rows | Description |
|-------|------|-------------|
| `raw_transactions` | ~10,000/day | Synthetic payments with merchant, amount, currency, status |
| `raw_fx_rates` | 8/day | USD exchange rates for 8 currencies |

### Transformation Layer (`payment_intelligence` dataset)

```
raw_transactions  ──▶  stg_transactions  ──▶  int_transactions_enriched
                                                        │
raw_fx_rates      ──▶  stg_fx_rates     ──────────────-┘
                                                        │
                              ┌─────────────────────────┼──────────────────────┐
                              ▼                         ▼                      ▼
                    mart_daily_summary    mart_merchant_analytics   mart_currency_breakdown
```

| Model | Type | Description |
|-------|------|-------------|
| `stg_transactions` | View | Cleaned, typed, nulls removed |
| `stg_fx_rates` | View | Date cast from STRING to DATE |
| `int_transactions_enriched` | View | Transactions joined with FX rates; `amount_usd` computed |
| `mart_daily_summary` | Table | Daily volume, transaction count, avg amount by currency |
| `mart_merchant_analytics` | Table | Per-merchant revenue, fraud rate, transaction count |
| `mart_currency_breakdown` | Table | Volume and fraud rates aggregated by currency |

---

## ⚙️ Airflow DAG

The `payment_intelligence_dag` runs daily at 6am and has 8 tasks with explicit dependencies:

```
extract_transactions
        │
        ▼
  load_to_gcs  ──▶  load_to_bigquery
                            │
                    extract_fx_rates
                            │
                      load_fx_to_bq
                            │
                        dbt_run
                            │
                        dbt_test
```

**Key design decisions:**
- `retries=3` with 5-minute delay on all tasks
- `depends_on_past=False` so failures don't cascade across days
- `catchup=False` to prevent backfill on first run
- Each task is a `BashOperator` calling scripts via the activated virtualenv

---

## 📊 Dashboard

The Looker Studio dashboard connects directly to BigQuery mart tables and shows:
- Daily transaction volume and trend
- Top 10 merchants by USD volume
- Fraud rate by merchant
- Transaction breakdown by currency (USD-normalised)
- Average transaction amount by category

---

## 🧠 Key Design Decisions

**Why GCS + BigQuery instead of loading directly?**
GCS acts as a persistent raw data archive. If a BigQuery load fails, the raw data is still safe. It also enables reprocessing without re-calling the API — a production best practice.

**Why dbt over raw SQL?**
dbt adds versioning, testing, lineage tracking, and documentation on top of SQL. Any SQL query can be written in dbt; not every dbt model can be replicated safely with ad-hoc SQL. This is the difference between a data analyst and a data engineer approach.

**Why three warehouse layers (staging → intermediate → marts)?**
Each layer has one responsibility. Staging cleans; intermediate enriches and joins; marts aggregate for business use. This means bugs are caught early and each layer is independently testable.

**Why native Airflow over Docker?**
Docker Desktop caused memory pressure on the development machine. Native Airflow in WSL2 uses ~40% less RAM and is faster to iterate on during development. In production, this would be managed Airflow (MWAA, Cloud Composer).

**Why Faker for data generation?**
Realistic synthetic data with controlled schema is ideal for a portfolio project — it demonstrates the full pipeline without privacy concerns, and Faker's `seed(42)` makes results reproducible.

---

## 🔮 Future Improvements

- **Streaming ingestion** with Pub/Sub + Dataflow for real-time transaction monitoring
- **Data quality** with Great Expectations checks on row counts and null rates
- **CI/CD** with GitHub Actions running `dbt test` on every PR
- **Incremental dbt models** using `is_incremental()` for large-scale efficiency
- **Infrastructure as Code** with Terraform for GCP resource provisioning

---

*Stack: Python · dbt · Apache Airflow · Google BigQuery · Google Cloud Storage · Looker Studio*
