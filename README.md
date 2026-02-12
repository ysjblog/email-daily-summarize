# Daily Summarize

多帳號 Gmail 自動摘要工具（預設時區：Asia/Taipei）。

## 快速開始（貼 token + 一個 command）

1. 建立個人 secrets 檔案（repo 外）

```bash
mkdir -p ~/.config/daily-summarize
cp config/secrets.example.env ~/.config/daily-summarize/secrets.env
chmod 600 ~/.config/daily-summarize/secrets.env
```

2. 編輯 `~/.config/daily-summarize/secrets.env`，填入你自己的 token

3. 一鍵檢查並執行 dry-run

```bash
bash scripts/quickstart.sh
```

`quickstart.sh` 會自動做以下動作：
- 建立 `.venv` 並安裝依賴
- 檢查 `~/.config/daily-summarize/secrets.env` 權限是否為 `600`
- 檢查必要 env key 是否完整
- 執行 `python -m src.main dry-run`

## 正式執行

```bash
python -m src.main run --env-file ~/.config/daily-summarize/secrets.env
```

## 本機每日自動排程（macOS）

先完成一次 quickstart（建立 `.venv` + 驗證 secrets）：

```bash
bash scripts/quickstart.sh
```

啟動排程（依 `config/settings.yaml` 的 `run_times`）：

```bash
bash scripts/local_schedule.sh start
```

停止排程：

```bash
bash scripts/local_schedule.sh stop
```

檢查狀態：

```bash
bash scripts/local_schedule.sh status
```

立即手動跑一次（不等排程）：

```bash
bash scripts/local_schedule.sh run-now
```

也可以直接雙擊 repo 根目錄：
- `start-local-schedule.command`
- `stop-local-schedule.command`
- `status-local-schedule.command`

預設時間為台灣時間 `12:00` 與 `20:00`（來自 `config/settings.yaml` 的 `run_times`）。

## 設定檔

主要設定在 `config/settings.yaml`。

重點：
- `digest.redaction_mode: strict`（預設）會讓 Slack/LINE 只收到安全摘要，不含主旨與內容。
- `accounts[]` 可設定多帳號，每個帳號需要對應的 `{PREFIX}_GMAIL_*` secrets。
- `move_mode` 可切換 `conservative / moderate / aggressive`，影響搬移敏感度。
- `scoring` 可調整 `keep_threshold / move_threshold / newsletter_threshold`，用來校準重要信件與電子報分流。

## Gmail OAuth 登入（互動式）

若你要透過互動流程取得 refresh token：

```bash
python -m src.main auth login --account work --email your-work@gmail.com
```

預設會寫入 `~/.config/daily-summarize/secrets.env`。

## 其他指令

```bash
python -m src.main dry-run --env-file ~/.config/daily-summarize/secrets.env
python -m src.main dry-run --hours 24 --env-file ~/.config/daily-summarize/secrets.env
python -m src.main run --hours 24 --env-file ~/.config/daily-summarize/secrets.env
python -m src.main backfill --days 7 --env-file ~/.config/daily-summarize/secrets.env
python -m src.main config-ui
```

## 一鍵開啟設定頁（可雙擊）

macOS 可直接雙擊 repo 根目錄的 `open-config-ui.command`，會自動：
- 啟動 `config-ui`（若尚未啟動）
- 打開 `http://127.0.0.1:8765`
- 你在頁面新增/移除白名單與黑名單（排除重要）後，會直接寫入 `config/settings.yaml`，下次 `dry-run/run` 立即生效。

## 輸出

- 報表：`data/reports/*.json`, `data/reports/*.md`
- 狀態：`data/state/*.json`
- 日誌：`logs/app.log`

## 安全建議

- 不要把真實 token 放進 repo。
- `secrets.env` 請固定 `chmod 600`。
- 詳細安全流程請看 `SECURITY.md`。
