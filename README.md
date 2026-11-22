# 莫名起妙不要問我要吃啥｜今天吃什麼 API

這是一個使用 FastAPI、SQLModel 與 SQLite 製作的餐廳管理及隨機推薦平台。網站名稱為「莫名起妙不要問我要吃啥」，所有餐廳資料都會實際寫入 `food.db`，不使用記憶體 list 保存資料。

## 專案結構

```text
03/
├── main.py
├── requirements.txt
├── README.md
├── prompt.md
└── food.db             # 第一次啟動應用程式時自動建立
```

## 安裝

建議使用 Python 3.10 以上版本。在 PowerShell 依序執行：

```powershell
cd D:\fastAPI\03
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果 PowerShell 阻擋啟用虛擬環境，可在目前的終端機暫時執行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 啟動

在 `D:\fastAPI\03` 目錄執行：

```powershell
python -m uvicorn main:app --reload
```

啟動後可使用：

- 餐廳平台首頁：<http://127.0.0.1:8000>
- Swagger UI：<http://127.0.0.1:8000/docs>
- ReDoc：<http://127.0.0.1:8000/redoc>

應用程式啟動時會在 `main.py` 同一目錄自動建立 `food.db` 與 `restaurants` 資料表。

## 網站介面

開啟首頁後可直接使用圖形化介面：

- 查看餐廳數量、營業中數量與美食分類統計
- 依名稱、食物類型及營業狀態篩選餐廳
- 新增、編輯與移除餐廳
- 依食物類型及最高價位隨機推薦一家營業中的餐廳
- 支援桌面、平板及手機版面

首頁會直接呼叫下方 API，所有異動仍會實際寫入 SQLite `food.db`。

## 資料表欄位

資料表名稱：`restaurants`

| 欄位 | SQLite / Python 型別 | 規則 | 說明 |
|---|---|---|---|
| `id` | INTEGER / int | 主鍵、自動編號 | 餐廳唯一識別碼 |
| `name` | VARCHAR / str | 必填、不可為空白、最長 100 字元 | 餐廳名稱 |
| `category` | VARCHAR / str | 必填、不可為空白、最長 50 字元 | 食物類型 |
| `price_level` | INTEGER / int | 必填，1～3 | 價位等級 |
| `is_open` | BOOLEAN / bool | 預設 `true` | 是否營業中 |

## API 路由表

| 方法 | 路由 | 功能 | 查詢參數 / 備註 | 成功狀態碼 |
|---|---|---|---|---|
| POST | `/restaurants` | 新增餐廳 | JSON request body | 201 |
| GET | `/restaurants` | 取得餐廳清單 | 可選 `category`、`is_open` | 200 |
| GET | `/restaurants/{id}` | 取得單一餐廳 | 找不到回傳 404 | 200 |
| PATCH | `/restaurants/{id}` | 部分更新餐廳 | 只需傳要修改的欄位；找不到回傳 404 | 200 |
| DELETE | `/restaurants/{id}` | 刪除餐廳 | 找不到回傳 404 | 204 |
| GET | `/recommend` | 隨機推薦營業中的餐廳 | 可選 `category`、`max_price_level`（1～3）；無結果回傳 404 | 200 |

### 新增資料範例

```json
{
  "name": "巷口牛肉麵",
  "category": "中式",
  "price_level": 2,
  "is_open": true
}
```

### 部分更新範例

```json
{
  "price_level": 3,
  "is_open": false
}
```

## 測試步驟

1. 依照上方指令安裝套件並啟動伺服器。
2. 開啟 <http://127.0.0.1:8000/docs>。
3. 展開 `POST /restaurants`，按 **Try it out**，加入至少兩筆不同分類、價位或營業狀態的餐廳；確認回傳 201 且有自動產生的 `id`。
4. 展開 `GET /restaurants`，先不帶參數查詢，再用 `category` 與 `is_open` 篩選；確認結果正確。
5. 使用其中一筆 `id` 測試 `GET /restaurants/{id}`；再以不存在的 id 測試，確認回傳 404。
6. 使用 `PATCH /restaurants/{id}` 修改一個或數個欄位，接著重新 GET，確認資料已寫入資料庫。
7. 測試 `GET /recommend`，分別使用 `category` 與 `max_price_level`；確認只會推薦營業中且符合條件的餐廳。使用不存在的分類，確認回傳 404。
8. 使用 `DELETE /restaurants/{id}` 刪除資料，確認回傳 204；再次查詢該 id，確認回傳 404。
9. 停止並重新啟動伺服器，再呼叫 `GET /restaurants`，確認未刪除的資料仍存在，證明資料儲存在 SQLite，而不是記憶體中。

## `/docs` 測試紀錄

以下為 2026-11-21 實際測試紀錄；測試資料已於測試完成後清除：

| 測試日期 | 路由 | 測試內容 | 預期狀態碼 | 實際結果 | 通過 |
|---|---|---|---:|---|:---:|
| 2026-11-21 | `POST /restaurants` | 新增合法餐廳與錯誤資料驗證 | 201 / 422 | 符合預期 | ☑ |
| 2026-11-21 | `GET /restaurants` | 清單及 `category`、`is_open` 條件篩選 | 200 | 符合預期 | ☑ |
| 2026-11-21 | `GET /restaurants/{id}` | 存在 / 不存在 id | 200 / 404 | 符合預期 | ☑ |
| 2026-11-21 | `PATCH /restaurants/{id}` | 部分更新及資料驗證 | 200 / 422 / 404 | 符合預期 | ☑ |
| 2026-11-21 | `DELETE /restaurants/{id}` | 刪除及重複刪除 | 204 / 404 | 符合預期 | ☑ |
| 2026-11-21 | `GET /recommend` | 符合 / 無符合條件 | 200 / 404 / 422 | 符合預期 | ☑ |
| 2026-11-21 | `/`、`/docs` | 平台首頁與 Swagger UI | 200 | 符合預期 | ☑ |

## 資料驗證

- `name` 與 `category` 不接受空字串或只有空白的字串。
- `price_level` 與 `max_price_level` 只接受 1 到 3。
- `is_open` 接受布林值，新增時未提供則預設為 `true`。
- PATCH 只更新有傳入的欄位，不接受把欄位更新為 `null`。
- request 不符合規則時，FastAPI 會回傳 422 與詳細驗證訊息。
