# Week 3 Interview Notes: Airflow Orchestration & Dashboard
## Payment Intelligence Pipeline Project

---

## TABLE OF CONTENTS
1. What We Built This Week
2. What is Docker? Do You Need It for Airflow?
3. Setting Up Airflow - Step by Step
4. What is a DAG? How Does Airflow Know What to Execute and When?
5. The Payment Pipeline DAG - Every Task Explained
6. Connecting to GCP from WSL
7. Looker Studio Dashboard
8. Key Concepts for Interviews
9. Likely Interview Questions with Answers

---

## 1. WHAT WE BUILT THIS WEEK

This week we added the orchestration and visualization layers to the pipeline. Here's the full picture of what the project now looks like end to end:

```
[Python Script]         [Python Script]
extract_transactions → 
                      → load_to_gcs → load_to_bigquery → dbt run → dbt test → done
extract_fx_rates    →
```

All of this is now **orchestrated by Apache Airflow** — meaning Airflow is the conductor that decides when each script runs, in what order, and what to do if something fails.

The full tech stack after Week 3:
- **Extraction**: Python (Faker for synthetic transactions, Open Exchange Rates API for FX)
- **Storage**: Google Cloud Storage (GCS) → raw file storage
- **Warehouse**: BigQuery → structured tables
- **Transformation**: dbt → staging → intermediate → mart models
- **Orchestration**: Apache Airflow → schedules and runs the entire pipeline daily
- **Visualization**: Looker Studio → dashboard connected directly to BigQuery

---

## 2. WHAT IS DOCKER? DO YOU NEED IT FOR AIRFLOW?

### What is Docker?

Docker is a tool that lets you run applications inside **containers**. A container is like a lightweight, self-contained box that has everything an application needs to run — the code, the runtime, the libraries, the config — all bundled together.

Think of it like this analogy: imagine you're shipping a product. Instead of just sending the product and hoping the recipient has the right packaging, tools, and environment to use it — you ship it in a complete, self-contained box with everything included. That's what Docker does for software.

**Why do people use Docker?**
- It guarantees the application runs the same way on every machine
- You don't need to install dependencies manually on each machine
- Easy to scale — you can spin up many containers at once
- Industry standard for deploying applications

### Do You Need Docker for Airflow?

**No, you don't.** Docker is a common way to run Airflow but it's not the only way.

The official Airflow documentation recommends Docker Compose for running Airflow locally because it handles all the complexity of setting up multiple services (webserver, scheduler, database, message broker) automatically.

**However**, in our project we chose NOT to use Docker for a specific reason: **RAM constraints**. The full Airflow Docker Compose setup runs 5+ containers simultaneously and consumes a lot of memory. Our machine was running at 87%+ RAM usage with Docker Desktop open, causing Docker Desktop to crash repeatedly.

So we made a pragmatic engineering decision: **run Airflow natively in WSL2 (Ubuntu)** instead.

### The Two Ways We Tried (and Why We Landed on WSL):

**Attempt 1: Docker Compose (failed due to RAM)**
- Downloaded the official `docker-compose.yaml` from Airflow's website
- Ran `docker compose up airflow-init` — this initializes the database
- Got `exited with code 0` meaning success
- But when running `docker compose up -d`, Docker Desktop crashed due to memory pressure
- The port was also conflicting (8080 was already taken by an old Airflow instance)

**Attempt 2: Native Windows (failed due to OS)**
- Tried installing Airflow directly via `pip install apache-airflow`
- Airflow explicitly does not support Windows natively
- Got error: `Cannot use relative path: sqlite:///C:\Users\...` — Windows backslashes vs Unix forward slashes

**Attempt 3: WSL2 Ubuntu (success)**
- WSL = Windows Subsystem for Linux — it runs a real Linux kernel inside Windows
- Airflow is fully supported on Linux
- Created a fresh Python virtual environment inside WSL: `python3 -m venv ~/airflow-venv`
- Set `AIRFLOW_HOME` to the Linux filesystem (not `/mnt/c/...`) to avoid Windows permission issues
- This is the working setup

**Interview Answer for "How did you run Airflow?":**
> "I ran Airflow natively in WSL2 on Windows. Docker was my first choice since it's the production-standard deployment method, but RAM constraints on my local machine caused Docker Desktop to crash. WSL2 gave me a real Linux environment where Airflow runs fully supported, which is also closer to how it would run in a cloud VM. This taught me an important engineering lesson — choose the right tool for the constraints you have."

---

## 3. SETTING UP AIRFLOW - STEP BY STEP

Here is exactly what we did to get Airflow running, and why each step was needed:

### Step 1: Enter WSL
```bash
wsl
```
This drops you into the Ubuntu Linux environment running inside Windows.

### Step 2: Install Python and pip in WSL
```bash
sudo apt update
sudo apt install python3-pip python3-venv -y
```
WSL Ubuntu didn't have pip (Python's package manager) by default. We had to install it before we could install anything else.

### Step 3: Create a dedicated virtual environment
```bash
python3 -m venv ~/airflow-venv
source ~/airflow-venv/bin/activate
```
Why a separate virtual environment? Because Airflow has very specific dependency requirements that conflict with other packages (like dbt). Keeping it isolated prevents version conflicts. The `~/` means this lives in the Linux home directory, not on the Windows filesystem.

