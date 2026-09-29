  export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/mba-ai-gdelt-key.json"

  nohup uv run --with google-cloud-bigquery --with google-cloud-storage --with pyarrow \
    python scripts/bigquery_ctas_export_gdelt_events.py \
    --project mba-ai-509708 --from 2015-02 --to 2020-01 \
    > gdelt-events-5y.log 2>&1 &
  disown

  nohup uv run algo-download run --source gpr > gpr-download.log 2>&1 &
  disown
