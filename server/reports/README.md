# ZeroS reports server

Receives ZeroS statistics and bug reports from phones and stores them in a
private Cloud Storage bucket. LEGAL.md (Privacy) tells users what it receives
and how long it keeps it; keep the two in step.

| Route | From | Stored as |
|---|---|---|
| `POST /v1/stats` | LineageParts, once a day while ZeroS statistics is on | `stats/<date>/<device hash>.json`, one per phone per day |
| `POST /v1/bugreports` | ZeroS tools, when the user taps Send to ZeroS | `bugreports/<date>/<ID>.zip` and `<ID>.json` (description, version, size, SHA-256) |
| `GET /v1/health` | checks (not `/healthz`, which Cloud Run reserves) | nothing |

Limits (main.py, `Limits`): bug reports up to 30 MiB, 3 an hour per address and
20 a day in total; statistics up to 4 KiB, 30 an hour per address and 5,000 a
day. The service runs on one instance at most, so the in-memory counters are
the whole service's. The bucket's lifecycle rules delete bug reports after 30
days and statistics after 395 days (13 months).

Standard library only (Python 3.9 or later locally, 3.13 in the image).

## Test on the Mac

    python3 -I test_main.py

## Deploy

Google Cloud project of the ROM projects, region us-central1 (free tier). The
bucket name is kept out of git, in ~/rom-keys/zeros-reports.env
(`ZEROS_REPORTS_BUCKET=...`).

- Service `zeros-reports`, address
  `https://zeros-reports-<project number>.us-central1.run.app` (in
  apps/ZeroSTools/res/values/config.xml and
  overlay/packages/apps/LineageParts/res/values/config.xml).
- Runs as `zeros-reports-run@`, which holds only Storage Object Creator on the
  bucket: it can add objects but not read, list or delete them.
- Built by Cloud Build as `zeros-reports-build@` (Cloud Run Builder on the
  project) from this folder's Dockerfile; .gcloudignore uploads only the
  Dockerfile and main.py.

Deploy or update (from this folder):

    . ~/rom-keys/zeros-reports.env
    P=$(gcloud config get-value project)
    gcloud run deploy zeros-reports --source . --region us-central1 \
      --service-account zeros-reports-run@$P.iam.gserviceaccount.com \
      --build-service-account projects/$P/serviceAccounts/zeros-reports-build@$P.iam.gserviceaccount.com \
      --no-invoker-iam-check --max-instances 1 --concurrency 4 \
      --cpu 1 --memory 512Mi --timeout 120 \
      --set-env-vars ZEROS_REPORTS_BUCKET=$ZEROS_REPORTS_BUCKET

Reading reports and statistics: ~/rom/bin/zeros-reports (Mac).
