# Week 1

# Payment Intelligence Pipeline — Complete Interview Notes
> Built by Pranav | Week 1 Complete | Last updated: February 26, 2026

---

## TABLE OF CONTENTS
1. What is this project?
2. The Tech Stack (and why each tool)
3. Key Concepts to Know
4. Step-by-Step: Everything We Did
5. Commands Reference
6. Interview Questions & Answers
7. Architecture Summary

---

## 1. WHAT IS THIS PROJECT?

A fully automated, end-to-end payments analytics pipeline built on a 100% free stack. It:
- Generates 10,000 realistic payment transactions
- Pulls real currency exchange rates from an API
- Stores raw data in Google Cloud Storage (data lake)
- Loads data into BigQuery (data warehouse)
- Transforms data using dbt (SQL models)
- Orchestrates everything with Apache Airflow (automation)
- Visualizes insights in Looker Studio (dashboard)

This is the same architecture used at companies like Stripe, Square, Chime, and Plaid.

**GitHub:** https://github.com/pranav1414/payment-intelligence-pipeline

---

## 2. THE TECH STACK

| Layer | Tool | Why we chose it |
|---|---|---|
| Data Generation | Python + Faker | Generate realistic synthetic payment data |
| Orchestration | Apache Airflow | Schedule and automate the pipeline daily |
| Raw Storage | Google Cloud Storage (GCS) | Cloud hard drive — stores raw files safely |
| Warehouse | BigQuery | Run SQL queries on large datasets |
| Transformation | dbt Core | Write SQL models to clean and transform data |
| Data Quality | Great Expectations | Validate data after each pipeline run |
| Containerization | Docker | Run Airflow locally without cloud cost |
| Version Control | GitHub | Store code + CI/CD via GitHub Actions |
| Visualization | Looker Studio | Free BI dashboard connected to BigQuery |

---

## 3. KEY CONCEPTS TO KNOW

### What is ELT?
ELT stands for Extract → Load → Transform. It is the modern approach to data engineering.

- **Extract** = Pull/generate the raw data (`extract_transactions.py`, `extract_fx_rates.py`)
- **Load** = Store it in the cloud (`load_to_gcs.py`, `load_to_bigquery.py`)
- **Transform** = Clean and reshape it inside the warehouse (dbt models)

Old approach was ETL (transform before loading). Modern approach is ELT because warehouses like BigQuery are powerful enough to do transformations inside them using SQL.

---

### What is an API?
API stands for Application Programming Interface. It is a door that lets your Python code talk to an external service and get data back automatically.

**Real example:** Instead of you going to a website, typing your city, and reading the weather yourself — your Python code sends a request to a weather API and gets the temperature back as data in 1 second.

In our project: `extract_fx_rates.py` calls the Open Exchange Rates API to get real historical currency exchange rates. The API returns JSON data like:
```json
{
  "USD": 1.0,
  "EUR": 0.906,
  "INR": 83.20,
  "JPY": 141.11
}
```

**"Pull from API"** = your Python script sends a request to a website and that website sends back data automatically.

---

### What is a Library?
A library is a tool someone else already built that you can plug into your code. Instead of writing everything from scratch, you install a library and use its functions.

**Examples in our project:**
- `Faker` — generates fake but realistic data (names, companies, cities)
- `Pandas` — manipulates data in table format (like Excel in Python)
- `google-cloud-bigquery` — lets Python talk to BigQuery
- `google-cloud-storage` — lets Python talk to GCS
- `requests` — lets Python make API calls

---

### GCS vs BigQuery — What's the difference?

**GCS (Google Cloud Storage)**
- Like Google Drive or Dropbox for your code
- Stores raw files (CSV, JSON, Parquet)
- Cannot run SQL queries on it
- Cannot filter, aggregate, or analyze data
- Just a dump of raw files — nothing more
- This is your DATA LAKE

**BigQuery**
- A full database engine built for analytics
- Can run SQL queries on billions of rows in seconds
- Can do GROUP BY, JOIN, window functions, aggregations
- This is where actual analysis happens
- This is your DATA WAREHOUSE

