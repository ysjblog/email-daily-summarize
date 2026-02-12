# Daily Summarize

多帳號 Gmail 自動摘要工具（預設時區：Asia/Taipei）。

## 1) 目標使用情境
- 自動整理多帳號 Gmail：重要信件、電子報、已搬移、疑似垃圾
- 可在本機（macOS）用 launchd 排程
- 可用 GitHub Actions 雲端排程

## 2) 安裝需求
- macOS（本機排程功能）
- Python 3.11+
- Google OAuth 憑證（每個帳號一組 Refresh Token）

> **⚠️ 注意事項：**
> 在執行 `get-refresh-token.command` 之前，請**務必關閉**已在編輯器中打開的 `secrets.local.env` 檔案，或確保該檔案未被鎖定。認證成功後，Token 會自動寫入該檔案，若檔案被編輯器佔用覆寫，會導致 Token 清空。

## 3) 一鍵初始化（建議）
在 repo 根目錄執行：

```bash
./init-user-config.command
./init-secrets.command
```

說明：
- `init-user-config.command` 會建立 `config/settings.local.yaml`
- `init-secrets.command` 會建立 `config/secrets.local.env` 並自動 `chmod 600`

> **💡 如何在終端機切換目錄？**
> 1. 打開終端機（Terminal）。
> 2. 輸入 `cd `（注意後面有空白）。
> 3. 將這個專案資料夾直接**拖曳**到終端機視窗內。
> 4. 按下 Enter，就會進入專案目錄了。

## 4) Token 與必要參數如何取得

### 4.1 Gmail（必要）
每個帳號都需要：
- `{PREFIX}_GMAIL_CLIENT_ID`
- `{PREFIX}_GMAIL_CLIENT_SECRET`
- `{PREFIX}_GMAIL_REFRESH_TOKEN`

建議流程：
1. 到 Google Cloud Console 建立/選擇 Project。
2. 啟用 Gmail API。
3. 設定 OAuth consent screen（至少完成可測試狀態）。
4. 建立 OAuth Client（Application type 選 `Desktop app`）。
5. 將 Client ID / Client Secret 填入 `config/secrets.local.env`（填完記得關檔）。
6. 請依序執行（瀏覽器會跳出認證）：

```bash
./get-refresh-token.command work your-work@gmail.com
./get-refresh-token.command personal your-personal@gmail.com
```

### 4.2 LINE（選用）
當 `settings.yaml` 的 `digest.channels` 包含 `line` 時需要：
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_TARGET_USER_ID`

常見流程：
1. 在 LINE Developers 建立 Messaging API channel。
2. 取得 Channel access token。
3. 將 Bot 加為好友，從 webhook event payload 取得 userId（或以你既有方式取得）。
4. 寫入 `secrets.env`。

### 4.3 Slack（選用）
當 `settings.yaml` 的 `digest.channels` 包含 `slack_bot` 時需要：
- `SLACK_BOT_TOKEN`
- `digest.slack.channel_id`（在 `settings.yaml`）

常見流程：
1. 建立 Slack App。
2. 設定 Bot Token scopes（至少 `chat:write`）。
3. 安裝 App 到 workspace 取得 Bot token。
4. 填入 `secrets.env`，並在 `settings.yaml` 放入 channel id。

## 5) 快速驗證（Dry Run）

```bash
bash scripts/quickstart.sh
```

`quickstart.sh` 會：
- 建立 `.venv` 與安裝依賴
- 檢查 `config/settings.local.yaml` 與 `config/secrets.local.env` 是否存在
- 檢查 `config/secrets.local.env` 權限是否為 `600`
- 檢查必要 env key 是否齊全
- 執行 `dry-run`

## 6) 正式執行

請使用我們提供的腳本（會自動載入 Python 環境）：

```bash
bash scripts/run_daily_digest.sh
```

**手動執行方式**（需先啟動虛擬環境）：

```bash
# 1. 啟動虛擬環境
source .venv/bin/activate

# 2. 執行主程式（設定檔已預設指向 local config）
python -m src.main run
```

## 7) 常用指令（需先啟動虛擬環境）

> 💡 Dry-run 模式可以安全地預覽分類結果的報表通知，且**不會**實際搬移郵件。

```bash
source .venv/bin/activate

# 模擬執行（不移動信件、不發通知）
python -m src.main dry-run

# 模擬過去 24 小時
python -m src.main dry-run --hours 24

# 回溯過去 7 天的報表
python -m src.main backfill --days 7

# 開啟設定 UI
python -m src.main config-ui
```

## 8) 本機每日排程（macOS）

啟動：

```bash
bash scripts/local_schedule.sh start
```

停止：

```bash
bash scripts/local_schedule.sh stop
```

狀態：

```bash
bash scripts/local_schedule.sh status
```

立即手動跑一次：

```bash
bash scripts/local_schedule.sh run-now
```

也可直接雙擊：
- `start-local-schedule.command`
- `stop-local-schedule.command`
- `status-local-schedule.command`
- `open-config-ui.command`

## 9) GitHub Actions 排程
- `.github/workflows/daily-email-digest.yml`：正式排程 job
- `.github/workflows/ci.yml`：PR / push 時跑 unit tests

若要在 GitHub 上跑 `daily-email-digest.yml`，請在 Repository Secrets 設定：
- `WORK_GMAIL_CLIENT_ID`
- `WORK_GMAIL_CLIENT_SECRET`
- `WORK_GMAIL_REFRESH_TOKEN`
- `PERSONAL_GMAIL_CLIENT_ID`
- `PERSONAL_GMAIL_CLIENT_SECRET`
- `PERSONAL_GMAIL_REFRESH_TOKEN`
- （選用）`SLACK_BOT_TOKEN`
- （選用）`LINE_CHANNEL_ACCESS_TOKEN`
- （選用）`LINE_TARGET_USER_ID`

## 10) 安全建議
- 不要把真實 token 放進 repo。
- `config/secrets.local.env` 權限固定 `600`。
- 對外通知建議使用 `digest.redaction_mode: strict`。
- 詳細流程請看 `SECURITY.md`。

## 11) 輸出位置
- 報表：`data/reports/*.json`, `data/reports/*.md`
- 狀態：`data/state/*.json`
- 日誌：`logs/*.log`
