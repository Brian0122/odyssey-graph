# Odyssey-Graph

## 專案目標
奧德賽（The Odyssey）知識圖譜 demo，對外展示用。目的是展示 MongoDB Atlas 同時做 Graph 遍歷（`$graphLookup`）與原生 Vector Search 的 Graph RAG 能力，並包裝成互動式冒險地圖體驗。

**核心定位**：這是推廣 Atlas 用的 demo，不是純技術評測。功能分兩層：
- **核心賣點**（技術上站得住腳，時間有限時優先做）：Automated Embedding + Vector Search + `$graphLookup` 三合一、Graph RAG vs 向量 RAG 對照展示、inline citation 可解釋性
- **體驗鉤子**（讓人願意停留/記住，但本身不證明 Atlas 能力，時間有限可以犧牲）：迷霧地圖、多視角敘事
- **技術歸屬要隨行**：地圖、知識圖譜等好玩的畫面上要有明顯標示（例如「Powered by Atlas `$graphLookup`」小徽章），避免觀眾只記得「好玩的小遊戲」卻不知道背後是 MongoDB Atlas
- Split-screen 對照展示是說服力最強的環節，正式 demo/簡報時應優先帶到（UI 結構已調整為第 3 個 tab，緊接在知識圖譜之後、AI 問答之前，就是為了呼應這個優先順序）

## 功能需求
- 知識圖譜關係網絡視圖（人物/神祇/地點/事件關係）
- Graph RAG vs 一般向量 RAG 對照展示（split-screen，同一問題兩套 pipeline 並列比較）
  - 範例問題，兩種類型，都在 `app/example_questions.py`（`app/views/qa.py`、`compare.py` 共用同一份，不會兩邊各自維護、不同步）：
    - **點對點間接關係**（刻意選文本中不會同段落出現的關係，凸顯純向量 RAG 答不出來、Graph RAG 靠 `$graphLookup` 才能答對）：
      - 「Telemachus 跟 Poseidon 有什麼關係？」（需經 `Telemachus →(父子)→ Odysseus →(仇敵)→ Poseidon` 兩跳，已用 `app/rag.py` 驗證可正確重建路徑）
      - 「刺瞎波呂斐摩斯的人，跟波塞頓有什麼關係？」（需經 `Odysseus →(刺瞎)→ Polyphemus →(父子)→ Poseidon` 兩跳，已驗證可正確重建路徑；原本規劃的「Odysseus 的盟友的敵人有誰」因為資料裡沒有 `ALLY_OF` 這類關係，答不出來，換成這題）
      - 「宙斯跟波呂斐摩斯是什麼關係？」（`Zeus →(手足)→ Poseidon →(父子)→ Polyphemus`，答案是「伯姪」）
      - 「萊爾特斯跟特勒馬科斯有什麼關係？」（`Laertes →(父子)→ Odysseus →(父子)→ Telemachus` 兩跳，答案是「祖孫」；Book 5/Books 21-24 資料擴充後新增，兩條 pipeline 都實測過才收進清單——純向量能各自搜到 Laertes、Telemachus，但誠實答不出兩人的關係）
    - **列舉/窮盡型**（跟點對點關係是不同的失敗模式）：
      - 「波塞頓總共有哪些子女？」——向量搜尋沒辦法保證找齊全部符合的邊，只會回傳「語意相近」的東西；`$graphLookup` 從節點展開是決定性的，一定找齊。實測這題向量版甚至沒把波塞頓本人搜尋進命中結果，比點對點關係題的落差更明顯
    - **共同祖先推論型**：
      - 「斯庫拉跟卡律布狄斯是什麼關係？」——資料庫裡兩人之間**沒有直接的邊**（沒有 `SIBLING_OF`），只各自有一條 `CHILD_OF` 指向同一個父親波塞頓。要答對必須先發現兩人共用父親，再推論出「手足」關係，比單純讀一條邊多一層推理。實測向量版連卡律布狄斯這個名字都沒搜到
    - **試過但拿掉的類型：事件因果鏈**（`CAUSES`，例如「是誰造成了宙斯的風暴」）——加進去之前只測了 Graph 版本能答對，沒測向量版；後來使用者發現兩邊都答得出來，補測才發現問題：事件的描述文字是 LLM 從原文抽取時寫成的敘事摘要，常常會**自己把因果寫進散文裡**（例如「宙斯的暴風雨」的描述已經寫「宙斯為了懲罰他們殺死牛群而摧毀了船隻」），不需要真的走 `CAUSES` 這條邊，單一片段就夠回答。這跟人物親屬關係不一樣——親屬是結構化事實，通常不會被順便寫進某一則描述的散文裡。**教訓**：新增旗艦問題一定要兩條 pipeline 都實測過（不能只測預期會成功的那一側），才能確認真的有展示出差異，不能憑「這題感覺應該答不出來」的直覺就收進清單
  - 左側呈現：向量 RAG 抓到的文字片段 + 答案（誠實作答，片段不夠就承認答不出來，不瞎猜）；右側呈現：Graph RAG 展開的關係路徑（`graph_data.py` 的 `filter_relevant_relationships()` 過濾到只剩答案真的有用到的邊）+ 子圖視覺化（streamlit-agraph）+ 答案
  - 頁面一進來就顯示左右分欄的標題/架構（不用等選了問題才出現），讓使用者馬上懂這頁在比較什麼
- 冒險地圖：依時間線順序排列地點、迷霧效果、點擊已解鎖地點才能前進到下一站
  - 需提供「解鎖全部」入口（例如地圖角落的按鈕），一鍵顯示全部地點與內容，方便 demo 展示時跳過逐步解鎖流程
- 新手模式（防雷：查詢範圍限制在目前已解鎖進度以前的劇情）vs 專家模式（自由查詢全圖譜，不設限）
- 關係路徑解釋器：點選兩個人物節點，AI 用圖遍歷解釋間接關係，並在圖上高亮路徑
- 地點導覽卡、角色初登場卡：解鎖新地點/新角色時 AI 自動生成介紹
- **答案可解釋性（inline citation）**：所有 Graph RAG 回答都要附上依據——引用的關係路徑（例：`Telemachus →(父子)→ Odysseus →(仇敵)→ Poseidon`）+ 對應的 `events.source_excerpt` 原文引用，讓答案「有憑有據」而非黑箱生成
- **多視角敘事**：抓某個角色連結的 events/relationships，讓 AI 用該角色第一人稱視角重述事件（例：「從 Poseidon 的角度描述這件事」），與關係路徑解釋器共用底層邏輯

## UI 結構（Tab 規劃）
新手/專家模式是側邊欄的全域切換，不是獨立 tab，會影響「冒險地圖」與「AI 問答」兩個 tab 的查詢範圍。

1. **冒險地圖**（主體/門面）
   - 迷霧 + 點擊解鎖、時間線推進
   - 地點導覽卡、角色初登場卡（自動生成介紹）
   - 多視角敘事（地點內選「用某角色視角看這件事」）
   - 「解鎖全部」按鈕
