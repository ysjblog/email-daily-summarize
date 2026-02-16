# Daily Summarize

多帳號 Gmail 自動摘要工具（預設時區：Asia/Taipei）。

## 1) 目標使用情境
- 自動整理多帳號 Gmail：重要信件、電子報、已搬移、疑似垃圾
- 可在本機（macOS）用 launchd 排程

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
1. 前往 **[Google Cloud Console](https://console.cloud.google.com/)**。
2. 建立新專案或選擇現有專案。
3.搜尋並啟用 **"Gmail API"**。
4. 設定 **OAuth consent screen**：
   - User Type 選 `External`。
   - 填寫 App name 與 Email（可隨意填）。
   - **Test users** 區域：**務必加入您要讀取的 Gmail 信箱地址**。
5. 建立 **Credentials**：
   - 點選 `Create Credentials` -> `OAuth client ID`。
   - Application type 選擇 **`Desktop app`**。
   - 下載或複製 `Client ID` 與 `Client Secret`。
6. 將這兩組字串填入 `config/secrets.local.env`（填完請儲存並關閉檔案）。
7. 執行以下指令取得 Refresh Token（瀏覽器會跳出認證視窗，請點選「繼續」與「允許」）：

```bash
./get-refresh-token.command work your-work@gmail.com
./get-refresh-token.command personal your-personal@gmail.com
```

> 💡 **重要提醒：防止授權 Token 每 7 天過期**
> 如果您的 Google Cloud 專案處於「測試 (Testing)」模式，Token 會在 7 天後失效導致排程中斷。
> 1. 返回 **[OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)** 頁面。
> 2. 點擊 **「發布應用程式 (Publish Application)」** 並確認。
> 3. **不需要**提交驗證（Submit for verification），直接發布即可避免 7 天過期限制。

### 4.2 LINE（必要）
當 `settings.yaml` 的 `digest.channels` 包含 `line` 時需要：
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_TARGET_USER_ID`

常見流程（參考官方文件：[Getting started with the Messaging API](https://developers.line.biz/en/docs/messaging-api/getting-started/)）：
1. 前往 **[LINE Developers Console](https://developers.line.biz/console/)** 並登入 LINE 帳號。
2. 建立一個 **Provider**（若已有可跳過）。
3. 建立 **Messaging API channel**：
   - 點選 "Create a new channel"。
   - 選擇 **Messaging API**。
   - 填寫必要資訊（App name, Description 等）。
4. 取得 **Channel Access Token**：
   - 進入該 Channel 的設定頁面，切換到 **Messaging API** 分頁。
   - 捲動到底部找到 `Channel access token`。
   - 點選 Issue 按鈕取得長效 Token（**請注意是 Token 不是 Secret**）。
5. 取得 **User ID**：
   - 在 **Basic settings** 分頁下方找到 `Your user ID`。
   - 或掃描 QR code 將 Bot 加為好友。
6. 將 Token 與 User ID 填入 `config/secrets.local.env`。




### 4.3 如何新增更多 Gmail 帳號
若您需要管理第三個（或更多）帳號，不需修改程式碼，僅需調整設定：

1. **修改 `config/settings.local.yaml`**：
   在 `accounts` 列表下新增一組設定（注意縮排）：
   ```yaml
   - id: project               # 自訂新帳號 ID
     display_name: Project Mail
     env_prefix: PROJECT       # 對應 secrets.env 的前綴 (全大寫)
     enabled: true
     overrides: {}
   ```

2. **設定 `config/secrets.local.env`**：
   新增對應的 Client ID 與 Secret。
   > 💡 **提示**：格式請參考上方 `work` 或 `personal` 的設定範例。
   
    請在檔案中加入：
    ```env
    PROJECT_GMAIL_CLIENT_ID=您的Client_ID
    PROJECT_GMAIL_CLIENT_SECRET=您的Client_Secret
    PROJECT_GMAIL_REFRESH_TOKEN=
    ```
    *(REFRESH_TOKEN 留空，**並請務必關閉檔案**，下一步會自動填入)*

3. **取得授權**：
   執行指令：
   ```bash
   ./get-refresh-token.command project your-project-email@gmail.com
   ```


4. **完成**：
   接續執行下方的「快速驗證」即可確認設定是否成功。

### 4.4 如何調整通知時間
您可以根據需求隨時更改每日摘要通知的時間：

1. **修改設定檔**：
   開啟 `config/settings.local.yaml`，找到 `run_times` 區塊並修改時間：
   ```yaml
   run_times:
     - '08:30'
     - '20:00'
   ```
   *（請使用 24 小時制格式，例如 `09:00` 或 `21:15`）*

2. **套用變更**：
   修改完儲存後，您必須重新啟動排程以套用新時間。您可以雙擊執行 `start-local-schedule.command` 或在終端機執行：
   ```bash
   bash scripts/local_schedule.sh start
   ```

3. **驗證**：
   執行 `bash scripts/local_schedule.sh status` 確認輸出資訊中的 `Times` 是否正確顯示新設定。

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



## 7) 本機每日排程（macOS）

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

## 8) 進階指令（需先啟動虛擬環境）

以下指令適合**除錯**或**補跑**資料時使用。

### 指令模式對照表

| 模式 | 對應指令 | **會實際寄送通知嗎？** | **會實際搬移信件嗎？** | 用途 |
| :--- | :--- | :--- | :--- | :--- |
| **正式執行 (Run)** | `scripts/run_daily_digest.sh`<br>或 `python -m src.main run` | **✅ 會寄送** | **✅ 會搬移** | 每日自動化運作使用。 |
| **模擬執行 (Dry-Run)** | `python -m src.main dry-run` | **✅ 會寄送** | **❌ 不會搬移** | 預覽報表格式、測試分類邏輯。 |
| **歷史回溯 (Backfill)** | `python -m src.main backfill` | **❌ 預設不寄送**<br>*(除非加 `--notify`)* | **❌ 不會搬移** | 補跑過去數據分析，不產生通知與搬移。 |

> 💡 Dry-run 模式可以安全地預覽分類結果的報表通知，且**不會**實際搬移郵件。

1. 進入虛擬環境：

```bash
source .venv/bin/activate
```

2. 模擬執行（不移動信件）：

```bash
python -m src.main dry-run
```

3. 模擬過去 24 小時（常用於除錯）：

```bash
python -m src.main dry-run --hours 24
```

4. 回溯過去 7 天的報表：

```bash
python -m src.main backfill --days 7
```

5. 開啟設定 UI（也可直接雙擊 open-config-ui.command）：

```bash
python -m src.main config-ui
```

## 9) 安全建議
- 不要把真實 token 放進 repo。
- `config/secrets.local.env` 權限固定 `600`。
- 對外通知建議使用 `digest.redaction_mode: strict`。
- 詳細流程請看 `SECURITY.md`。

## 10) 輸出位置
- 報表：`data/reports/*.json`, `data/reports/*.md`
- 狀態：`data/state/*.json`
- 日誌：`logs/*.log`