### Step 4: Install Airflow with constraints
```bash
pip install "apache-airflow==2.9.1" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.1/constraints-3.12.txt"
```
The `--constraint` flag is critical. Airflow has hundreds of dependencies. Without constraints, pip might install incompatible versions of sub-dependencies. The constraints file pins every dependency to a version that's known to work with Airflow 2.9.1 on Python 3.12.

### Step 5: Set AIRFLOW_HOME
```bash
export AIRFLOW_HOME=~/airflow-home
```
`AIRFLOW_HOME` is an environment variable that tells Airflow where to store all its files — the database, config, logs, and DAGs. We set this to the Linux filesystem (`~/airflow-home`) rather than the Windows filesystem (`/mnt/c/...`) because WSL doesn't have write permissions on Windows NTFS files needed for log rotation, which caused a `PermissionError` when we first tried it.

### Step 6: Initialize the database
```bash
airflow db init
```
Airflow uses a database (SQLite by default for local dev, PostgreSQL in production) to track DAG runs, task states, logs, and connections. This command creates that database and sets up all the tables Airflow needs.

### Step 7: Create an admin user
```bash
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
```
Airflow's web UI requires authentication. This creates the login credentials.

### Step 8: Start the webserver and scheduler (two separate processes)
```bash
# Terminal 1
airflow webserver --port 8080

# Terminal 2  
airflow scheduler
```
Airflow needs TWO processes running simultaneously:
- **Webserver**: Serves the UI at `localhost:8080`. This is what you see in the browser.
- **Scheduler**: The brain of Airflow. It constantly scans the DAGs folder, checks schedules, queues tasks, and monitors execution.

These are separate because the UI and the scheduling logic are independent concerns. If the webserver crashes, the scheduler keeps running and your pipelines keep executing.

---

## 4. WHAT IS A DAG? HOW DOES AIRFLOW KNOW WHAT TO EXECUTE AND WHEN?

### What is a DAG?

DAG stands for **Directed Acyclic Graph**. Let's break that down:
- **Directed**: Each connection between tasks has a direction — task A points TO task B, meaning A must run before B
- **Acyclic**: There are no cycles — you can't have task A depend on task B which depends on task A. The graph must flow in one direction.
- **Graph**: A network of nodes (tasks) and edges (dependencies between them)

In Airflow, a DAG is a Python file that defines:
1. A collection of tasks
2. The dependencies between those tasks
3. When the pipeline should run (schedule)
4. What to do on failure (retries, alerts)

### Which Code File Runs Airflow?

In our project, the file is:
```
airflow/dags/payment_pipeline.py
```

This is the DAG definition file. It's a Python script that Airflow reads and executes.

### How Does Airflow Know When to Execute What?

This is the most important concept to understand. Here's exactly how it works:

**Step 1: The Scheduler scans the DAGs folder**

The Airflow scheduler constantly watches the folder defined by `AIRFLOW_HOME/dags/`. Every 30 seconds (by default), it scans this folder for Python files containing DAG definitions.

**Step 2: It parses the DAG file**

When it finds `payment_pipeline.py`, it imports it as a Python module and reads the DAG configuration — the schedule, start date, tasks, and dependencies.

**Step 3: It checks the schedule**

Our DAG has `schedule_interval='@daily'`. This means Airflow will trigger one run per day. Other options include `@hourly`, `@weekly`, or a cron expression like `0 6 * * *` (every day at 6am).

**Step 4: It checks if a run is due**

The scheduler compares the `start_date` and `schedule_interval` to determine if a new run should be triggered. With `catchup=False`, it only runs for the current period, not for missed past periods.

**Step 5: It queues tasks respecting dependencies**

When a run is triggered, the scheduler looks at the task dependency graph and queues tasks in the correct order:
- `health_check` has no dependencies → queued immediately
- `extract_transactions` depends on `health_check` → queued only after health_check succeeds
- `extract_fx_rates` depends on `health_check` → also queued after health_check (runs in parallel with extract_transactions)
- `load_to_gcs` depends on BOTH extract tasks → queued only after both succeed
- And so on...

**Step 6: The executor runs the tasks**

We used `SequentialExecutor` (default for SQLite), which runs one task at a time. In production you'd use `CeleryExecutor` or `KubernetesExecutor` which can run tasks in parallel across many workers.

### Is Airflow Always Run by Code?

Yes and no. The **definition** of what to run is always in code (the Python DAG file). But **when** it runs can be:
1. **Automatically** — based on the schedule (`@daily`, cron expression, etc.)
2. **Manually** — clicking "Trigger DAG" in the UI or using the CLI: `airflow dags trigger payment_intelligence_pipeline`
3. **Via API** — Airflow has a REST API you can call programmatically

The DAG file itself is never "executed" directly like a regular Python script. You don't run `python payment_pipeline.py`. Instead, Airflow imports it, reads the structure, and then executes the individual task functions/bash commands at the appropriate times.

---

## 5. THE PAYMENT PIPELINE DAG - EVERY TASK EXPLAINED

Here is the full DAG we built and why each task exists:

```python
health_check >> [extract_transactions, extract_fx_rates] >> load_to_gcs >> load_to_bigquery >> dbt_run >> dbt_test >> pipeline_complete
```

### Task 1: `health_check` (PythonOperator)
**What it does**: Runs a simple Python function that prints a message and returns "healthy"

**Why it exists**: Every production pipeline should have a health check at the start. It verifies the pipeline can execute before spending time on expensive operations. In a real system, this would check database connectivity, API availability, disk space, etc.

**Operator type**: `PythonOperator` — executes a Python function directly within Airflow

