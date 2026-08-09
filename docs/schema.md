# Schema 設計

範圍：MVP 先涵蓋 Books 9-12（漂流歷險記），後續擴充 Book 5（離開卡呂普索島、船難抵達費阿基亞）與 Books 21-24（張弓比武、屠殺求婚者、返鄉團圓，壓縮成地圖上的一個收尾地點）。四個 collection：`characters`、`locations`、`events`、`relationships`。

## 共通設計原則

- **雙語欄位**：所有面向使用者的文字欄位用 `{ en, zh }` 結構。`en` 是從 Samuel Butler 1900 譯本（Project Gutenberg #1727，公版）抽取的權威內容；`zh` 是 LLM 生成的翻譯/摘要，UI 上需標示為 AI 翻譯。
- **來源追溯（provenance）**：每筆文件記錄 `source` 欄位，標明資料是 `wikidata`（人物基本關係）還是 `llm_extracted`（劇情事件/地點，從原文抽取），供 demo 展示資料可信度時引用。
- **Embedding**：每個 collection 都有 `embedding_source`（純字串，英文原文，實際餵給 Atlas Automated Embedding 的欄位）與 `embedding`（Atlas 自動寫入的向量欄位，不手動填）。
  - **待確認**：`embedding_source` 是否可以省略、直接讓 Automated Embedding 指向 `description.en`（巢狀路徑）。等實際建 index 時測試；若不支援才保留 `embedding_source` 這個扁平欄位。
- **Graph 遍歷**：關係一律存在獨立的 `relationships` collection（邊集合），不內嵌在節點文件裡，方便 `$graphLookup` 跨 characters/locations/events 三種節點類型遞迴查詢。

---

## `characters`

人物與神祇。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `_id` | ObjectId | |
| `slug` | string | **唯一鍵**，固定不變的人物識別碼（例：`odysseus`、`poseidon`、`polyphemus`）。Wikidata 腳本與 LLM 抽取腳本都以此欄位 upsert，避免同一人物被建立成多筆文件 |
| `name` | `{ en, zh }` | 例：`{ en: "Odysseus", zh: "奧德修斯" }` |
| `aliases` | `[string]` | 選填，別名（例：`"Ulysses"`） |
| `type` | string enum | `mortal` \| `god` \| `monster` \| `creature` |
| `description` | `{ en, zh }` | 人物簡介 |
| `embedding_source` | string | 待確認是否需要（見上）|
| `embedding` | vector | Atlas 自動寫入 |
| `wikidata_id` | string | 選填，來源為 Wikidata 時記錄對應 QID |
| `source` | `[string]` | 資料來源清單（可能兩者皆有，例：`["wikidata", "llm_extracted"]`）|

**人物合併策略**：匯入前先定義 Books 9-12 權威人物清單（`slug` 固定），Wikidata 腳本先跑 upsert 建立/補齊 `wikidata_id`、家族關係；LLM 抽取腳本比對同一份 `slug` 清單，upsert 補齊敘事相關欄位（`description`、`type` 等），兩邊的 `relationships` 都指向同一個 `_id`，不建立重複文件。

## `locations`

奧德賽航行途經的地點。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `_id` | ObjectId | |
| `name` | `{ en, zh }` | 例：`{ en: "Land of the Cyclopes", zh: "獨眼巨人之地" }` |
| `description` | `{ en, zh }` | |
| `embedding_source` | string | |
| `embedding` | vector | |
| `order` | int | 時間線順序（1, 2, 3...），用於地圖迷霧解鎖順序、也用於新手模式的防雷過濾 |
| `book_chapter` | string | 例：`"Book 9"` |
| `coordinates` | `{ x, y }` | 虛構地圖座標（非真實地理），前端畫地圖用 |
| `image` | string \| null | 該地點對應劇情的公版藝術作品，相對路徑（相對於 `app/assets/`），例：`"locations/03-cyclops.png"`。來源見 `image_credit`，非 LLM 抽取內容，於 `scripts/import_to_mongodb.py` 的 `LOCATION_IMAGES` 對照表按 `order` 掛入 |
| `image_credit` | string \| null | 圖片來源標註（藝術家、作品名、年代、館藏），解鎖卡片顯示圖片時一併附上 |
| `on_map` | bool | 是否出現在冒險地圖（`app/map_data.py` 的 `fetch_locations()` 以此欄位過濾）。Books 9-12 跟 Books 21-24 的收尾地點是 `true`；Book 5（卡呂普索島）是 `false`——地圖只收錄連續航線，Book 5 只是過場橋段，不是獨立一站，但仍是真實 MongoDB 資料，知識圖譜/AI問答/對照展示照常查得到 |
| `source` | string enum | `llm_extracted` \| `manual` |

## `events`