2. **知識圖譜**（自由探索關係網絡）
   - 完整人物/地點/事件關係圖視覺化（force-directed layout）
   - 關係路徑解釋器：點兩個節點，AI 解釋間接關係並高亮路徑
   - 通常對應專家模式，不受劇情進度限制
3. **Graph RAG 對照展示**（demo 用）
   - Split-screen：同一問題，左邊純向量 RAG、右邊 Graph RAG（含子圖視覺化）
   - 內建範例問題集（見「功能需求」的範例問題）
4. **AI 問答**（自然語言查詢）
   - Text-to-MQL 對話框，`$graphLookup` + Vector Search 混合查詢
   - 答案附 inline citation（關係路徑 + 原文引用）

## 視覺主題
- 古希臘史詩冒險風格：暗色系、Cinzel（羅馬碑文風格字體）+ EB Garamond、希臘迴紋（meander）裝飾線
- 背景圖是真實照片而非純 CSS/SVG 生成——公版的 1903 年古希臘地圖（Wikimedia Commons, "Map of Ancient Greece (as drawn in 1903)"，public domain），用 PIL 處理成暗金棕色調 + 模糊，當氛圍紋理不搶文字（處理腳本：`scripts/process_map_background.py`，原圖跟處理結果存在 `app/assets/`）
- 節點顏色維持 dataviz skill 驗證過的無障礙配色（暗色模式版本），不因主題調整而犧牲可讀性
- **設計教訓**：不要疊加發光文字、灑星星點、雙線框這類「看起來厲害」的裝飾特效，會顯得廉價業餘；用真正具體的文化符號（希臘迴紋、真實地圖紋理）+ 克制的留白排版，比堆砌通用奇幻裝飾更有說服力
- **視覺方向定案**：曾考慮過改走中古世紀騎士/城堡風格，決定不改——《奧德賽》是西元前的古希臘故事，比中世紀早了近兩千年，現有的 Cinzel／希臘迴紋／真實古希臘地圖都是針對這個時代刻意選的，換成哥德字體/羊皮紙卷軸邊框/盾徽會跟故事背景時代不符，也違背上面「拒絕通用奇幻裝飾」的原則
- **原生元件主題化**（`app/theme.py`）：`st.button`／`st.selectbox`／`st.expander`／`st.chat_input`／`st.divider()` 預設是 Streamlit 中性灰色樣式，不受 `.streamlit/config.toml` 的 `primaryColor` 影響（那個只餵給 BaseWeb 的 checkbox/radio 打勾顏色，不影響這幾個元件的邊框/背景）——補上金色邊框 + 羊皮紙文字色，讓這些高頻使用的元件（範例問題按鈕、AI 問答輸入框、聚焦下拉選單）跟整體質感一致
  - CSS 選擇器是直接 grep 實際裝好的 `streamlit==1.61.1` 前端 JS bundle 確認的 `data-testid`（`stBaseButton-${kind}`、`stChatInput`、`stExpanderDetails`），不是憑訓練記憶——這層 DOM 結構跨版本會變。Selectbox 內部沒有穩定的 class name，改用 `[role="combobox"]`（WAI-ARIA 語意屬性，比猜測 BaseWeb 內部 div 巢狀結構穩定）
  - `st.divider()` 沒有專屬 testid（就是一個純 `<hr>`），直接用 `hr` 選擇器套金色細線

## 技術架構
- 資料來源（混合）：
  - 人物基本關係（父母/配偶/子女等家族關係）：Wikidata SPARQL 查詢（CC0 公版，不用 LLM 重新辨識）
  - 劇情事件、地點、事件相關的關係：LLM 從 Samuel Butler 1900 年英文散文譯本（Project Gutenberg #1727，公版）原文抽取，中文譯本多有版權問題不採用
- **人物合併策略**：Wikidata 跟 LLM 抽取是兩條獨立 pipeline，都可能產生同一個人物（例如 Odysseus、Poseidon），須避免 `characters` collection 出現重複記錄
  - 先建一份 Books 9-12 涉及人物的**權威人物清單**（固定 `slug`，例如 `odysseus`、`poseidon`、`polyphemus`），寫進 `docs/schema.md` 的 `characters.slug` 欄位
  - Wikidata 腳本、LLM 抽取腳本都以 `slug` 做 upsert（`update_one({slug}, upsert=True)`），關係一律掛在同一個 `_id` 底下，不各自建立新文件
- 資料庫：MongoDB Atlas
  - `$graphLookup` 做關係遞迴展開
  - Atlas 原生 Vector Search，**寫入/查詢混合架構**：
    - **寫入**：`characters`/`locations`/`events` 用 Atlas Automated Embedding（`type: "autoEmbed"`）——文件寫入時 Atlas 自動呼叫 Voyage AI 把 `embedding_source` 轉成向量存進 index，應用程式完全不用管向量
    - **查詢**：`app/rag.py` 自己呼叫 Voyage AI 算一次查詢向量，三個 collection 共用同一個向量做 `$vectorSearch`（`queryVector`），不再用會觸發 Atlas 自動 embed 的 `query` 文字參數
    - **取捨原因**：原本規劃查詢也全部交給 Automated Embedding（`query` 文字參數），但 `graph_rag_retrieve()` 每題要對三個 collection 各查一次，同一句話被 Atlas 重複 embed 三次，demo 測試時很快撞到 Voyage 的 RPM 限制。自己算一次、三個 collection 共用，同樣的資訊、Voyage 請求量降 2/3——**不是要繞開 rate limit**（自行呼叫用的很可能是同一把 key、共用同一組額度，繞不開），純粹是減少重複請求量。寫入端維持全自動是因為寫入頻率低（demo 資料量小、不常變動），沒有同樣的重複呼叫問題，沒必要放棄 Automated Embedding 的省心
    - 細節記錄在「目前進度」AI Agent 項目底下（index 實際維度/量化參數、int8 向量格式等）
  - 刻意不用 Neo4j 等專用圖資料庫——「單一資料庫同時做 vector + graph」正是這個 demo 要展示的重點，此規模（幾十~上百節點）`$graphLookup` 效能完全足夠