**Analogy:**
- GCS = storage room where raw ingredients are kept (flour, eggs, vegetables)
- BigQuery = kitchen where ingredients are cooked into actual meals
- dbt = the recipes that tell the kitchen how to cook

---

### What is a Virtual Environment (.venv)?
A virtual environment is an isolated Python installation for your project. It keeps your project's dependencies separate from your system Python.

**Why it matters:** If Project A needs `pandas==1.0` and Project B needs `pandas==2.0`, without virtual environments they would conflict. With `.venv`, each project has its own isolated packages.

**How to activate on Windows:**
```powershell
.venv\Scripts\activate
```
You know it's active when you see `(.venv)` at the start of your terminal prompt.

---

### What is Idempotency?
Idempotency means you can run the pipeline multiple times and always get the same result — no duplicate data.

**In our project:** We use `WRITE_TRUNCATE` in BigQuery, which means every time you run `load_to_bigquery.py`, it replaces the existing table instead of appending to it. So running it twice doesn't double your rows.

This is a critical production concept. Interviewers love this word.

---

### What is Date Partitioning?
Instead of dumping all files in one flat folder, we organize files by date:
```
gs://payment-intelligence-pipeline/
└── transactions/
    └── year=2026/
        └── month=02/
            └── day=26/
                └── raw_transactions.csv
```

**Why it matters:**
- Never overwrites old data — each day's run is preserved
- If something goes wrong today, yesterday's data is safe
- BigQuery can scan specific date partitions instead of everything — much faster
- Called IMMUTABLE RAW STORAGE — a core DE principle

---

### What is Cloud Authentication?
Think of it as a 3-layer security system:

```
API (the door)          → Enabled in Google Cloud Console
Service Account (ID badge) → Identity for your Python code
Roles (room access)     → What the code is allowed to do
```

Without any one of these, your code gets blocked with a 403 Permission Denied error.

**In our project:**
- We enabled BigQuery API and Cloud Storage API (unlocked the doors)
- We created a service account called `pipeline-sa` (gave the code an ID)
- We assigned `BigQuery Admin` and `Storage Admin` roles (gave access to rooms)
- We used `gcloud auth application-default login` instead of a key file (modern, secure approach)

**Why no key file?** Google now blocks JSON key creation by default on new accounts for security. Application Default Credentials (ADC) is the modern, safer alternative. Your code automatically picks up credentials without needing a file.

---

### What is a Service Account?
A Service Account is a Google identity for your code — not for a human, but for a program. It tells Google Cloud "this is my code, please allow it to do X."

In real companies, every application has its own service account with only the minimum permissions it needs. This is called the Principle of Least Privilege.

---

### Why Two Load Steps (GCS then BigQuery)?
You could technically skip GCS and load directly from your laptop into BigQuery. But in production you never do that because:

1. **GCS acts as a backup** — if BigQuery load fails, raw data is still safe in GCS
2. **Replay ability** — you can reload into BigQuery anytime from GCS without re-running extraction
3. **Separation of concerns** — storage and querying are kept separate
4. **Audit trail** — you always have the original raw files untouched

---

### What is Faker?
Faker is a Python library that generates fake but realistic data. It can create:
- Company names: "Rodriguez, Figueroa and Sanchez"
- Cities: "Lake Joyside"
- Country codes: "CU", "AT", "GN"

We used `Faker.seed(42)` to make results reproducible — every time you run the script you get the same data. This is important for testing.

---

## 4. STEP-BY-STEP: EVERYTHING WE DID

---

### PHASE 0: Project Planning

Before writing any code we designed the full architecture:

**Pipeline layers:**
1. Source APIs → Python ingestion scripts
2. Ingestion Layer → Python extracts raw JSON/CSV → lands in GCS
3. Airflow Orchestration → schedules everything, triggers dbt runs
4. BigQuery Warehouse → Raw → Staging → Mart layers
5. dbt Transformations → cleans raw data, creates analytics models
6. Data Quality → Great Expectations validates after each load
7. Analytics Layer → Looker Studio dashboard

**Project focus:** Payments / Transaction Analytics (leverages fintech background)

---

### PHASE 1: Setting Up the Repository