### Task 2: `extract_transactions` (BashOperator)
**What it does**: Runs `python ingestion/extract_transactions.py`

**Why it exists**: Generates 10,000 synthetic payment transactions using the Faker library and saves them to a local CSV file (`data/raw_transactions.csv`)

**Operator type**: `BashOperator` — executes a shell command. We used this because our extraction scripts are standalone Python files outside of Airflow.

**Key design decision**: We point to the WSL Python binary directly (`/home/pranav_sonje/airflow-venv/bin/python`) rather than activating a virtual environment. This is because `source activate` doesn't work well inside BashOperator — it's cleaner to use the absolute path.

### Task 3: `extract_fx_rates` (BashOperator)
**What it does**: Runs `python ingestion/extract_fx_rates.py`

**Why it exists**: Calls the Open Exchange Rates API to get real FX rates for the day and saves them to CSV

**Runs in parallel with**: `extract_transactions`. Both tasks depend only on `health_check`, so Airflow runs them simultaneously. This is a key pipeline optimization — why wait for transactions to finish before starting FX extraction if they're independent?

**Dependency**: Uses `python-dotenv` to load the API key from the `.env` file. We had to install this separately because the WSL virtual environment didn't have it initially.

### Task 4: `load_to_gcs` (BashOperator)
**What it does**: Runs `python ingestion/load_to_gcs.py`

**Why it exists**: Uploads the raw CSV files from local disk to Google Cloud Storage. GCS acts as the "data lake" layer — raw, unprocessed files stored cheaply before transformation.

**Why GCS before BigQuery?**: This is the ELT pattern (Extract, Load, Transform). We land raw data in GCS first as a backup/audit trail. If something goes wrong in BigQuery, we can always reload from GCS. It's also cheaper to store raw files in GCS than in BigQuery.

**Why this was added mid-project**: Our initial DAG went directly from extraction to BigQuery, but `load_to_bigquery.py` actually reads from GCS (it was designed that way). So we needed the intermediate GCS step.

### Task 5: `load_to_bigquery` (BashOperator)
**What it does**: Runs `python ingestion/load_to_bigquery.py`

**Why it exists**: Reads the CSV files from GCS and loads them into BigQuery raw tables (`payments_raw.raw_transactions` and `payments_raw.raw_fx_rates`)

**Authentication issue we hit**: When running in WSL, Google Cloud credentials weren't available. The error was `DefaultCredentialsError: Your default credentials were not found`. We fixed this by:
1. Finding the credentials on the Windows filesystem: `/mnt/c/Users/Pranav/AppData/Roaming/gcloud/application_default_credentials.json`
2. Setting the environment variable in the DAG's `default_args`:
```python
'env': {
    'GOOGLE_APPLICATION_CREDENTIALS': '/mnt/c/Users/Pranav/AppData/Roaming/gcloud/application_default_credentials.json',
    'GOOGLE_CLOUD_PROJECT': 'payment-intelligence-488700',
}
```

### Task 6: `dbt_run` (BashOperator)
**What it does**: Runs `dbt run` inside the dbt project directory

**Why it exists**: Executes all dbt models — the staging, intermediate, and mart transformations we built in Week 2. This converts raw BigQuery tables into clean, analytics-ready tables.

**What dbt actually does when it runs**: It compiles the SQL models, determines the execution order based on `ref()` dependencies, and runs each model as a CREATE TABLE or CREATE VIEW statement in BigQuery.

### Task 7: `dbt_test` (BashOperator)
**What it does**: Runs `dbt test` inside the dbt project directory

**Why it exists**: Runs the data quality tests we defined in `schema.yml` — `not_null`, `unique`, `accepted_values`. If any test fails, this task fails, and `pipeline_complete` never runs. This is the data quality gate.

**Why test AFTER run?**: Because tests run against the actual data in BigQuery. You need the data to exist first before you can test it.

### Task 8: `pipeline_complete` (PythonOperator)
**What it does**: Prints a completion message with the timestamp

**Why it exists**: Acts as a clear success signal. In production, this task would send a Slack notification, trigger a downstream pipeline, update a metadata table, or call a webhook. Having an explicit terminal task makes the DAG graph clean and makes it easy to hook into completion events.

### Task Dependencies Explained

```python
health_check >> [extract_transactions, extract_fx_rates] >> load_to_gcs >> load_to_bigquery >> dbt_run >> dbt_test >> pipeline_complete
```

The `>>` operator sets dependencies. `[extract_transactions, extract_fx_rates]` means both tasks are downstream of `health_check` and both must succeed before `load_to_gcs` starts. This creates the parallel extraction pattern.

### default_args Explained

```python
default_args = {
    'owner': 'pranav',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'env': {
        'GOOGLE_APPLICATION_CREDENTIALS': '...',
        'GOOGLE_CLOUD_PROJECT': '...',
    }
}
```

- `retries: 1` — if a task fails, try once more before marking it as failed
- `retry_delay: timedelta(minutes=5)` — wait 5 minutes between the failure and the retry
- `env` — environment variables passed to every BashOperator task in this DAG

---

## 6. CONNECTING TO GCP FROM WSL

This was one of the trickier parts of the setup and is worth understanding deeply for interviews.

### The Problem
When our DAG ran `load_to_bigquery.py`, it failed with:
```
google.auth.exceptions.DefaultCredentialsError: Your default credentials were not found.
```

### Why This Happened
Google Cloud libraries use **Application Default Credentials (ADC)** — a standard way to authenticate. When you run `gcloud auth application-default login` on Windows, it stores credentials at:
```
C:\Users\Pranav\AppData\Roaming\gcloud\application_default_credentials.json
```