- AI Agent：Gemini API（`google-genai` SDK，function calling），不用 LangChain——原本規劃用 Anthropic SDK，因為當下沒有 Anthropic API key、且使用者已有 Gemini 額度，決定整個查詢 agent 也改用 Gemini（見下方「LLM 供應商使用範圍」）
- 前端：MVP 先用 Streamlit 主體 + 嵌入自訂 HTML/JS component 處理視覺化
  - 知識圖譜關係視圖：可用 streamlit-agraph 或自訂 Cytoscape.js/D3
  - 冒險地圖（迷霧、漸進解鎖）：Streamlit 原生元件做不到，需自訂 HTML/JS（Canvas 或 SVG）嵌入，用 `streamlit.components.v1.declare_component` 做雙向溝通
  - 決策依據：MVP 階段互動需求（點節點前進、hover 提示、路徑高亮、解鎖全部）Streamlit + 自訂 component 做得到，且能維持單一 Python 技術棧、不用額外拆後端 API；若之後對外展示覺得不夠精緻（動畫生硬、rerun 閃爍），再把地圖那頁抽換成 React
  - **為了讓未來抽換成 React 方便**，架構上要做到：
    - 業務邏輯（MongoDB 查詢、Graph RAG 邏輯、AI Agent 呼叫）寫成獨立的 Python 函式/模組，不要直接寫在 Streamlit UI callback 裡，未來包一層 FastAPI 就能重用
    - 自訂 component 的資料介面（傳給前端視覺化的 nodes/edges/地圖狀態 JSON 格式）維持框架無關的純資料結構，未來同一份 JSON 格式可以直接餵給 React 版本的元件，視覺化程式碼（Canvas/SVG/Cytoscape.js 邏輯）也能盡量原封不動搬過去
  - **為了讓未來抽換 LLM 供應商方便**：所有跟 Gemini SDK 打交道的細節（tool 定義、呼叫、回應解析）都關在 `app/agent.py` 一個檔案裡，對外只暴露 `ask(question, lang) -> {answer, retrievals}` 這個乾淨介面，其他程式（UI、`rag.py`）都不知道底層是哪家 LLM。之後真的要換供應商，改動範圍鎖定在這個檔案內部重寫——刻意不做一層「供應商無關抽象介面」（例如自訂 `LLMProvider` 基底類別），那等於自己刻一個迷你版 LangChain，跟「不用 LangChain」的原則矛盾，且目前沒有「同時支援多家」的真實需求，先做這層抽象是為了假設情境設計，容易做錯
- 地圖解鎖進度：只存在前端（session state / 瀏覽器端），不寫回 MongoDB，重新整理即重置（demo 用途，不需要持久化）
- 地圖資料本身（地點座標、時間線順序、內容文字）：存在 MongoDB

## Schema 設計原則
- Collection 和欄位由你根據功能需求決定，過程中可隨時新增或調整
- 初步構想（正式定案記錄在 `docs/schema.md`）：
  - `characters`：人物/神祇
  - `locations`：地點（含座標、時間線順序、對應章節）
  - `events`：事件（發生地點、涉及人物、章節）
  - `relationships`：人物/地點/事件間的關係邊，供 `$graphLookup` 使用
- 每個節點需同時具備：**embedding 欄位**（vector 查詢入口）+ **明確關係欄位**（graph 遍歷用），兩者缺一不可
- **中英雙語支援**：文字欄位（名稱、描述等）以 `{en, zh}` 平行結構存放
  - 英文為權威來源（Samuel Butler 原文抽取），中文為 LLM 生成翻譯/摘要，中文欄位需標記為 AI 翻譯，不視為絕對準確的原文
  - Embedding 只需存一份（英文原文或中英合併文字皆可），Voyage AI embedding 模型本身支援多語言，中文提問也能匹配英文內容
  - UI 預設顯示中文，提供語言切換或雙語並列，英文原文可作為 Graph RAG 答案可信度的佐證來源
- Schema 變動後必須同步更新：`docs/schema.md`、query agent 的 tool description、embedding index 設定（如有影響）

## 開發策略
- MVP first：先做 Books 9-12（Odysseus 向費阿基亞人自述的漂流歷險：獨眼巨人、風神埃俄羅斯、萊斯特律戈涅斯食人族、瑟西、冥界、賽蓮女妖、斯庫拉與卡律布狄斯、太陽神牛群）
  - 這段是連續地點 + 時間線結構，天生適合地圖/迷霧機制
- **已擴充**：Book 5（離開卡呂普索島、船難抵達費阿基亞）+ Books 21-24（張弓比武、屠殺求婚者、返鄉團圓，壓縮成地圖收尾一站）——見「目前進度」的擴充資料項目，細節與踩過的坑都記在那裡
- 沒收：第 1-4 卷（Telemachus 尋父，政治/家族戲，知名度較低）、第 6-20 卷（費阿基亞人款待、喬裝潛回故鄉的鋪陳段落）——刻意只挑「大家聽過的」經典段落，不是全 24 卷通吃
- 每個功能跑通後再擴大資料範圍，流程確認沒問題後再考慮擴充其他卷冊

## 開發原則
- 所有 Python 執行都在 conda 環境 `odyssey-graph` 內進行（與 `franchise-mlb` 分開，不共用）
- 實作細節你決定，架構有重大變動再告訴我
- 每個步驟執行前說明你打算怎麼做，確認後再動作
- 遇到錯誤或需要 API key 才停下來
- 不要動 `.env` 的內容，API key 一律用 python-dotenv 讀取

## 環境變數（`.env`）
以下變數需存在 `.env`，一律用 python-dotenv 讀取，不要動 `.env` 內容本身：
- `MONGODB_URI`：Atlas 連線字串
- `MONGODB_DB_NAME`：資料庫名稱（暫定 `odyssey_graph`）
- `GEMINI_API_KEY`：Gemini API key（AI Agent / 查詢端 + Books 9-12 LLM 抽取都用這把 key）
- `GEMINI_MODEL`：選填，查詢 agent（`app/agent.py`）用的模型，預設 `gemini-3.6-flash`；改型號只要改這個環境變數，不用動程式碼
- `VOYAGE_API_KEY`：Voyage AI key，`app/rag.py` 自己呼叫 Voyage 算查詢向量用（見「目前進度」AI Agent 項目的 rate limit 說明）——跟 Atlas Automated Embedding 內部用的很可能是同一把 key、共用同一組 rate limit 額度，不是獨立額度
- ~~`ANTHROPIC_API_KEY`~~：已不需要，AI Agent 改用 Gemini（見下方「LLM 供應商使用範圍」）

## LLM 供應商使用範圍
- **查詢 agent（自然語言查詢、Graph RAG 回答，`app/agent.py`）**：Gemini API（`google-genai` SDK，function calling），不用 LangChain
  - **變更記錄**：原本規劃維持 Anthropic SDK，視為「專案核心技術主張、不變」。實作到這步時發現 `.env` 沒有 `ANTHROPIC_API_KEY`，且使用者已有 Gemini 額度，決定整個查詢 agent 也改走 Gemini，不再區分「抽取用 Gemini、查詢用 Anthropic」。demo 真正要展示的技術主張是 **MongoDB Atlas 同時做 Vector Search + `$graphLookup`**，LLM 選哪家不影響這個主張是否成立
  - 所有 Gemini SDK 細節關在 `app/agent.py` 一個檔案裡（見「技術架構」的說明），之後想換回 Anthropic 或別家，只改這個檔案內部
- **Books 9-12 LLM 抽取腳本（`scripts/extract_books.py`）**：`gemini-3.1-flash-lite`（一次性資料準備工作，跟即時查詢 agent 用的模型分開設定，各自選最適合的成本/品質）

## 限制
- 不使用 Neo4j 等專用圖資料庫，堅持用 MongoDB Atlas 展示其原生能力
- 地圖解鎖進度不落地儲存
- Conda 環境名稱固定為 `odyssey-graph`，不要改

