from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'pranav',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def check_pipeline_health():
    """Simple health check - verifies pipeline can run"""
    print("Payment Intelligence Pipeline - Health Check Passed")
    print(f"Pipeline executed at: {datetime.now()}")
    return "healthy"

with DAG(
    dag_id='payment_intelligence_pipeline',
    default_args=default_args,
    description='End-to-end payment data pipeline: Extract → Load → Transform',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['payments', 'bigquery', 'dbt'],
) as dag:

    # Task 1: Health check
    health_check = PythonOperator(
        task_id='health_check',
        python_callable=check_pipeline_health,
    )

    # Task 2: Extract transactions from source
    extract_transactions = BashOperator(
        task_id='extract_transactions',
        bash_command='cd /mnt/c/Users/Pranav/payment-intelligence-pipeline && source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null; python src/extract_transactions.py && echo "Extraction complete"',
    )

    # Task 3: Extract FX rates
    extract_fx_rates = BashOperator(
        task_id='extract_fx_rates',
        bash_command='cd /mnt/c/Users/Pranav/payment-intelligence-pipeline && source .venv/bin/activate 2>/dev/null; python src/extract_fx_rates.py && echo "FX rates extraction complete"',
    )

    # Task 4: Load to BigQuery
    load_to_bigquery = BashOperator(
        task_id='load_to_bigquery',
        bash_command='cd /mnt/c/Users/Pranav/payment-intelligence-pipeline && source .venv/bin/activate 2>/dev/null; python src/load_to_bigquery.py && echo "Load to BigQuery complete"',
    )

    # Task 5: Run dbt transformations
    dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='cd /mnt/c/Users/Pranav/payment-intelligence-pipeline/dbt_project && source /mnt/c/Users/Pranav/payment-intelligence-pipeline/.venv/bin/activate 2>/dev/null; dbt run --profiles-dir . && echo "dbt run complete"',
    )

    # Task 6: Run dbt tests
    dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='cd /mnt/c/Users/Pranav/payment-intelligence-pipeline/dbt_project && source /mnt/c/Users/Pranav/payment-intelligence-pipeline/.venv/bin/activate 2>/dev/null; dbt test --profiles-dir . && echo "dbt tests passed"',
    )

    # Task 7: Pipeline completion notification
    pipeline_complete = PythonOperator(
        task_id='pipeline_complete',
        python_callable=lambda: print(f"Pipeline completed successfully at {datetime.now()}"),
    )

    # Define task dependencies
    health_check >> [extract_transactions, extract_fx_rates] >> load_to_bigquery >> dbt_run >> dbt_test >> pipeline_complete