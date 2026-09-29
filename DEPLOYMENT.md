# 將 Steady 公開成網站

目前這個專案有網站端編輯器與伺服器儲存。最直接的部署方式是 **Render Web Service + persistent disk**。Render 會提供 `*.onrender.com` 網址及 HTTPS；若要用自己的網域，再設定 DNS。Render 的免費 Web Service 沒有持久磁碟，重啟或重新部署後會遺失編輯內容，因此這個檔案儲存版本需要付費 Web Service 與磁碟。

## 1. 上傳程式

在 GitHub 按 **New repository** 建立一個 repository（可選 Private），再用 **Add file → Upload files** 上傳這個資料夾的程式檔：`server.py`、`app.js`、`index.html`、`styles.css`、`diagrams.css`、`README.md`、`DEPLOYMENT.md` 和 `.gitignore`。不要上傳 `admin.json`、`content.json`、`__pycache__` 或任何密碼；`.gitignore` 已排除伺服器執行時產生的資料。若你在本機已編輯內容，先從網站編輯器匯出 JSON 備份。

## 2. 在 Render 建立服務

1. Render Dashboard → **New** → **Web Service**，連接剛才的 GitHub repository。
2. Language 選 **Python 3**；Build Command 填 `python -m py_compile server.py`；Start Command 填 `python server.py`。
3. 選可附加 persistent disk 的付費 Web Service。Render 會提供 `PORT`，程式會自動使用，不必手動設定。
4. 在 **Advanced** 加入 persistent disk，Mount path 填 `/opt/render/project/src/storage`。只有這個路徑內的檔案會在重新部署後保留。
5. 加入下列 Environment Variables：

   | Key | Value |
   | --- | --- |
   | `STEADY_HOST` | `0.0.0.0` |
   | `STEADY_HTTPS` | `1` |
   | `STEADY_DATA_DIR` | `/opt/render/project/src/storage` |
   | `STEADY_ADMIN_PASSWORD` | 自己建立的強密碼；只用於第一次啟動 |

6. Health Check Path 可填 `/api/status`，然後建立服務。部署完成後，Render 會顯示公開的 `https://...onrender.com` 網址。

`STEADY_HTTPS=1` **不會自己開啟 HTTPS**；它只讓登入 Cookie 僅透過 HTTPS 傳送。公開的 TLS 與 HTTP 轉 HTTPS 由 Render 處理。

## 3. 驗證與管理

1. 開啟公開網址，確認首頁與指南可讀。
2. 按 **Edit content**，用 `STEADY_ADMIN_PASSWORD` 登入。第一次啟動時，程式會把密碼轉成加鹽雜湊存入磁碟的 `admin.json`，不會把明文密碼存入網站資料。
3. 確認登入與編輯可用後，從 Render Environment 刪除 `STEADY_ADMIN_PASSWORD`；磁碟上的管理者帳密會保留。
4. 若本機已有內容備份，到 **Backup & restore** 匯入 JSON。新增或修改一筆指南，再用另一個瀏覽器確認更新公開可見。
5. 定期從編輯器匯出 JSON 備份。Render 磁碟也有快照，但額外備份有助於搬家或恢復誤編輯。

## 4. 自訂網域（可選）

在 Render 服務的 **Settings → Custom Domains** 加入自己的網域，依 Render 顯示的 DNS 記錄到網域註冊商設定，再回 Render 驗證。Render 會管理該網域的 TLS 憑證。沒有自己的網域時，先用 `onrender.com` 網址即可。

公開急救內容前，請當地急救專業人員審閱指南與緊急電話。預設號碼是臺灣的 119；若面向其他地區，先到 **Site settings** 更新。

參考官方文件：[Render Web Services](https://render.com/docs/web-services)、[Persistent Disks](https://render.com/docs/disks)、[Custom Domains](https://render.com/docs/custom-domains)。