#### What is a Repository?
A repository (repo) is a folder tracked by Git — it saves every version of your code so you can go back in time and collaborate with others.

#### Step 1: Create the project folder
```powershell
mkdir payment-intelligence-pipeline
cd payment-intelligence-pipeline
```
- `mkdir` = "make directory" = creates a new folder
- `cd` = "change directory" = moves into that folder

#### Step 2: Initialize Git
```powershell
git init
```
This turns the folder into a Git repository. It creates a hidden `.git` folder that tracks all changes.

#### Step 3: Create the folder structure
```powershell
mkdir -p ingestion/tests
mkdir -p dbt_project/models/staging
mkdir -p dbt_project/models/marts
mkdir -p airflow/dags
mkdir -p great_expectations/expectations
mkdir -p .github/workflows
mkdir -p architecture
```
`-p` means "create parent folders too if they don't exist"

**Why this structure?** Each folder maps to one layer of the pipeline. This signals to hiring managers that you think in systems, not just scripts.

#### Step 4: Create placeholder files
On Windows, we used PowerShell's `New-Item` instead of `touch` (which is a Mac/Linux command):
```powershell
New-Item -ItemType File -Path "ingestion/extract_transactions.py" -Force
```
`-Force` means create parent directories if they don't exist.

#### Step 5: Create .gitignore
The `.gitignore` file tells Git which files to NEVER track or push to GitHub.

**Critical entries:**
```
.env                    ← contains secret API keys
credentials.json        ← contains GCP service account key
.venv/                  ← virtual environment (thousands of files)
__pycache__/            ← Python compiled files
data/                   ← generated data files (large CSVs)
```

**Why .env and credentials.json?** If you push these to GitHub, anyone in the world can use your Google Cloud account and rack up charges. This is the #1 security mistake junior engineers make.

#### Step 6: Create requirements.txt
Lists all Python packages the project needs with exact version numbers:
```
faker==24.0.0
pandas==2.2.0
google-cloud-storage==2.14.0
google-cloud-bigquery==3.17.0
dbt-bigquery==1.7.0
great-expectations==0.18.0
python-dotenv==1.0.0
pytest==8.0.0
requests==2.31.0
```
Pinning exact versions ensures anyone cloning your repo gets the same environment. Production best practice.

#### Step 7: Create .env file
Stores secret configuration values locally:
```
GCP_PROJECT_ID=payment-intelligence-488700
GCP_BUCKET_NAME=payment-intelligence-pipeline
BIGQUERY_DATASET=payments_raw
OPEN_EXCHANGE_RATES_APP_ID=your-api-key
```
The `python-dotenv` library loads these into your Python code at runtime using `os.getenv("GCP_PROJECT_ID")`.