## 執行順序
1. 建立專案資料夾結構
2. 建立 Conda 環境 `odyssey-graph` 並安裝套件
3. 設計 MongoDB schema（`docs/schema.md`）並建立 index（含 vector search index）
4. 定義 Books 9-12 權威人物清單（固定 `slug`），供後續兩條 pipeline 合併對應用
5. Wikidata SPARQL 抓取人物基本關係資料（以 `slug` upsert）
6. 取得 Samuel Butler 譯本 Books 9-12 原文，LLM 抽取事件/地點/關係（人物比對同一份 `slug` 清單 upsert）
7. 資料匯入 MongoDB（觸發 Atlas Automated Embedding）
8. 實作 Graph RAG 查詢邏輯（`$graphLookup` + Vector Search）
9. 實作 AI Agent（Gemini API + function calling）
10. Streamlit UI + 嵌入知識圖譜視覺化 component
11. Streamlit UI + 嵌入冒險地圖（迷霧、點擊解鎖）component
12. 進階功能：新手/專家模式切換、Graph RAG vs 一般 RAG 對照展示（split-screen）

## 目前進度
- [x] 環境建立（conda `odyssey-graph`，Python 3.11，見 `requirements.txt`）
- [x] Schema 設計（見 `docs/schema.md`）
- [x] 資料匯入（Wikidata 24 條家族關係 + Gemini 抽取 10 地點/17 事件/5 條敘事關係 + 30 條自動生成 `PARTICIPATES_IN` + 17 條自動生成 `LOCATED_AT`，共 18 人物、76 關係邊，已寫入 MongoDB `odyssey_graph`）
- [x] **資料擴充：Book 5 + Books 21-24**（人物 18→28、地點 10→12、事件 17→27、關係邊 76→150）
  - 新增 10 個人物：Calypso、Hermes、Athena（Book 5）+ Laertes、Eumaeus、Eurycleia、Philoetius、Antinous、Eurymachus、Melanthius（Books 21-24）——Wikidata QID 都是**即時查 `wbsearchentities` 確認的，不是憑訓練記憶猜的**：Antinous 這個名字尤其危險，搜尋結果第一筆是羅馬皇帝哈德良的男寵（Q171876，知名度遠高於奧德賽這個同名求婚者），選錯會查回完全不相關的家族關係；Philoetius 查不到獨立的 Wikidata 條目（只有月球上一個以他命名的坑洞），`wikidata_id` 留 `null`，`fetch_wikidata.py` 的 `load_canonical()` 也同步修正為跳過沒有 `wikidata_id` 的人物，避免組出 `wd:None` 這種無效 SPARQL 值
  - Butler 譯本的角色譯名慣例延續下去：Hermes 全文只用「Mercury」、Athena 全文只用「Minerva」（跟既有的 Neptune=Poseidon、Jove=Zeus 同一套規則），Eurycleia 該譯本拼法是「Euryclea」——都寫進人物的 `aliases`，供抽取時的名稱對應使用
  - **地圖收不收的判斷**：Book 5（離開卡呂普索島、船難抵達費阿基亞）跟 Books 21-24（返鄉復仇）之間，劇情有一大段空白（第 6-20 卷完全沒收），若照單全收接上冒險地圖的連續解鎖機制，會出現一個沒有解釋的斷點。最後決定：Books 21-24 壓縮成地圖上**一個收尾地點**（「重返伊薩卡王宮」，底下掛 6 個事件：張弓比武、屠殺求婚者、懲處叛徒、與 Penelope 相認、與父親 Laertes 重逢、雅典娜促成和平），讓地圖故事線「有始有終」；Book 5 本身不上地圖（純過場、不是獨立一站），但仍是正常 MongoDB 資料，知識圖譜/AI問答/對照展示照常查得到——`locations` 新增 `on_map` 欄位（見 `docs/schema.md`），`app/map_data.py` 的 `fetch_locations()` 用它過濾
  - **`scripts/extract_books.py` 從單一硬編碼腳本改成參數化**（`BATCHES` dict，`python scripts/extract_books.py <book5|books21-24>`），每個 batch 各自的地點/事件「floor list」是我自己讀過對應原文後手寫的（跟原本 9-12 卷 prompt 同等級的策展細節，不是讓 LLM 自由發揮）——**Books 9-12 原本已驗證過的 `extraction_gemini.json` 完全沒有重新生成**，新 batch 各自寫進獨立的 `extraction_gemini_book5.json` / `extraction_gemini_books21-24.json`，避免旗艦展示問題依賴的既有資料被意外改動
  - **`scripts/import_to_mongodb.py` 新增 `merge_batches()`**：合併三個 extraction 檔案前，先幫每個 batch 的 `temp_id`（`loc_1`、`event_1`...）加上 batch 前綴，因為三個 batch 各自獨立從 1 開始編號，直接合併會撞名；同時對 LLM 敘事關係做跨 batch 去重（例如 Book 5 的風暴事件又獨立生出一條 `poseidon ANTAGONIST_OF odysseus`，跟 9-12 卷既有的那條完全重複，去重後只留一條）
  - `scripts/enrich_characters.py` 改成**只幫清單裡新增的 slug 生成中文名/雙語簡介**，已有的 18 筆維持原樣不重新生成，避免規模擴大時意外讓已經驗證過的角色敘述跟著漂移
  - 新出現的敘事關係動詞（`KILLS`、`PUNISHES`、`PRECEDES`、`PROTECTOR_OF`）都補進 `app/i18n.py` 跟 `app/views/graph.py` 的 `RELATION_LABEL`，否則 UI 會直接顯示英文大寫代碼
  - **擴充後全面回歸測試**：旗艦問題「Telemachus 跟 Poseidon 有什麼關係」重跑一次，答案不但沒被新資料稀釋/搞混，反而更豐富（自然帶入了張弓比武、屠殺求婚者的情節）；`filter_relevant_relationships` 的 citation 篩選在關係邊從 76 條增加到 150 條之後依然收斂到 6 條，沒有失控；新增角色/事件也用一個新問題（梅蘭修斯的下場、與 Laertes 重逢）驗證過 AI 問答答得出來；vector search 對新內容（"a father and son reunited..." 語意查詢）正確把「與拉爾提斯重逢」事件排到第一名，確認 Automated Embedding 對新寫入的文件有正常觸發
  - **暫時的落差**：新增的地點（Ogygia、重返伊薩卡王宮）目前沒有配圖（`LOCATION_IMAGES` 對照表還沒收錄 `order` 11/12），地圖卡片會顯示無圖版本，不影響功能；`unmatched_characters` 額外標記出 Ino、Tithonus（Book 5）與 Leiodes、Phemius、Medon、Eupeithes、Dolius、Halitherses、Eurynome（Books 21-24）等次要具名角色，目前刻意不收進權威人物清單，維持精簡範圍
  - **踩過的坑：地圖最後一站解鎖不了**——`app/views/map.py` 的解鎖判斷是 `clicked_order == unlocked_order + 1`（嚴格連續整數），`app/components/odyssey_map` 的 JS 也用同一個假設算迷霧/船的位置。新增收尾地點後，MongoDB 裡的真實 `order` 變成 1-10（9-12 卷）、11（Ogygia，`on_map:false` 被濾掉）、12（收尾站）——地圖上看得到的最後一個可解鎖點，`order` 直接從 10 跳到 12，`10+1=11 ≠ 12`，永遠卡住解不開。修法是 `app/map_data.py` 的 `fetch_locations()` 對已經篩選+排序過的地點**依畫面上的順位重新編號**（1,2,3...11 連續，不用原始 DB 的 `order`），連帶地圖座標也要用重新編號後的順位算（原本存的座標是照 DB `order`=12 算的，會在畫面上留一個對應到 Ogygia 的空隙），DB 本身的 `order` 欄位不動，只在回傳給地圖用的字典裡覆寫——這樣「地圖用的 order 必須連續」這個假設對所有呼叫端都繼續成立，不用去改 Python 跟 JS 兩邊的解鎖判斷邏輯本身
