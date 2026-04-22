# R/IGCSE Pipeline

This repository maintains two pipeline entrypoints:

- `pipeline.py`: local/manual pipeline entrypoint.
- `githubpipeline.py`: GitHub Actions pipeline entrypoint.

## GitHub Actions CI/CD

Workflow file: `.github/workflows/pipeline.yml`

Triggers:

- Push to `main`
- Monthly schedule (`0 0 1 * *`)

Job chain and artifacts:

- `validate`
- `schedule-data` -> uploads `schedule-data` artifact (`output/schedule/schedule.csv`)
- `download-pdfs` -> uploads `pdf-downloads` artifact (`output/pdf`)
- `extract-csvs` -> uploads `extracted-csvs` artifact (`output/csv`)
- `compile-tables` -> uploads `compiled-tables` artifact (`output/table`)

Artifact retention is set to 30 days.

## A Level Marks Calculator UI

A standalone calculator page is available at `docs/calculator.html`.

It provides:

- Dynamic marks table (add/remove/edit rows)
- Live raw mark -> PUM conversion with validation feedback
- Threshold-based A Level grade calculation using `output/tables/*_all.csv`
- Auto-calculated status and summary metrics
- Synced marks charts (raw marks comparison + PUM trend)