#### Step 8: Create Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\activate    # Windows
```
After activation you see `(.venv)` in your terminal prompt — confirms it's active.

#### Step 9: Install dependencies
```powershell
pip install -r requirements.txt
```
`pip` = Python's package installer. This reads requirements.txt and installs everything.

#### Step 10: First Git commit
```powershell
git add .
git commit -m "feat: initial project scaffold"
```
- `git add .` = stage ALL changed files for commit
- `git commit -m "..."` = save a snapshot with a message

**Commit message convention:** `feat:` means a new feature. Other prefixes: `fix:`, `docs:`, `refactor:`

#### Step 11: Push to GitHub
```powershell
git remote add origin https://github.com/pranav1414/payment-intelligence-pipeline.git
git branch -M main
git push -u origin main
```
- `git remote add origin` = links your local repo to GitHub
- `git branch -M main` = renames default branch to "main"
- `git push -u origin main` = pushes code to GitHub

---

### PHASE 2: Writing the Data Generator

**File:** `ingestion/extract_transactions.py`

**Purpose:** Generate 10,000 realistic payment transactions using Faker library and save as CSV.

#### Key design decisions:

**1. Category-specific amount ranges:**
```python
AMOUNT_RANGES = {
    "travel":        (50, 2000),   # travel is expensive
    "subscriptions": (5, 50),      # Netflix/Spotify are cheap
    "groceries":     (10, 200),
}
```
This makes data realistic — travel transactions are bigger than subscription transactions.

**2. Weighted status distribution:**
```python
STATUSES = ["completed", "completed", "completed", "failed", "pending"]
```
"completed" appears 3 times out of 5 = 60% completion rate. Reflects real-world payment success rates.

**3. Fraud flag:**
```python
"is_flagged": random.random() < 0.02   # 2% fraud rate
```
Real-world payment fraud rate is ~1-3%. We simulated this realistically.

**4. Faker seed:**
```python
Faker.seed(42)
random.seed(42)
```
Setting seed = 42 makes results reproducible. Every run produces identical data. Critical for testing.

**5. Logging:**
```python
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
```
Professional code logs what it's doing. You can see exactly what happened and when.

**Result:** 10,000 rows with 13 columns saved to `data/raw_transactions.csv`

**To run:**
```powershell
mkdir data
python ingestion/extract_transactions.py
```

---

### PHASE 3: Setting Up Google Cloud

#### Step 1: Create GCP Account
- Go to https://cloud.google.com/free
- Get $300 free credits + permanent free tier
- Created project called `payment-intelligence` (ID: `payment-intelligence-488700`)

#### Step 2: Enable APIs
Go to https://console.cloud.google.com/apis/library

Enabled:
- **BigQuery API** — allows Python to talk to BigQuery
- **Cloud Storage API** — allows Python to talk to GCS

**Why enable APIs?** Google Cloud is like a building with many locked rooms. Enabling an API = unlocking that room. Without it, your code gets 403 Permission Denied.

#### Step 3: Create Service Account
- Name: `pipeline-sa`
- Roles: `BigQuery Admin` + `Storage Admin`
- Email: `pipeline-sa@payment-intelligence-488700.iam.gserviceaccount.com`

**What is a Service Account?** A Google identity for your code. Not for a human — for a program. It carries an ID so Google knows what your code is allowed to do.

#### Step 4: Authentication
JSON key creation was blocked by Google's security policy on new accounts. Used Application Default Credentials (ADC) instead — the modern, more secure approach.

**Install Google Cloud CLI:**
Download from https://cloud.google.com/sdk/docs/install

**Authenticate:**
```powershell
gcloud init
gcloud auth application-default login
gcloud config set project payment-intelligence-488700
```

**Verify Python can authenticate:**
```powershell
python -c "import google.auth; creds, project = google.auth.default(); print('Auth working! Project:', project)"
```

#### Step 5: Create GCS Bucket
```powershell
gsutil mb -p payment-intelligence-488700 -l US gs://payment-intelligence-pipeline/
```
- `gsutil` = Google Cloud Storage command line tool
- `mb` = make bucket
- `-l US` = location United States
- `gs://` = Google Storage URL prefix

---

### PHASE 4: Upload to Google Cloud Storage

**File:** `ingestion/load_to_gcs.py`

**Purpose:** Upload raw CSV files from laptop to Google Cloud Storage with date partitioning.

#### Key design decision — Date Partitioning:
```python
gcs_path = (
    f"{gcs_folder}/"
    f"year={today.year}/"
    f"month={today.month:02d}/"
    f"day={today.day:02d}/"
    f"{filename}"
)
```

Result: `gs://payment-intelligence-pipeline/transactions/year=2026/month=02/day=26/raw_transactions.csv`

**Why partition by date?**
- Never overwrites old data
- Each day's raw file is preserved forever
- Called IMMUTABLE RAW STORAGE
- BigQuery can scan specific partitions — much faster queries
- If pipeline fails today, yesterday's data is safe

**To run:**
```powershell
python ingestion/load_to_gcs.py
```

---

### PHASE 5: Load into BigQuery

**File:** `ingestion/load_to_bigquery.py`

**Purpose:** Load CSV from GCS into BigQuery table for SQL querying.

#### Key design decisions:

**1. Explicit schema definition:**
```python
schema = [
    bigquery.SchemaField("transaction_id",   "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("amount",           "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("is_flagged",       "BOOLEAN", mode="NULLABLE"),
]
```
Always define schema explicitly — never let BigQuery auto-detect. Auto-detect can guess wrong data types (e.g., reading a date as a string).

