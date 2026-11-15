#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
export AIRFLOW_HOME=~/airflow
export AIRFLOW__CORE__DAGS_FOLDER="$(pwd)/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export PYTHONPATH="$(pwd)"
export NO_PROXY="*"
airflow standalone