- [x] `$graphLookup` 基本驗證通過（Telemachus → Poseidon 2 跳內可達，旗艦展示問題資料基礎打通）
- [x] 知識圖譜視覺化（`app/views/graph.py` + `app/graph_data.py` + `app/theme.py`，streamlit-agraph，暗色希臘史詩主題，篩選/聚焦/去重/hover 說明都做完）
  - **節點也有 hover 說明**：`fetch_graph_data()` 現在會一併撈 `description`，`graph.py` 的 `Node(...)` 補上 `title=`（沿用邊已經在用的 vis-network 原生 tooltip 機制）——人物/地點/事件節點滑過去都會顯示簡介，不只邊有說明
  - **資料擴充後節點變擠、標籤重疊**（67 個節點，原本 ~45 個）：`streamlit-agraph` 的 `Config()` 建構子只暴露幾個頂層 physics 參數（solver 名稱、timestep、min/maxVelocity），barnesHut 求解器自己的間距選項（`springLength`、`avoidOverlap`）不是建構子參數——但 `config.physics` 本身就是一個普通 dict，直接序列化給前端，所以建構後可以直接塞值進去：`config.physics["barnesHut"] = {...}`。畫布高度也從 700 調到 800px 給更多空間
    - **第一次調過頭**：把 `springLength` 拉到 220、`centralGravity` 降到 0.15，重疊問題解決了，但整體變得很小——原因是 vis-network 穩定後會自動縮放整張圖去塞進固定尺寸的畫布（`stabilization.fit`），圖的實際佔用範圍變大（間距拉開），畫布沒有跟著變大，就會整體縮得更小，節點、字都跟著一起縮水。改成 `springLength` 只小幅調到 150、`centralGravity` 維持預設值（把整張圖拉回中心，不讓佔用範圍膨脹太多，連帶壓低需要的縮放幅度），另外把節點跟字級也直接調大（20/14→24/17，字 15→18）當緩衝，這樣即使還是會有一點自動縮放，剩下的畫面看起來也還夠清楚
    - 這批純粹是根據 vis-network 文件調的參數，我沒有瀏覽器能實際看渲染結果，麻煩實測後回報效果
  - **手機上圖譜沒有跟著縮**：查到 `streamlit-agraph` 的 `Config.__init__` 固定寫死 `self.width = f"{width}px"`——傳 `width="100%"` 進去，字串拼接結果是 `"100%px"`，是**無效的 CSS 值**，不是真的百分比寬度。這個 class 的建構子設計上只吃純數字（像素），完全沒有支援百分比寬度的管道。`app/views/graph.py` 跟 `app/views/compare.py`（`render_subgraph`）都中招，兩處都改成建構完 `Config` 後直接覆寫 `config.width = "100%"`（跳過那段字串拼接，塞一個真正合法的 CSS 百分比值進去）。這是直接讀 `streamlit_agraph` 原始碼確認的，不是猜的；但「vis-network 的 canvas 在視窗真的變窄時會不會即時重新計算尺寸」這件事我沒瀏覽器驗證不了，只能確認畫面初始渲染時的寬度設定值本身是對的
  - 「聚焦特定人物」預設即時呼叫 `$graphLookup`（`graphlookup_ego_network`，每一跳各發一次查詢，人物節點不當跳板的規則靠分兩階段查詢達成），側邊欄 checkbox 可切換回本地 Python BFS 計算（`filter_graph`）——兩者結果驗證一致，預設開啟 `$graphLookup` 讓 demo 直接展示 Atlas 圖遍歷能力，checkbox 保留給需要 rollback 或效能考量時用
  - **`$graphLookup` 寫法**（`_graphlookup_direct_edges()`，`app/graph_data.py`）：
    ```python
    pipeline = [
        {"$match": {"_id": oid}},          # 從哪個節點開始
        {"$graphLookup": {
            "from": "relationships",        # 遞迴查詢的邊集合
            "startWith": "$_id",            # 從目前文件的 _id 開始
            "connectFromField": "to_id",    # 用邊的 to_id 去比對...
            "connectToField": "from_id",    # ...下一層邊的 from_id
            "as": "outgoing",
            "maxDepth": 0,                  # 0 = 只展開直接關係這一層
        }},
        {"$graphLookup": {                  # 再發一次，方向相反
            "from": "relationships", "startWith": "$_id",
            "connectFromField": "from_id", "connectToField": "to_id",
            "as": "incoming", "maxDepth": 0,
        }},
    ]
    ```
    - `connectFromField`/`connectToField` 是遞迴核心：從 `startWith` 出發找 `connectToField` 相符的邊，把那些邊的 `connectFromField` 當下一輪起點，重複到 `maxDepth`
    - 關係邊有方向性（`from_id→to_id`），`$graphLookup` 一次只能沿一個方向走，所以要發兩次（順向+反向）合併才是完整鄰居
    - `maxDepth: 0` 刻意只展開一層——第二跳是否要展開（人物節點不當跳板）由應用層邏輯決定要不要對特定第一跳結果再發一次查詢，不讓 `$graphLookup` 自己遞迴到底
    - `$graphLookup` 前面一定要接在某個已知文件上，因為 `characters`/`locations`/`events` 是三個不同 collection，程式依序嘗試直到找到該 `_id` 所在的 collection