**2. WRITE_TRUNCATE (Idempotency):**
```python
write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
```
Replaces the entire table on each run. Running the pipeline twice = same result, no duplicates. This is IDEMPOTENCY.

Alternative: `WRITE_APPEND` adds rows each time — creates duplicates if you re-run.

**3. Auto-create dataset:**
```python
def create_dataset_if_not_exists(client):
    try:
        client.get_dataset(dataset_ref)
    except:
        client.create_dataset(dataset)
```
If the dataset doesn't exist, create it. Makes the pipeline self-healing.

**Result:** 10,000 rows loaded into `payment-intelligence-488700.payments_raw.raw_transactions`

**To run:**
```powershell
python ingestion/load_to_bigquery.py
```

**First SQL query run in BigQuery:**
```sql
SELECT
  merchant_category,
  COUNT(*) AS total_transactions,
  ROUND(SUM(amount), 2) AS total_amount,
  ROUND(AVG(amount), 2) AS avg_amount
FROM `payment-intelligence-488700.payments_raw.raw_transactions`
GROUP BY merchant_category
ORDER BY total_amount DESC;
```

**Results:**
- Travel: $1,066,760 total, $1,017 avg
- Subscriptions: $28,093 total, $26.99 avg
- Confirmed data was loaded correctly ✅

---

### PHASE 6: FX Rates from Real API

**File:** `ingestion/extract_fx_rates.py`

**Purpose:** Pull real historical currency exchange rates from Open Exchange Rates API.

#### Why do we need FX rates?
Transactions are in 8 currencies (USD, EUR, INR, GBP, CAD, AUD, SGD, JPY). To compare amounts fairly across currencies, everything needs to be converted to USD. FX rates provide the conversion factor.

Example: 1000 INR × (1/83.20) = $12.02 USD

#### Why only 30 dates?
Free plan = 1,000 API calls/month. Fetching all 365 days = 365 calls just for one run. We sample 30 evenly spaced dates across 2024 instead. In dbt we'll use the closest available date for each transaction — called a POINT-IN-TIME LOOKUP.

#### How the API call works:
```python
url = f"https://openexchangerates.org/api/historical/{date}.json"
params = {"app_id": APP_ID, "symbols": "EUR,GBP,INR,...", "base": "USD"}
response = requests.get(url, params=params)
rates = response.json()["rates"]
```
1. Build URL with the date we want
2. Add API key + currencies as parameters
3. `requests.get()` sends HTTP request to the API
4. `.json()` parses the response into a Python dictionary

**Result:** 240 records (8 currencies × 30 dates) saved to `data/raw_fx_rates.csv`

**Three columns:**
```
date       | currency | rate_to_usd
2024-01-01 | INR      | 83.202850
2024-01-01 | EUR      | 0.906074
2024-01-01 | USD      | 1.000000
```

**Note:** The actual `amount_usd` conversion column does NOT exist yet in this file. It gets created in Week 2 when dbt joins transactions + FX rates inside BigQuery.

**To run:**
```powershell
python ingestion/extract_fx_rates.py
```

**Upload to GCS:**
```powershell
python -c "from ingestion.load_to_gcs import upload_to_gcs; upload_to_gcs('data/raw_fx_rates.csv', 'fx_rates')"
```

---

## 5. COMMANDS REFERENCE

| Command | What it does |
|---|---|
| `mkdir foldername` | Creates a new folder |
| `cd foldername` | Move into a folder |
| `pwd` | Print current directory (where am I?) |
| `git init` | Initialize a git repository |
| `git add .` | Stage all changed files |
| `git commit -m "message"` | Save a snapshot of your code |
| `git push` | Upload commits to GitHub |
| `python -m venv .venv` | Create virtual environment |
| `.venv\Scripts\activate` | Activate virtual environment (Windows) |
| `pip install -r requirements.txt` | Install all dependencies |
| `gcloud init` | Initialize Google Cloud CLI |
| `gcloud auth application-default login` | Authenticate Python with GCP |
| `gsutil mb gs://bucket-name/` | Create a GCS bucket |

---

## 6. INTERVIEW QUESTIONS & ANSWERS

