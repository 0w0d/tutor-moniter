# 1111家教網 新案件監控 → Discord 通知

每 5 分鐘自動檢查一次指定的搜尋結果頁，一旦出現新案件就推播到你的 Discord 頻道。完全免費，跑在 GitHub Actions 上，不需要自己的伺服器。

## 設定步驟

### 1. 建立 Discord Webhook
1. 在 Discord 裡開啟你想接收通知的伺服器 → 選一個頻道 → 點頻道設定（齒輪圖示）
2. 左側選「整合」（Integrations）→「Webhook」→「新增 Webhook」
3. 幫它取個名字（例如「家教案件通知」），複製「Webhook URL」（長得像 `https://discord.com/api/webhooks/xxxx/yyyy`）
   - 沒有伺服器也沒關係：右上角「+」新增一個只有自己的伺服器即可

### 2. 建立 GitHub Repository 並上傳這些檔案
1. 到 [github.com/new](https://github.com/new) 建立一個新的 repo（設為 Private 即可，內容不需要公開）
2. 把這次下載到的檔案（`monitor.py`、`requirements.txt`、`.github/workflows/monitor.yml`）上傳上去，保持原本的資料夾結構

### 3. 設定 Secrets
到 repo 頁面 → Settings → Secrets and variables → Actions → New repository secret，新增兩組：

| Name | Value |
|---|---|
| `SEARCH_URL` | 你要監控的搜尋結果網址，例如：`https://tutor.1111.com.tw/case/caseSearch.asp?newSearch=search&Item1=2&sCity0=100501,100502` |
| `DISCORD_WEBHOOK_URL` | 步驟 1 複製的 Webhook 網址 |

### 4. 手動測試一次
到 repo 的「Actions」分頁 → 選「1111家教網新案件監控」→ 右邊「Run workflow」手動觸發一次。

- **第一次執行**不會推播任何訊息，只會把目前所有案件記錄成「已讀」基準名單（避免你一次收到 56 則舊案件轟炸）
- 之後每次執行，只要出現新案件編號，就會推播到 Discord

之後 GitHub Actions 會照 `.github/workflows/monitor.yml` 裡設定的排程（每 5 分鐘）自動執行，不用再手動做任何事。

## 常見問題

**多久算「即時」？**
排程設定是 5 分鐘，但 GitHub 的免費排程有時會延遲數分鐘才觸發，實際上大約是 5~15 分鐘內會收到通知。如果想抓更緊，可以把 `monitor.yml` 裡的 `cron: "*/5 * * * *"` 改成更短間隔，但 GitHub 對免費帳號的排程最小間隔實務上建議不要低於 5 分鐘。

**想同時監控多個地區/科目條件？**
複製整個 repo 或整組 workflow + secrets，把 `SEARCH_URL` 換成不同的篩選條件即可分開監控、分開通知。

**網站改版導致抓不到資料怎麼辦？**
`monitor.py` 裡用正則表達式解析頁面文字，如果 1111 家教網改版，解析規則可能需要更新。腳本會在解析不到任何案件時印出警告、不覆蓋已讀名單，不會誤發或漏發通知。

**要換成 Email 通知呢？**
把 `monitor.py` 裡的 `send_discord()` 換成寄信邏輯（例如用 Gmail SMTP + App Password）即可，架構不用改。