- [x] 冒險地圖（迷霧/解鎖）（`app/views/map.py` + `app/map_data.py` + `app/components/odyssey_map/`）
  - **自訂 component 是純手刻的靜態 HTML/SVG/JS**（`app/components/odyssey_map/frontend/index.html`），沒有用 npm/React build——直接實作 Streamlit component 的原始 postMessage 協定（`streamlit:componentReady`／`streamlit:render`／`streamlit:setComponentValue`／`streamlit:setFrameHeight`），`declare_component(name, path=...)` 指向這個純靜態資料夾即可，不需要額外的前端 build pipeline
  - 地圖視覺：地點間用二次貝茲曲線（`seaPathD`，控制點往垂直方向偏移）畫成類似航線的弧線而非直線；未解鎖地點用固定大小、`feGaussianBlur` 模糊的橢圓（`fogBlur` filter）蓋住，不用 `feTurbulence` 程序化雲霧（試過，濾鏡範圍算不準、肉眼無法預覽，容易整個炸掉，改用簡單模糊更可控）
  - **解鎖動畫是 component 內部自己維護的一個小型狀態機**（`displayOrder`／`targetOrder`／`stepBusy`），不是單純把 Python 傳來的 `unlocked_order`直接拿來畫：
    - 每次只前進一站，一站的動畫（畫線＋船沿路徑用 `<animateMotion>` 移動＋抵達後迷霧解開）跑完才會讓下一站變成可點擊——如果直接用 Python 傳來的值即時渲染，下一站會在動畫播完「之前」就已經是可點擊狀態，快速連點會出現「線還沒畫完，下下一站卻被解鎖」的 bug
    - `unlocked_order` 變小（重新開始）或帶 `instant=True`（「解鎖全部」按鈕）時直接瞬間跳過去，不跑動畫
    - 船的定位跟晃動動畫故意拆成兩層 `<g>`：CSS `transform` 動畫（晃動）會整個蓋掉元素自己的 `transform` 屬性（定位用）而不是疊加，兩者要分開才不會互相打架
  - 地點卡片圖片：10 個地點各配一張真實公版藝術作品（Wikimedia Commons 個別核實授權，Willy Pogány 1918 年《奧德賽》繪本插畫 2 張 + John Flaxman 版畫 7 張 + Isaac Moillon／Theodoor van Thulden 油畫版畫各 1 張），存在 `app/assets/locations/`，`scripts/import_to_mongodb.py` 的 `LOCATION_IMAGES` 表按 `order` 掛進 `locations.image` / `locations.image_credit`（非 LLM 抽取內容，故不混進 `extraction_gemini.json`）；卡片上圖片維持原始比例顯示（試過 `object-fit: cover` 會裁到內容、`contain` 塞進固定框會留白，兩者都不好看，最後讓框直接貼合圖片本身大小，只設最大高度）
- [x] **Streamlit 多頁架構改用 `st.navigation` + `st.Page`**：`app/main.py` 是薄路由器，`app/views/graph.py`／`app/views/map.py` 是實際頁面內容，檔名跟網址都用英文（`/graph`、`/map`），但 `st.Page(..., title="知識圖譜"/"冒險地圖")` 讓側邊欄顯示的還是中文——藉此避免程式檔名/URL 出現中文，同時 UI 文字不受影響
- [x] **中英文全站切換**（`app/i18n.py` + `app/main.py` 側欄 radio）：`STRINGS = {"zh": {...}, "en": {...}}` + `t(key)` 查表，`get_lang()` 讀 `st.session_state.lang`；資料內容（人物/地點/事件名稱、描述）本來就有 `{en, zh}` 欄位，UI 這層只是接上 `lang=get_lang()`
  - **踩過的坑**：`st.multiselect` 在語言切換時會把已選項清空——懷疑前端是用「顯示文字」而非底層值比對已選項，`format_func` 讓同一個值在不同語言下顯示不同文字時，前端就認不出是同一個已選項，導致跟後端 session_state 兜不起來。改成三個獨立 `st.checkbox`（無「選項清單比對」，各自只是一個布林值）後問題消失。用 Streamlit 官方的 `streamlit.testing.v1.AppTest`（不用開瀏覽器，純 Python 模擬 widget 互動+rerun）驗證過修復後的行為正確
  - 語言切換元件本身用 `key="lang"` 直接綁定 `session_state`，不手動呼叫 `st.rerun()`——因為 Streamlit 在 script 重新執行「之前」就會把 widget 新值寫進 session_state，手動比對新舊值再呼叫 `st.rerun()` 等於疊加一次多餘的 rerun
  - 曾經試過把語言切換搬到 `pg.run()` 之前（側邊欄最上面、導覽選單正下方），理論上「全域設定該跟導覽放一起」——但實際看起來像沒有標題的兩顆按鈕突兀地卡在導覽選單下面，改回原本「`pg.run()` 之後」放最下面，維持原樣
- [x] **Tab 順序調整**：`app/main.py` 的 `st.navigation` 清單改成 冒險地圖 → 知識圖譜 → 對照展示 → AI 問答（原本是 知識圖譜 → 冒險地圖 → AI 問答 → 對照展示，跟 CLAUDE.md 原本規劃的順序有落差，也沒有把對照展示往前提）——冒險地圖當作門面第一個看到，知識圖譜接著看底層結構，對照展示這個「說服力最強」的環節緊接在後而不是被排到最後，AI 問答（自由問答、沒有固定劇本）放在最後收尾
- [x] **Vector Search**（`scripts/create_vector_indexes.py`）：`characters`/`locations`/`events` 各建一個 Atlas Vector Search index，用 **Automated Embedding**（`type: "autoEmbed"`，非手動算 embedding 的 `type: "vector"`），指向 `embedding_source`，模型 `voyage-4`；`locations`/`events` 額外加 `type: "filter"` 的 `order` 欄位，供之後新手模式防雷查詢直接在 index 層 pre-filter（`order <= 目前解鎖進度`）
  - **語法是即時查官方文件確認的**，不是憑訓練記憶——`autoEmbed` 是較新的功能，模型名稱也跟舊版（`voyage-3-large` 等）不同，現在是 `voyage-4` / `voyage-4-lite` / `voyage-4-large` / `voyage-code-3`
  - **踩過的坑**：
    - 原本的 Atlas cluster 跟 `franchise-mlb` 專案共用，免費/共享層 cluster 的 FTS index 數量上限（整個 cluster 跨所有資料庫共用額度）已經被 `franchise-mlb` 的 3 個 index 用滿，`odyssey-graph` 這邊一個都建不了——這是跨專案資源衝突，非我能自行決定，請使用者決定後**重建了一個獨立的新 cluster**（`MONGODB_URI` 已更新），資料用 `scripts/import_to_mongodb.py` 重新匯入一次
    - `$vectorSearch` 查詢即使用 Automated Embedding（傳文字 `query` 而非 `queryVector`），`numCandidates` 依然是必填，沒帶會直接報錯 `numCandidates is required for approximate vector search`
    - Automated Embedding 產生的向量**不會**以 `embedding` 欄位寫回文件本身（跟手動 embedding 模式不同）——向量存在 Atlas 的 search index 基礎設施裡，用 `db.collection.find()` 查不到，屬正常行為，不是沒生效
  - 已驗證端到端可用：查詢 "a giant one-eyed monster who eats sailors" 正確把 Polyphemus（獨眼巨人）排進前三名結果