發生在特定地點的劇情事件。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `_id` | ObjectId | |
| `name` | `{ en, zh }` | 例：`{ en: "Blinding of Polyphemus", zh: "刺瞎波呂斐摩斯" }` |
| `description` | `{ en, zh }` | |
| `embedding_source` | string | |
| `embedding` | vector | |
| `location_id` | ObjectId → `locations._id` | 事件發生地點 |
| `order` | int | 時間線順序，繼承或細分自 location 的 order，供防雷過濾使用 |
| `book_chapter` | string | |
| `source_excerpt` | string | 英文原文引用片段，供 Graph RAG 答案佐證/可信度展示 |
| `source` | string enum | `llm_extracted` \| `manual` |

## `relationships`

人物/地點/事件之間的關係邊，供 `$graphLookup` 遞迴查詢。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `_id` | ObjectId | |
| `from_id` | ObjectId | 起點節點 `_id`（可能來自任一節點 collection）|
| `from_type` | string enum | `character` \| `location` \| `event` |
| `from_name` | `{ en, zh }` | **快取欄位**，起點節點的名稱快照，避免畫關係圖時要再回頭查三個節點 collection 才能顯示標籤 |
| `to_id` | ObjectId | 終點節點 `_id` |
| `to_type` | string enum | `character` \| `location` \| `event` |
| `to_name` | `{ en, zh }` | **快取欄位**，終點節點的名稱快照 |
| `relation` | string | 關係標籤，例：`MARRIED_TO`、`FATHER_OF`、`CHILD_OF`、`ANTAGONIST_OF`、`BLINDS`、`CURSES`、`LOCATED_AT`、`PARTICIPATES_IN`、`CAUSES` |
| `description` | `{ en, zh }` | 選填，關係的補充說明 |
| `order` | int | 選填，繼承相關 event/location 的時間線順序，供防雷過濾 |
| `source` | string enum | `wikidata` \| `llm_extracted` |

**`LOCATED_AT` 說明**：跟 `PARTICIPATES_IN` 一樣，`LOCATED_AT`（事件→地點）不是由 LLM 抽取產生，而是匯入時從 `events.location_id` **程式自動生成**成正式的關係邊（避免 LLM 產生不一致的資料）。早期曾經考慮「`location_id` 欄位已經有這個資訊，不用再存成邊」而省略這條邊，但這樣會讓 `$graphLookup` 沒辦法穿過地點做圖遍歷（例如「跟某事件同地點還發生過什麼」這類查詢會斷掉），幾十筆邊的重複儲存成本可忽略，決定還是要存成正式邊。

**Extended Reference 說明**：`from_name`/`to_name` 是 MongoDB schema design 的 Extended Reference pattern——人物/地點/事件名稱在這個 demo 範圍內幾乎不會變動，適合在寫入關係邊時直接快取一份，畫知識圖譜時單一 collection 查詢就能拿到完整可讀標籤，不用每條邊都回頭 `$lookup` 三個節點 collection。若之後真的要修正某個節點名稱，需同步 `updateMany` 更新所有引用它的 `relationships` 邊（此規模資料量小，成本可忽略）。

**`$graphLookup` 範例**（找出 Odysseus 的所有間接關係，最多 3 跳）：

```javascript
db.characters.aggregate([
  { $match: { "name.en": "Odysseus" } },
  {
    $graphLookup: {
      from: "relationships",
      startWith: "$_id",
      connectFromField: "to_id",
      connectToField: "from_id",
      as: "connections",
      maxDepth: 3,
      depthField: "depth"
    }
  }
])
```

---

## Index（已建立，見 `scripts/create_vector_indexes.py`）

- `characters` / `locations` / `events`：各一個 Vector Search index（`characters_vector_index`／`locations_vector_index`／`events_vector_index`），`type: "autoEmbed"` 指向 `embedding_source`，模型 `voyage-4`。**注意**：Automated Embedding 產生的向量不會寫回文件的 `embedding` 欄位，存在 Atlas search index 基礎設施裡，`find()` 查不到是正常現象
  - `locations` / `events` 的 index 額外加了 `type: "filter"` 的 `order` 欄位，供新手模式防雷查詢直接在 index 層 pre-filter
- `relationships`：`from_id`、`to_id` 一般 index，加速 `$graphLookup` 查詢
- `locations` / `events`：`order` 一般 index，供防雷過濾（`order <= 目前解鎖進度`）排序/篩選用

## 待辦

- [x] ~~確認 Automated Embedding 是否支援直接指向 `description.en`~~ — 保留 `embedding_source` 扁平欄位，未測試巢狀路徑
- [x] Wikidata SPARQL 查詢腳本（`scripts/fetch_wikidata.py`）：已抓取並人工核對家族關係，存於 `data/relationships_wikidata.json`（24 條邊）；尚未寫入 MongoDB，待 `MONGODB_URI` 設定後執行匯入
- [ ] LLM 抽取腳本：讀 Butler 譯本 Books 9-12，產出 `locations` + `events` + `relationships`（`source: "llm_extracted"`），並生成中文欄位