But our Airflow tasks run inside WSL (Linux). WSL has its own filesystem and doesn't automatically inherit Windows credentials. The Google library looked for credentials in the Linux default location (`~/.config/gcloud/`) and found nothing.

### The Fix
We set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point explicitly to the Windows credentials file, accessed via the WSL mount:
```
/mnt/c/Users/Pranav/AppData/Roaming/gcloud/application_default_credentials.json
```

`/mnt/c/` is how WSL accesses the Windows C: drive.

We added this to `default_args` in the DAG so every task inherits it automatically.

### Interview Talking Point
> "One of the challenges I solved was authentication between WSL and GCP. Airflow was running in WSL but the GCP credentials were on the Windows filesystem. I used the GOOGLE_APPLICATION_CREDENTIALS environment variable to bridge the two environments, passing it as a default arg in the DAG so all tasks inherited it."

---

## 7. LOOKER STUDIO DASHBOARD

### What is Looker Studio?
Looker Studio (formerly Google Data Studio) is a free business intelligence tool by Google. It connects directly to BigQuery without any intermediate steps — you just pick your table and start building charts.

### Why Looker Studio for This Project?
- Free — no cost
- Native BigQuery integration — no data exports needed, queries run directly on BigQuery
- The connection itself demonstrates that your data pipeline produced usable, query-able data
- Interviewers can see a live dashboard that updates when the pipeline runs

### What We Connected To
We connected to the `payment_intelligence` dataset in BigQuery — specifically the `mart_daily_summary` table. This is the mart layer produced by dbt, not the raw tables. This demonstrates the full pipeline value: raw data went through transformation and is now serving a business dashboard.

### The Four Charts We Built

**Chart 1: Daily Transaction Volume (Line Chart)**
- Dimension: `transaction_date`
- Metric: `total_volume_usd`
- Shows the trend of payment volume over 2024
- Business insight: spot seasonality, growth trends, anomalies

**Chart 2: Currency Breakdown (Stacked Bar)**
- Dimension: `currency`
- Metrics: `total_volume_usd`, `avg_transaction_usd`, `total_transactions`
- Shows which currencies drive the most volume
- Business insight: understand currency exposure for FX risk management

**Chart 3: Volume Share by Currency (Pie Chart)**
- Dimension: `currency`
- Metric: `total_volume_usd`
- Shows GBP at 22.7%, EUR at 18.7%, JPY at 17.8%, etc.
- Business insight: portfolio diversification, dominant currency markets

**Chart 4: Total Transactions KPI (Scorecard)**
- Metric: `total_transactions`
- Shows: 847
- Business insight: single number summary of pipeline output volume

---

## 8. KEY CONCEPTS FOR INTERVIEWS

### The ELT Pattern (Extract, Load, Transform)
Our pipeline follows ELT not ETL:
- **ETL** (old way): Transform data before loading it to the warehouse
- **ELT** (modern way): Load raw data first, then transform inside the warehouse using SQL (dbt)

Why ELT? Because cloud warehouses like BigQuery are cheap and powerful enough to do the transformation. Loading raw data first means you never lose the original — you can always re-transform if requirements change.

### Idempotency
A pipeline is idempotent if running it multiple times produces the same result as running it once. Our pipeline re-generates synthetic data on each run, so it's not perfectly idempotent — in a real system you'd want to handle deduplication. This is a good thing to mention as a known limitation.

### The Scheduler vs Executor
- **Scheduler**: Decides WHAT to run and WHEN. Reads DAG files, tracks run history, queues tasks.
- **Executor**: Decides HOW to run tasks. SequentialExecutor (one at a time), LocalExecutor (parallel on one machine), CeleryExecutor (distributed across workers), KubernetesExecutor (each task in its own pod).