- [x] **Graph RAG 查詢邏輯**（`app/rag.py`，`graph_rag_retrieve(query, lang)`）：對 `characters`/`locations`/`events` 三個 collection 做 `$vectorSearch` 找語意相關節點，再對每個命中節點跑 `_graphlookup_direct_edges()`（重用 `graph_data.py` 已有的函式）展開直接關係；`expand_depth=2` 時再對 hop-1 鄰居中的 event/location（不含 character，理由同知識圖譜頁的「人物不當跳板」規則）多展開一跳，關係邊的 `from_type`/`to_type` 欄位已經有型別資訊，不用額外查詢就能判斷是否該繼續展開。回傳 `{matches, relationships, citations}`，citations 從命中的 event 節點的 `source_excerpt` 帶出
  - **用兩個旗艦問題實測驗證過**（見「功能需求」的範例問題）：Telemachus/Poseidon 兩跳關係、Odysseus/Polyphemus/Poseidon 兩跳關係都正確從 `relationships` 裡重建出完整路徑
  - 過程中發現原規劃的「Odysseus 的盟友的敵人」這題資料庫裡沒有 `ALLY_OF` 關係、答不出來，換成「刺瞎波呂斐摩斯的人跟波塞頓的關係」（用 `BLINDS` + `CHILD_OF` 兩跳）
- [x] **AI Agent**（`app/agent.py` + `app/views/qa.py`，Tab 3「AI 問答」）：Gemini function calling，單一 tool `search_odyssey_graph` 包住 `graph_rag_retrieve()`；對外只暴露 `ask(question, lang) -> {answer, retrievals}`，UI 跟其他模組不碰 Gemini SDK 細節（見「技術架構」的供應商隔離說明）
  - Gemini 的 content 只有 `user`/`model` 兩種 role，沒有像 Anthropic/OpenAI 那樣獨立的 tool/function role——function 執行結果是用 `Part.from_function_response()` 包成一個 `role="user"` 的新 turn 送回去
  - SDK 語法是對照**實際裝好的 `google-genai==2.17.0`** 用 `inspect`/`model_fields` 反查確認的，不是憑訓練記憶——這個套件版本間 API 差異不小（同時存在較舊的 `models.generate_content` 跟較新的 `interactions.create` 兩種介面，選了前者，因為型別明確、跟 Anthropic Messages API 的呼叫模式更接近）
  - `st.chat_message`/`st.chat_input` 做對話 UI，每則回答下面有個「回答依據」collapsible，把 `graph_rag_retrieve` 回傳的關係路徑跟原文引用整理出來——這個是**程式直接組出來的，不是依賴 Gemini 自己在文字裡有沒有老實引用**，可信度不依賴模型自律
  - 側欄有兩個旗艦問題的快速按鈕，demo 時不用手打
  - 用兩個旗艦問題實測過完整流程（不只 retrieval，含 Gemini 生成的最終答案），路徑跟中文回答都正確
  - **實測成本**：單次問答（含兩次 Gemini 呼叫）約 6,200 prompt tokens + 1,100 output tokens，US$0.018/題（`gemini-3.6-flash`：input $1.50/1M、output $7.50/1M），demo 規模完全不用擔心。實測發現內部「思考」token（`thoughts_token_count`）在合成答案那次呼叫佔比比可見輸出還高，且用 output 費率計價——這個任務屬於「把已檢索到的結構化資料組織成答案」，不需要深度推理，測試 `thinking_config=ThinkingConfig(thinking_level="low")` 答案品質沒有變化、成本降約 40%，已套用。另外發現 prompt 成本（把 `graph_rag_retrieve` 撈到的完整關係邊列表塞給模型）其實佔整體成本 8 成以上，比 output 更值得優化，但還沒動手（trim 掉不必要的欄位有風險影響答案品質，需要先測過再套用）
  - **Voyage AI rate limit（query-time embedding）**：`app/rag.py` 的 `graph_rag_retrieve()` 原本對 `characters`/`locations`/`events` 三個 collection 各用 `$vectorSearch` 的 `query` 文字參數（觸發 Atlas Automated Embedding 自動呼叫 Voyage），同一句問題被重複 embed 三次，demo 測試時很快就撞到 Voyage 的 RPM 限制。改成**自己呼叫 Voyage AI 一次**（`_embed_query()`，用 `.env` 裡原本沒用到的 `VOYAGE_API_KEY`），把同一個向量重複用在三個 collection 的 `$vectorSearch`（改用 `queryVector` 而非 `query`），一題從 3 次 Voyage 請求降到 1 次
    - **索引用 `numDimensions=1024`、`quantization="scalar"`，這個是查了 `list_search_indexes()` 的實際回傳確認的，不是憑猜的**——Atlas 建 autoEmbed index 時沒讓你指定這些參數、是它自動決定的，跟 `scripts/create_vector_indexes.py` 裡寫的 index 定義不會直接告訴你這兩個值
    - 因為 index 是 `scalar` 量化，`queryVector` 必須是 **int8**、不能是 float32（直接傳 float32 會被 Atlas 拒絕，錯誤訊息會告訴你要傳 int8），所以呼叫 Voyage 時要帶 `output_dtype="int8"`、`output_dimension=1024`，並用 `bson.binary.Binary.from_vector(vec, BinaryVectorDtype.INT8)` 包成 BSON 向量
    - 用 `input_type="query"`（Voyage 的非對稱 embedding，query 跟 document 的 embed 方式不同，要對應 Atlas 對 `$vectorSearch` 查詢文字的處理方式，不能隨便用預設）
    - 已驗證：自己 embed 出來的分數跟原本 Automated Embedding 自動算的幾乎一致（同一個查詢字串跑兩次，top-3 結果與分數幾乎相同），確認替換沒有損失準確度
    - 注意：這個改動**沒有繞開** Voyage 的 rate limit 額度（同一把 key 共用同一組配額），純粹是把「同一句話重複算 3 次」降成「算 1 次重複用」，實打實減少 2/3 的請求量，不是找漏洞
- [x] **Graph RAG 對照展示**（`app/views/compare.py`，Tab 4）：同一問題同時跑 `rag.vector_only_search()`（純向量，不展開關係）+ `agent.ask_vector_only()` vs 既有的 `agent.ask()`（Graph RAG），左右分欄呈現。範例問題見「功能需求」段落
  - 頁面結構（左右欄標題）一開始就顯示，不是選了問題才出現——讓使用者一進來就懂這頁在比較什麼
  - `graph.py` 的 `NODE_TYPE_COLOR`/`LABEL_FONT_COLOR`/`NODE_TYPE_SHAPE` 抽到 `graph_data.py` 共用，知識圖譜頁跟這裡的子圖視覺化樣式保證一致，不會兩邊各自維護後跑掉
  - 純向量那側的 prompt 刻意誠實（片段不夠就承認答不出來，不能瞎猜關係），不是刻意做壞來襯托 Graph RAG——這樣對比才有說服力，不是稻草人
  - **踩過的坑**：原本只把「問題文字」存進 `session_state`，沒有存「執行結果」，導致單純切到別的 tab 再切回來，也會被當成「有問題要處理」重新跑一次兩條 pipeline（重新呼叫 Gemini + Voyage，白花錢又要重新等）。改成結果也存進 `session_state.compare_result`，只有點了新問題才清快取重新跑