**Q: Why did you use GCS before BigQuery instead of loading directly?**
A: GCS acts as a backup raw storage layer. If the BigQuery load fails, the raw data is still safely in GCS and can be reloaded without re-running extraction. It also separates storage from compute — a core data engineering principle.

**Q: What is idempotency and how did you implement it?**
A: Idempotency means running the pipeline multiple times produces the same result with no duplicates. I implemented it using WRITE_TRUNCATE in BigQuery, which replaces the table on each run instead of appending.

**Q: Why did you choose BigQuery over Snowflake?**
A: BigQuery's serverless model fits batch workloads with unpredictable query patterns — no cluster management needed. The free 10GB/month tier also made it accessible for this project. In production I'd evaluate cost per TB scanned vs Snowflake's credit model based on query frequency.

**Q: What happens if the pipeline fails midway?**
A: The raw data is safely in GCS. Since each step is independent, I can restart from any point. The BigQuery load uses WRITE_TRUNCATE so re-running won't create duplicates. In production this would be handled by Airflow's retry logic.

**Q: How would you scale this to 10x data volume?**
A: The date partitioning in GCS is already in place. In BigQuery I'd add table partitioning and clustering by `merchant_category`. At higher volumes I'd switch from batch to streaming ingestion using Pub/Sub → Dataflow.

**Q: Why did you use date partitioning in GCS?**
A: To implement immutable raw storage. Each day's data lands in its own folder so it's never overwritten. This gives us a complete audit trail and the ability to replay the pipeline from any historical date.

**Q: What is ELT and how does it differ from ETL?**
A: ETL transforms data before loading it into the warehouse. ELT loads raw data first, then transforms it inside the warehouse using SQL. ELT is the modern approach because warehouses like BigQuery are powerful enough to handle transformations at scale, and keeping raw data untouched gives you more flexibility.

---

## 7. ARCHITECTURE SUMMARY

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                         │
│  Faker Library (synthetic)  +  Open Exchange Rates API  │
└────────────────────┬────────────────────────────────────┘
                     │ Extract
                     ▼
┌─────────────────────────────────────────────────────────┐
│              GOOGLE CLOUD STORAGE (Data Lake)           │
│  transactions/year=2026/month=02/day=26/               │
│  fx_rates/year=2026/month=02/day=26/                   │
└────────────────────┬────────────────────────────────────┘
                     │ Load
                     ▼
┌─────────────────────────────────────────────────────────┐
│              BIGQUERY (Data Warehouse)                  │
│  payments_raw.raw_transactions  (10,000 rows)          │
│  payments_raw.raw_fx_rates      (240 rows)             │
└────────────────────┬────────────────────────────────────┘
                     │ Transform (Week 2)
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    DBT MODELS                           │
│  staging: stg_transactions, stg_fx_rates               │
│  marts: mart_daily_summary, mart_merchant_analytics    │
└────────────────────┬────────────────────────────────────┘
                     │ Visualize (Week 4)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              LOOKER STUDIO DASHBOARD                    │
│  Transaction trends, merchant analytics, fraud flags   │
└─────────────────────────────────────────────────────────┘

All orchestrated by APACHE AIRFLOW running via Docker
```

---
## 8. ELT PROCESS EXPLANATION (For Interviews)

In the ELT process:
Extract:

Generated 10,000 synthetic payment transactions using the Faker library in extract_transactions.py and saved them as raw_transactions.csv on the local machine
Pulled real historical currency exchange rates for 30 dates across 2024 from the Open Exchange Rates API in extract_fx_rates.py and saved them as raw_fx_rates.csv on the local machine

Load:

Uploaded both CSV files from the local machine to Google Cloud Storage (GCS) using load_to_gcs.py, organized in date-partitioned folders (year=2026/month=02/day=27/)
Loaded the transactions CSV from GCS into a BigQuery table called raw_transactions inside the payments_raw dataset using load_to_bigquery.py — 10,000 rows now queryable via SQL

Transform:

Not done yet — happening in Week 2 using dbt, where we will join transactions with FX rates inside BigQuery to create clean, analytics-ready tables with a new amount_usd column

*Week 1 complete. Next: Week 2 — dbt models and SQL transformations.* 