We used SequentialExecutor because we used SQLite (which doesn't support concurrent writes). In production, you'd use PostgreSQL + CeleryExecutor or KubernetesExecutor.

### Why Both GCS and BigQuery?
This is a common interview question for data engineering roles:
- **GCS** = data lake = cheap, raw, unstructured storage. Think of it as a filing cabinet.
- **BigQuery** = data warehouse = expensive, structured, query-optimized. Think of it as a database built for analytics.

You land in GCS first because: (1) it's cheap insurance, (2) you can reload into BigQuery from GCS if needed, (3) GCS → BigQuery is a native, fast, serverless load job.

### SQLite vs PostgreSQL for Airflow
We used SQLite (default) because it's simple and requires no setup. But SQLite has limitations: no concurrent writes, single file, not suitable for production. In production Airflow deployments, you always use PostgreSQL or MySQL as the metadata database.

---

## 9. LIKELY INTERVIEW QUESTIONS WITH ANSWERS

**Q: Walk me through your Airflow setup.**

A: "I ran Airflow 2.9.1 natively in WSL2 Ubuntu on Windows, using SQLite as the metadata database and SequentialExecutor for local development. The DAG is defined in a Python file and picked up automatically by the Airflow scheduler. I structured the pipeline with parallel extraction tasks for transactions and FX rates, followed by GCS loading, BigQuery loading, and dbt transformations with data quality tests at the end."

---

**Q: What is a DAG and why is it acyclic?**

A: "A DAG is a Directed Acyclic Graph — it defines the tasks in a pipeline and the dependencies between them. It's acyclic because you can't have circular dependencies — if Task A depends on Task B and Task B depends on Task A, you have a deadlock with no starting point. Airflow enforces this constraint so pipelines always have a clear start and end."

---

**Q: How does Airflow know when to run a pipeline?**

A: "The Airflow scheduler continuously scans the DAGs folder for Python files. Each DAG has a `schedule_interval` — in our case `@daily`. The scheduler checks this against the last run time and queues a new run when it's due. Tasks are then queued respecting their dependencies — a task only runs after all its upstream tasks have succeeded."

---

**Q: How did you handle failures in your pipeline?**

A: "I configured `retries=1` and `retry_delay=timedelta(minutes=5)` in `default_args`, so any failed task automatically retries once after 5 minutes. The `dbt_test` task acts as a data quality gate — if tests fail, the `pipeline_complete` task never runs, making failures visible. In production I would also add alerting via email or Slack on failure callbacks."

---

**Q: Why did you use BashOperator instead of PythonOperator for the extraction tasks?**

A: "Our extraction scripts were written as standalone Python files with their own dependencies and environment setup. Using BashOperator let us invoke them exactly as they'd be run on the command line, with full control over the working directory and environment variables. PythonOperator would require importing the functions directly into the DAG file, which would create tight coupling and dependency management issues since the extraction code uses libraries not present in the Airflow virtual environment."

---

**Q: What would you change if this went to production?**

A: "Several things: (1) Replace SQLite with PostgreSQL as the Airflow metadata database, (2) Use CeleryExecutor or KubernetesExecutor for parallel task execution, (3) Add proper secret management instead of hardcoded credential paths, (4) Add email/Slack alerting on failure, (5) Make the pipeline truly idempotent by handling deduplication, (6) Add data freshness SLA monitoring, (7) Deploy Airflow on a managed service like Cloud Composer or MWAA instead of running it locally."

---

**Q: How does dbt integrate with Airflow?**

A: "dbt is invoked as a shell command via BashOperator — `dbt run` and `dbt test`. The scheduler treats dbt like any other command-line tool. This is actually the standard pattern — dbt isn't natively aware of Airflow and vice versa. In larger setups, teams use the `astronomer-cosmos` package which can parse dbt projects and create individual Airflow tasks for each dbt model, giving you more granular control and observability."

---

**Q: What is the difference between the webserver and scheduler in Airflow?**

A: "The webserver serves the UI — it's what you see at localhost:8080. It lets you view DAG runs, trigger runs manually, inspect logs, and manage connections. The scheduler is the actual brain — it reads DAG files, determines what should run and when, and queues tasks for execution. They're separate processes so the UI can be restarted independently without affecting running pipelines. This separation of concerns is good architecture."

---

*End of Week 3 Interview Notes*
*Project: Payment Intelligence Pipeline*
*GitHub: github.com/pranav1414/payment-intelligence-pipeline*




dbt Complete Reference Notes
Payment Intelligence Pipeline - Week 2

TABLE OF CONTENTS

What is dbt and Why We Used It
Project Folder Structure
Key Config Files Explained
The Three-Layer Architecture
Every SQL Model With Code and Explanation
source() vs ref() — Critical Distinction
Views vs Tables — Why It Matters
Data Quality Tests (schema.yml)
How dbt Runs
Interview Questions and Answers


1. WHAT IS dbt AND WHY WE USED IT
What is dbt?
dbt (data build tool) is a transformation framework that lets you write SQL SELECT statements and it handles turning them into tables/views in your data warehouse (BigQuery).
You write:
sqlSELECT * FROM some_table WHERE amount > 0
dbt handles:

Running the SQL in BigQuery
Creating the output as a table or view
Running it in the right order (if model B depends on model A, run A first)
Running data quality tests after

What dbt Does NOT Do
dbt does NOT move data. It does NOT extract from APIs. It does NOT load CSVs. It ONLY transforms data that is already inside BigQuery. The "T" in ELT.
Why We Used It (vs Plain SQL)
Plain SQL in BigQuerydbtScripts scattered everywhereOrganized project structureNo dependency trackingKnows model A depends on model BManual execution orderRuns models in correct order automaticallyNo testsBuilt-in data quality testsNo documentationAuto-generates a data catalogHard to version controlPure SQL files → perfect for Git
The Core Value Proposition for Interviews

"dbt brings software engineering best practices to SQL — version control, testing, documentation, and modularity. Instead of ad-hoc SQL queries scattered around, every transformation is a tested, documented, version-controlled SQL file."


2. PROJECT FOLDER STRUCTURE
Our dbt project lives at:
C:\Users\Pranav\payment-intelligence-pipeline\dbt_project\
Inside it:
dbt_project/
├── dbt_project.yml          ← project config (name, materialization settings)
├── profiles.yml             ← BigQuery connection details
├── models/
│   ├── staging/
│   │   ├── sources.yml      ← declares where raw data lives
│   │   ├── schema.yml       ← data quality tests
│   │   ├── stg_transactions.sql
│   │   └── stg_fx_rates.sql
│   ├── intermediate/
│   │   └── int_transactions_enriched.sql
│   └── marts/
│       ├── mart_daily_summary.sql
│       ├── mart_merchant_analytics.sql
│       └── mart_currency_breakdown.sql
└── target/                  ← compiled SQL (auto-generated, don't edit)

3. KEY CONFIG FILES EXPLAINED
dbt_project.yml
This is the identity file for the entire dbt project. It tells dbt:

What the project is called
Where the models folder is
What materialization to use for each layer (view vs table)

yamlname: 'payment_intelligence'
version: '1.0.0'
config-version: 2

profile: 'payment_intelligence'

model-paths: ["models"]

models:
  payment_intelligence:
    staging:
      +materialized: view      # staging models = views (cheap, always fresh)
    intermediate:
      +materialized: view      # intermediate models = views
    marts:
      +materialized: table     # mart models = tables (fast for dashboards)
Why staging and intermediate are views: Views don't store data, they just store the SQL query. Every time you query a view, it runs the SQL fresh against the source. This is cheap (no storage cost) and always reflects the latest data.
Why marts are tables: Dashboards query marts constantly. If marts were views, BigQuery would re-run all the transformation SQL every time someone opened the dashboard — very slow and expensive. Tables store the pre-computed results so queries are fast.

profiles.yml
This is the connection file. It tells dbt HOW to connect to BigQuery. This file lives in the dbt_project folder (not the default ~/.dbt/ location, which is why we use --profiles-dir . when running dbt).
yamlpayment_intelligence:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: payment-intelligence-488700
      dataset: payment_intelligence
      threads: 1
      timeout_seconds: 300
Key settings:

method: oauth — uses your Google Cloud Application Default Credentials (the same ones set up with gcloud auth)
project: payment-intelligence-488700 — your GCP project ID
dataset: payment_intelligence — ALL dbt output tables/views are created in this dataset


sources.yml (inside staging/)
This file declares your raw source data to dbt. Without this file, dbt doesn't know your raw tables exist.
yamlversion: 2

sources:
  - name: payments_raw
    database: payment-intelligence-488700
    schema: payments_raw
    tables:
      - name: raw_transactions
        description: "Raw payment transactions loaded from GCS"
      - name: raw_fx_rates
        description: "Raw FX rates from Open Exchange Rates API"
Why this file exists: It lets you use {{ source('payments_raw', 'raw_transactions') }} in your SQL instead of hardcoding the full BigQuery path payment-intelligence-488700.payments_raw.raw_transactions. Change it in one place, it updates everywhere.

4. THE THREE-LAYER ARCHITECTURE
This is the most important concept. Every professional dbt project follows this pattern:
RAW DATA (BigQuery - payments_raw dataset)
    raw_transactions    ← 10,000 rows, messy, straight from Python/GCS
    raw_fx_rates        ← 240 rows, straight from API

         ↓ dbt transforms ↓

STAGING LAYER (payment_intelligence dataset - VIEWS)
    stg_transactions    ← cleaned raw_transactions
    stg_fx_rates        ← cleaned raw_fx_rates

         ↓ dbt transforms ↓

INTERMEDIATE LAYER (payment_intelligence dataset - VIEWS)
    int_transactions_enriched  ← stg_transactions JOIN stg_fx_rates

         ↓ dbt transforms ↓

MART LAYER (payment_intelligence dataset - TABLES)
    mart_daily_summary         ← daily payment volumes by currency
    mart_merchant_analytics    ← performance by merchant
    mart_currency_breakdown    ← volume and fraud rates by currency
Layer 1: Staging

Purpose: Clean and standardize raw data. Nothing else.
Rules: No joins, no aggregations, no business logic
What you do here: Rename columns, cast types, filter nulls, lowercase strings
Output: Views (one per raw table)

Layer 2: Intermediate

Purpose: Join and enrich staging models
Rules: No aggregations, no final business metrics
What you do here: Join transactions with FX rates, calculate derived columns like amount_usd
Output: Views

Layer 3: Marts

Purpose: Final business-ready tables for dashboards and analysts
Rules: These are the "products" your pipeline delivers
What you do here: GROUP BY, COUNT, SUM, AVG — business aggregations
Output: Tables (materialized for query performance)


5. EVERY SQL MODEL WITH CODE AND EXPLANATION
stg_transactions.sql
sqlwith source as (
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
        lower(status)           as status,      -- standardize to lowercase
        country,
        city,
        is_flagged,
        current_timestamp()     as _loaded_at   -- audit column
    from source
    where transaction_id is not null            -- remove bad rows
)

select * from staged
What each part does:

{{ source('payments_raw', 'raw_transactions') }} — points to the raw BigQuery table. This is a dbt template, not plain SQL. dbt compiles it to the full path at runtime.
lower(status) — standardizes 'COMPLETED', 'Completed', 'completed' to always be 'completed'
where transaction_id is not null — removes any rows without an ID (would cause problems downstream)
current_timestamp() as _loaded_at — audit column that records when dbt processed this row
source and staged are CTEs (temporary names that only exist during query execution, never saved to BigQuery)

Output: A VIEW called stg_transactions in the payment_intelligence dataset in BigQuery.

stg_fx_rates.sql
sqlwith source as (
    select * from {{ source('payments_raw', 'raw_fx_rates') }}
),

staged as (
    select
        cast(date as date)      as date,        -- cast string to proper DATE type
        currency,
        rate_to_usd,
        current_timestamp()     as _loaded_at
    from source
    where currency is not null
      and rate_to_usd is not null
      and rate_to_usd > 0                       -- remove invalid rates
)

select * from staged
What each part does:

cast(date as date) — the raw table stores date as a string. We cast it to a proper DATE type so we can join on it with transaction_date later.
rate_to_usd > 0 — a rate of 0 or negative makes no sense and would cause division-by-zero errors in the intermediate model

Output: A VIEW called stg_fx_rates in the payment_intelligence dataset.

int_transactions_enriched.sql
sqlwith transactions as (
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
        round(t.amount / f.rate_to_usd, 2)     as amount_usd
    from transactions t
    left join fx_rates f
        on t.currency = f.currency
        and t.transaction_date = f.date
)

select * from enriched
What each part does:

{{ ref('stg_transactions') }} — references the staging VIEW we built. NOT source() because this is a dbt model, not a raw table.
LEFT JOIN — we use LEFT JOIN (not INNER JOIN) so that transactions with no matching FX rate are still included (just with null amount_usd). If we used INNER JOIN, we'd silently lose transactions.
on t.currency = f.currency and t.transaction_date = f.date — we join on BOTH currency AND date because rates change daily
round(t.amount / f.rate_to_usd, 2) — converts any currency to USD. If a transaction was 100 INR and the rate is 83.5 INR/USD, then amount_usd = 100/83.5 = 1.20

Output: A VIEW called int_transactions_enriched in payment_intelligence.

mart_daily_summary.sql
sqlwith fact as (
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
What each part does:

ref('int_transactions_enriched') — builds on top of the intermediate model. dbt knows to run int first.
count(transaction_id) — total number of transactions per day per currency
sum(amount_usd) — total USD volume
avg(amount_usd) — average transaction size
countif(is_flagged = true) — BigQuery-specific function that counts rows matching a condition
group by transaction_date, currency — one row per day per currency

Output: A TABLE called mart_daily_summary. This is what the Looker Studio dashboard connects to.

mart_merchant_analytics.sql
sqlwith fact as (
    select * from {{ ref('int_transactions_enriched') }}
),

final as (
    select
        merchant_name,
        merchant_category,
        count(transaction_id)                                           as total_transactions,
        sum(amount_usd)                                                 as total_volume_usd,
        avg(amount_usd)                                                 as avg_transaction_usd,
        countif(is_flagged = true)                                      as flagged_count,
        round(countif(is_flagged = true) / count(transaction_id), 4)   as fraud_rate,
        countif(status = 'completed')                                   as completed_count,
        countif(status = 'failed')                                      as failed_count
    from fact
    where amount_usd is not null
    group by merchant_name, merchant_category
    order by total_volume_usd desc
)

select * from final
What each part does:

round(countif(is_flagged = true) / count(transaction_id), 4) — calculates fraud rate as a percentage per merchant. e.g. 0.0312 = 3.12% fraud rate
order by total_volume_usd desc — merchants sorted by highest volume first

Output: A TABLE called mart_merchant_analytics.

mart_currency_breakdown.sql
sqlwith fact as (
    select * from {{ ref('int_transactions_enriched') }}
),

final as (
    select
        currency,
        count(transaction_id)                                           as total_transactions,
        sum(amount_usd)                                                 as total_volume_usd,
        avg(amount_usd)                                                 as avg_transaction_usd,
        min(amount_usd)                                                 as min_transaction_usd,
        max(amount_usd)                                                 as max_transaction_usd,
        countif(is_flagged = true)                                      as flagged_transactions,
        round(countif(is_flagged = true) / count(transaction_id), 4)   as fraud_rate
    from fact
    where amount_usd is not null
    group by currency
    order by total_volume_usd desc
)

select * from final
Output: A TABLE called mart_currency_breakdown.

6. SOURCE() VS REF() — CRITICAL DISTINCTION
This is asked in almost every dbt interview question.
{{ source('dataset', 'table') }}

Use when referencing raw tables that exist OUTSIDE dbt
These are tables that were loaded by Python/GCS, not created by dbt
In our project: raw_transactions and raw_fx_rates in the payments_raw dataset
Defined in sources.yml

{{ ref('model_name') }}

Use when referencing another dbt model (a SQL file in your project)
dbt uses this to build the dependency graph — it knows the execution order
In our project: stg_transactions, stg_fx_rates, int_transactions_enriched

Why ref() is Powerful
When you write ref('stg_transactions') inside int_transactions_enriched.sql, dbt automatically knows:

int_transactions_enriched depends on stg_transactions
Therefore: build stg_transactions FIRST, then build int_transactions_enriched
If stg_transactions fails, don't even try to build the intermediate model

This is the DAG (Directed Acyclic Graph) that dbt builds from your ref() calls. You never have to manually specify execution order — dbt figures it out.

7. VIEWS VS TABLES — WHY IT MATTERS
View

Just stores the SQL query definition, not the actual data
Every time you query it, BigQuery re-runs the SQL
Zero storage cost
Always fresh — reflects changes in source data immediately
Slower to query (re-computes every time)

Table (Materialized)

Physically stores the query results as data
Querying it is fast — data is already computed and stored
Has storage cost
Stale until dbt runs again and refreshes it

Our Choices and Why
Staging = Views because:

Queried infrequently (mostly by intermediate models during dbt runs)
We want them always fresh
Storage cost is not worth it for cleaning logic

Intermediate = Views because:

Same reasons — these are steps in the transformation, not final outputs
Nobody queries intermediate models directly

Marts = Tables because:

Dashboards (Looker Studio) query these constantly
Making analysts wait for BigQuery to re-run all transformation SQL every time they open a dashboard is unacceptable
We pay a small storage cost in exchange for fast queries


8. DATA QUALITY TESTS (schema.yml)
We added tests to our staging models in schema.yml:
yamlversion: 2

models:
  - name: stg_transactions
    description: "Cleaned payment transactions"
    columns:
      - name: transaction_id
        description: "Unique transaction identifier"
        tests:
          - not_null        # every row must have a transaction_id
          - unique          # no two rows can have the same transaction_id
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
    description: "Cleaned FX rates from Open Exchange Rates API"
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
The Four Test Types We Used
not_null: Checks that a column never has NULL values. If any row has NULL in that column, the test fails.
unique: Checks that every value in a column is distinct. For transaction_id, this ensures we don't have duplicate transactions.
accepted_values: Checks that a column only contains specific values. If status has a value like 'CANCELLED' that's not in our list, the test fails — catching data quality issues upstream.
relationships (we discussed but didn't add): Checks referential integrity — like a foreign key check. e.g., every transaction_id in the intermediate model must exist in stg_transactions.
How to Run Tests
bashdbt test
Or test a specific model:
bashdbt test --select stg_transactions
Why Tests Matter for Interviews

"I implemented dbt tests including not_null, unique, and accepted_values on my staging models. In the Airflow DAG, dbt_test runs as a separate task after dbt_run — if any test fails, the pipeline stops and pipeline_complete never executes. This means a data quality failure is visible in the Airflow UI, not silently ignored."


9. HOW dbt RUNS
Commands We Used
dbt debug — tests the connection to BigQuery. Run this first to verify setup.
bashdbt debug --profiles-dir .
dbt run — compiles and runs all models, creating views/tables in BigQuery.
bashdbt run --profiles-dir .
dbt run --select staging — runs only the staging layer models.
dbt test — runs all tests defined in schema.yml.
bashdbt test --profiles-dir .
dbt run && dbt test — run models, then immediately test them.
Why --profiles-dir .?
By default dbt looks for profiles.yml in ~/.dbt/. We stored ours inside the project folder (dbt_project/profiles.yml) so we tell dbt where to find it with --profiles-dir . (the . means "current directory").
What Happens When You Run dbt run

dbt reads dbt_project.yml to understand the project structure
dbt reads profiles.yml to connect to BigQuery
dbt scans all .sql files in the models/ folder
dbt builds a dependency graph from all ref() calls
dbt determines execution order (staging → intermediate → marts)
dbt compiles each SQL model (replaces ref() and source() with actual BigQuery paths)
dbt runs each compiled SQL in BigQuery as CREATE OR REPLACE VIEW or CREATE OR REPLACE TABLE
dbt reports PASS/FAIL for each model

The Output We Got
23:39:14  Running with dbt=1.7.19
23:39:14  1 of 6 START sql view model payment_intelligence.stg_fx_rates
23:39:15  1 of 6 OK created sql view model payment_intelligence.stg_fx_rates [CREATE VIEW in 1.24s]
23:39:15  2 of 6 START sql view model payment_intelligence.stg_transactions
23:39:16  2 of 6 OK created sql view model payment_intelligence.stg_transactions [1.15s]
23:39:16  3 of 6 START sql view model payment_intelligence.int_transactions_enriched
...
Done. PASS=6 WARN=0 ERROR=0 SKIP=0 TOTAL=6

10. INTERVIEW QUESTIONS AND ANSWERS
Q: What is dbt and what does it do?
A: "dbt is a transformation tool that lets you write SQL SELECT statements and handles turning them into tables or views in your data warehouse. It adds software engineering practices to SQL — version control, testing, documentation, and dependency management. In our project, dbt takes raw payment data in BigQuery and transforms it through a three-layer architecture into analytics-ready mart tables."

Q: What's the difference between source() and ref() in dbt?
A: "source() is used to reference raw tables that were loaded from outside dbt — in our case, raw_transactions loaded from GCS via Python scripts. ref() is used to reference other dbt models. The key reason to use ref() is that dbt uses it to build the dependency graph — it automatically knows to run stg_transactions before int_transactions_enriched because int uses ref('stg_transactions')."

Q: Why did you use views for staging but tables for marts?
A: "Staging and intermediate models are transformation steps, not final outputs. Views are zero-cost storage and always fresh — perfect for cleaning logic that runs during dbt runs. Mart models are queried constantly by dashboards. If they were views, BigQuery would re-run all transformation SQL every time the dashboard loaded, which would be slow and expensive. Tables pre-compute the results so dashboard queries are fast."

Q: How does dbt know the order to run models?
A: "dbt builds a DAG automatically from ref() calls. When int_transactions_enriched uses ref('stg_transactions'), dbt adds an edge in the graph: stg_transactions must run before int_transactions_enriched. dbt then does a topological sort and executes models in that order. You never have to manually specify execution order."

Q: How did you ensure data quality in your pipeline?
A: "I implemented dbt schema tests on staging models — not_null on critical columns, unique on transaction_id to prevent duplicates, and accepted_values on status to catch unexpected values. In the Airflow DAG, dbt_test is a separate task that runs after dbt_run. If any test fails, the pipeline_complete task never executes, making data quality failures visible in the Airflow UI."

Q: Walk me through the data flow in your dbt project.
A: "Raw transactions and FX rates land in BigQuery's payments_raw dataset via our Python ingestion scripts. dbt staging models clean this data — renaming columns, casting types, filtering nulls — and create views in the payment_intelligence dataset. The intermediate model joins transactions with FX rates using a left join on both currency and date, calculating amount_usd for every transaction. Finally, three mart tables aggregate this enriched data — daily payment volumes by currency, performance by merchant, and breakdown by currency. These mart tables are what the Looker Studio dashboard queries."

End of dbt Reference Notes
Project: Payment Intelligence Pipeline
GitHub: github.com/pranav1414/payment-intelligence-pipeline