- [x] **技術歸屬徽章**（`app/theme.py` 的 `atlas_badge()` + 四個頁面都掛上）：原本四個頁面各自用 `st.caption()` 標示「Powered by MongoDB Atlas」，但 `theme.py` 把 `.stCaption` 設成斜體、75% 透明度、置中小字（給一般說明文字用），套在技術歸屬標示上反而不夠顯眼、容易被忽略——另外知識圖譜頁是唯一真的寫了這行字的頁面（還是寫死的英文，沒走 i18n），冒險地圖頁完全沒有，跟「好玩畫面要有明顯標示」的要求（見開頭「核心定位」）不符
  - 新增獨立的 `.atlas-badge` CSS class：實心邊框膠囊、`Cinzel` 字體大寫小字＋不透明背景，跟頁面標題同一個視覺語彙但夠醒目，不是用發光/裝飾特效達成（沿用本專案一貫的設計克制原則）
  - 四個頁面都改用 `theme.atlas_badge(t(...))`：知識圖譜（`$graphLookup + Vector Search`）、AI 問答（沿用原本 `qa.caption` 文字）、對照展示（新增 `compare.badge`：`Vector Search vs $graphLookup`，跟原本純描述性的 `compare.caption` 分開兩行）、冒險地圖（新增 `map.badge`：純品牌歸屬，因為地圖本身的迷霧/解鎖機制是前端邏輯、不是特定 Atlas 查詢能力的展示，跟其他三頁性質不同）
- [x] **全面回歸測試**（資料擴充 + 這幾輪 UI/圖譜調整之後，一次跑過所有能在沒有瀏覽器情況下驗證的層面）：20 項全過，0 fail、0 error
  - **資料完整性**：collection 筆數（28/12/27/150）符合預期；`events.location_id`／`relationships.from_id`/`to_id` 沒有懸空引用；`locations.on_map` 正確（11 個 `true`、1 個 `false`=Ogygia）；150 條關係邊沒有 `(from,to,relation)` 完全重複的；28 個人物都有中英雙語 `description`
  - **知識圖譜**：`fetch_graph_data()` 節點/邊數正確、每個節點都有 `description`（hover 說明不會漏）；針對 4 個人物（odysseus、poseidon、laertes、antinous）驗證本地 BFS 聚焦結果跟即時 `$graphLookup` 完全一致
  - **冒險地圖**：11 個地點 `order` 連續無斷點（1-11）、地圖座標單調遞增無重疊；**用程式碼原封不動模擬 `map.py` 的解鎖判斷式（`clicked_order == unlocked_order + 1`）跑過整條 1→11 序列，確認剛才那個「最後一站解不開」的 bug 真的修好了**；11 個地點都至少掛了一個事件
  - **Vector Search**：新資料（"a father and son reunited..." 語意查詢）正確命中「與拉爾提斯重逢」；舊資料回歸測試（"一隻吃水手的獨眼怪物"）依然正確命中 Polyphemus，沒有因為擴充而劣化
  - **AI Agent — 6 題旗艦問題全部跑過 `ask()` 跟 `ask_vector_only()` 兩條 pipeline**（不是只挑幾題抽測）：Graph RAG 六題全部正確答出連結的角色、citation 邊數落在 3-7 條之間（沒有失控爆量）；純向量六題全部誠實承認/迴避，沒有一題誤答或瞎猜——確認資料擴充後，六個旗艦問題展示的「向量搜不到、Graph RAG 找得到」對比依然成立
  - **i18n 完整性**：DB 裡實際用到的 15 種關係代碼，中英文標籤都齊全，沒有漏翻譯掉回英文大寫代碼的
  - **測試腳本本身**：`/Users/brian/.claude/jobs/7b4c02c2/tmp/full_regression_test.py`（跑一次過程中兩個真的網路問題重試後通過，兩個測試腳本自己的 bug 也修掉了）——這個腳本放在 job 暫存目錄，不是專案的一部分，之後要重跑回歸測試需要重新寫或找回這份
- [ ] 地點導覽卡/角色初登場卡的「AI 自動生成介紹」（目前卡片文字是資料庫既有欄位，不是即時生成）
- [ ] 多視角敘事
- [x] **Streamlit Cloud 部署準備**
  - 新增 `.gitignore`（排除 `.env`、`.streamlit/secrets.toml`、`__pycache__` 等），專案原本沒有 git repo
  - `requirements.txt` 移除沒在用的 `anthropic` 套件（改用 Gemini 後留下的殘留依賴，`app/agent.py` 裡唯一的 "Anthropic" 字樣只是註解提到，不是真的 import）
  - **新增 `app/secrets_util.py` 的 `get_secret(key, default=None)`**，取代所有 `os.environ[...]`/`os.environ.get(...)` 讀密鑰的地方（`db.py`／`rag.py`／`agent.py` 共 5 處）：本地開發還是走 `os.environ`（`.env` 沒變），但額外 fallback 讀 `st.secrets`——原因是查了 Streamlit 官方文件，只確認「本地 `secrets.toml` 的內容同時能用環境變數讀到」，但 **Community Cloud 專屬文件沒有明確重申這件事對 Cloud 面板貼進去的 secrets 是否同樣成立**，只保證 `st.secrets` 這條路徑在 Cloud 上一定能用。與其賭 Cloud 是否真的把面板 secrets 也塞進 `os.environ`，兩條路都接，不管哪個假設成立都能動
  - `scripts/*.py`（資料準備用的一次性腳本）沒有改，維持原本的 `os.environ[...]`——這些腳本只會在本地跑、不會部署到 Streamlit Cloud，不需要這層保險
  - 部署到 Streamlit Cloud 時，`.streamlit/config.toml`（自訂主題）不用擔心路徑問題——Cloud 是從 repo 根目錄執行 `streamlit run app/main.py`，跟本機測過的「一定要從專案根目錄啟動」是同一種執行方式（見前面「Streamlit cwd」那次踩過的坑）

## Commands
- 啟動環境：`conda activate odyssey-graph`
- 執行 app：`streamlit run app/main.py`
- 匯入資料：`python scripts/import_to_mongodb.py`
- 執行測試：`pytest`

## 自然語言查詢實作方式
使用 Gemini API function calling（見「AI Agent」進度項目的細節）：
- 定義 `search_odyssey_graph` tool，對應 `app/rag.py` 的 `graph_rag_retrieve()`（`$graphLookup` + Vector Search 混合查詢，不是分開兩個 tool）
- Gemini 自動決定何時呼叫 tool、要搜尋什麼關鍵字
- 執行查詢後把結果（節點 + 關係路徑 + 原文引用）整理成自然語言回答，並要求模型在回答中明確寫出用到的關係路徑
- UI 端另外用程式直接組出「回答依據」面板（不依賴模型文字裡有沒有引用），可信度更高
- 新手模式（尚未實作）：規劃額外帶入「目前解鎖進度」，透過 `locations`/`events` 的 `order` filter 欄位（`$vectorSearch` 的 pre-filter，見 `scripts/create_vector_indexes.py`）限制查詢範圍，避免劇透
