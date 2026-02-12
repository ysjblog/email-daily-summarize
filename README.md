# Daily Summarize

Multi-account Gmail automation (09:00 and 21:00 Asia/Taipei):
- Classify inbox messages and move low-priority emails in moderate mode.
- Scan Spam for potentially important emails (report-only).
- Build one combined digest with clear account sections.
- Send digest to Gmail + Slack + LINE.

## 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill all secrets in one `.env` file.

## 2. Configure

Edit:
- `config/settings.yaml`

Add new accounts by appending `accounts[]` entries with a new `env_prefix`.

## 3. Authorize Gmail account (interactive)

For each account, run:

```bash
python -m src.main auth login --account work --email your-work@gmail.com
python -m src.main auth login --account personal --email your-personal@gmail.com
```

This opens a browser and writes `${PREFIX}_GMAIL_REFRESH_TOKEN` into `.env`.

## 4. Run

```bash
python -m src.main dry-run
python -m src.main run
python -m src.main run --account work
python -m src.main backfill --days 7
```

## 5. Output

Reports:
- Combined: `data/reports/<run_id>.json`, `data/reports/<run_id>.md`
- Per account: `data/reports/<run_id>__<account_id>.json`, `data/reports/<run_id>__<account_id>.md`

State:
- `data/state/<account_id>.json`

## 6. Required Gmail OAuth scopes

- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/gmail.send`
