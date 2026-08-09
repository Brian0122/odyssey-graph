"""Shared bilingual UI strings + language toggle.

`st.session_state.lang` is the single source of truth ("zh" | "en"), set
once by the sidebar toggle in app/main.py — session state is shared
across all pages in a Streamlit multipage app, so the choice persists as
the user navigates between 知識圖譜/冒險地圖.

This only covers UI chrome (titles, labels, buttons). Data content
(character/location/event names & descriptions) already carries its own
{en, zh} pair per docs/schema.md — callers pass get_lang() straight into
the fetch_* functions instead of going through this dict.
"""

import streamlit as st

STRINGS = {
    "zh": {
        "graph.page_title": "奧德賽知識圖譜",
        "graph.nav_title": "知識圖譜",
        "graph.epigraph": "「繆思啊，請告訴我那位機智過人的英雄的故事，"
                           "他在攻陷特洛伊城後，又漂泊了許多年月……」——《奧德賽》卷一開篇",
        "graph.badge": "Powered by MongoDB Atlas — $graphLookup + Vector Search",
        "graph.filters": "篩選",
        "graph.show_types": "顯示節點類型",
        "graph.show_all": "（顯示全部）",
        "graph.focus_select": "聚焦特定人物（只顯示他的直接關係）",
        "graph.use_graphlookup": "聚焦時改用 MongoDB $graphLookup 即時查詢",
        "graph.use_graphlookup_help": "預設即時呼叫 $graphLookup 查詢資料庫，用來展示 Atlas 的圖遍歷能力；"
                                       "取消勾選則改用本地計算（BFS），較快。兩者結果應該一致，若 $graphLookup "
                                       "版本有問題，取消勾選即可馬上退回本地計算的版本。",
        "graph.no_nodes": "目前篩選條件下沒有節點可顯示，調整左側篩選選項。",
        "graph.footer": "{nodes} 個節點、{edges} 條關係邊",
        "node_type.character": "人物",
        "node_type.location": "地點",
        "node_type.event": "事件",
        "relation.CHILD_OF": "子女",
        "relation.FATHER_OF": "父親",
        "relation.MOTHER_OF": "母親",
        "relation.PARENT_OF": "父母",
        "relation.MARRIED_TO": "配偶",
        "relation.SIBLING_OF": "手足",
        "relation.ANTAGONIST_OF": "宿敵",
        "relation.BLINDS": "刺瞎",
        "relation.CAUSES": "導致",
        "relation.PARTICIPATES_IN": "參與",
        "relation.LOCATED_AT": "發生於",
        "relation.KILLS": "殺死",
        "relation.PUNISHES": "懲處",
        "relation.PRECEDES": "先於",
        "relation.PROTECTOR_OF": "守護",
        "map.page_title": "奧德賽冒險地圖",
        "map.title": "冒險地圖",
        "map.epigraph": "「他見過許多民族的城市，領略過他們的心志，"
                         "在海上也身受重重苦難……」——《奧德賽》卷一開篇",
        "map.caption": "點擊發光的下一站，逐步撥開迷霧、推進航程",
        "map.badge": "Powered by MongoDB Atlas",
        "map.progress": "航程進度",
        "map.progress_caption": "已解鎖 {n} / {max} 站",
        "map.unlock_all": "解鎖全部",
        "map.restart": "重新開始",
        "map.events_heading": "這裡發生的事",
        "map.characters_heading": "登場角色",
        "map.source_excerpt": "原文：{excerpt}",
        "map.not_started": "點擊地圖上發光的下一站，開始你的航程。",
        "map.footer": "進度僅保存在本次瀏覽 session，重新整理頁面會重置。",
        "map.fogged_label": "？？？",
        "map.journey_end_badge": "終點：重返家園",
        "qa.page_title": "奧德賽問答",
        "qa.nav_title": "AI 問答",
        "qa.epigraph": "「奧德修斯啊，你想問的事，我這就從頭一一道來……」",
        "qa.caption": "Powered by MongoDB Atlas — Vector Search + $graphLookup（Graph RAG）",
        "qa.input_placeholder": "問問奧德賽裡的人物、地點或事件……",
        "qa.thinking": "查詢知識圖譜、生成回答中…",
        "qa.citations_heading": "原文依據",
        "qa.source_excerpt": "原文引用：{excerpt}",
        "qa.no_citations": "這次回答沒有用到圖譜資料。",
        "qa.error": "查詢時發生問題（可能是暫時性的網路或流量限制），請稍後再試一次。",
        "qa.clear_chat": "清除對話",
        "qa.example_questions": "範例問題",
        "compare.page_title": "Graph RAG 對照展示",
        "compare.nav_title": "對照展示",
        "compare.badge": "Powered by MongoDB Atlas — Vector Search vs $graphLookup",
        "compare.caption": "同一個問題，兩套 pipeline 並列比較",
        "compare.select_question": "從側欄選一個範例問題，兩邊會同時執行。",
        "compare.vector_placeholder": "選一個範例問題後，這裡會顯示純向量搜尋抓到的片段，以及只憑這些片段生成的回答。",
        "compare.graph_placeholder": "選一個範例問題後，這裡會顯示 Graph RAG 展開出的關係路徑、子圖視覺化，以及完整回答。",
        "compare.thinking": "兩套 pipeline 執行中…",
        "compare.vector_column": "純向量 RAG",
        "compare.graph_column": "Graph RAG",
        "compare.snippets_heading": "語意搜尋命中的片段",
        "compare.answer_heading": "回答",
        "compare.path_heading": "關係路徑（$graphLookup 展開）",
        "compare.subgraph_heading": "子圖視覺化",
        "compare.no_path": "這題沒有用到額外的關係展開。",
        "sidebar.language": "語言",
    },
    "en": {
        "graph.page_title": "Odyssey Knowledge Graph",
        "graph.nav_title": "Knowledge Graph",
        "graph.epigraph": "“Tell me, O muse, of that ingenious hero who travelled far and wide "
                           "after he had sacked the famous town of Troy…” "
                           "— The Odyssey, Book I",
        "graph.badge": "Powered by MongoDB Atlas — $graphLookup + Vector Search",
        "graph.filters": "Filters",
        "graph.show_types": "Show node types",
        "graph.show_all": "(show all)",
        "graph.focus_select": "Focus on a character (direct relations only)",
        "graph.use_graphlookup": "Use live MongoDB $graphLookup when focusing",
        "graph.use_graphlookup_help": "Defaults to calling $graphLookup against the database live, to "
                                       "demonstrate Atlas's graph traversal. Uncheck to use a local BFS "
                                       "instead (faster). Results should match either way — uncheck to roll "
                                       "back instantly if the $graphLookup path misbehaves.",
        "graph.no_nodes": "No nodes match the current filters — adjust the filters on the left.",
        "graph.footer": "{nodes} nodes, {edges} relationships",
        "node_type.character": "Character",
        "node_type.location": "Location",
        "node_type.event": "Event",
        "relation.CHILD_OF": "Child of",
        "relation.FATHER_OF": "Father of",
        "relation.MOTHER_OF": "Mother of",
        "relation.PARENT_OF": "Parent of",
        "relation.MARRIED_TO": "Married to",
        "relation.SIBLING_OF": "Sibling of",
        "relation.ANTAGONIST_OF": "Antagonist of",
        "relation.BLINDS": "Blinds",
        "relation.CAUSES": "Causes",
        "relation.PARTICIPATES_IN": "Participates in",
        "relation.LOCATED_AT": "Located at",
        "relation.KILLS": "Kills",
        "relation.PUNISHES": "Punishes",
        "relation.PRECEDES": "Precedes",
        "relation.PROTECTOR_OF": "Protector of",
        "map.page_title": "Odyssey Adventure Map",
        "map.title": "Adventure Map",
        "map.epigraph": "“Many cities did he visit, and many were the nations with whose manners "
                         "and customs he was acquainted; moreover he suffered much by sea…” "
                         "— The Odyssey, Book I",
        "map.caption": "Click the glowing next stop to part the fog and advance",
        "map.badge": "Powered by MongoDB Atlas",
        "map.progress": "Voyage Progress",
        "map.progress_caption": "{n} / {max} stops unlocked",
        "map.unlock_all": "Unlock All",
        "map.restart": "Restart",
        "map.events_heading": "What happened here",
        "map.characters_heading": "Characters",
        "map.source_excerpt": "Source text: {excerpt}",
        "map.not_started": "Click the glowing next stop on the map to begin your voyage.",
        "map.footer": "Progress only lasts this browser session — reloading the page resets it.",
        "map.fogged_label": "???",
        "map.journey_end_badge": "Journey's End: Homecoming",
        "qa.page_title": "Odyssey Q&A",
        "qa.nav_title": "AI Q&A",
        "qa.epigraph": "“Ask, and I will tell you all, from the beginning…”",
        "qa.caption": "Powered by MongoDB Atlas — Vector Search + $graphLookup (Graph RAG)",
        "qa.input_placeholder": "Ask about a character, location, or event in the Odyssey…",
        "qa.thinking": "Searching the knowledge graph and drafting an answer…",
        "qa.citations_heading": "Source citations",
        "qa.source_excerpt": "Source text: {excerpt}",
        "qa.no_citations": "This answer didn't draw on the graph data.",
        "qa.error": "Something went wrong while searching (possibly a transient network or rate-limit issue) — please try again in a moment.",
        "qa.clear_chat": "Clear chat",
        "qa.example_questions": "Example questions",
        "compare.page_title": "Graph RAG Comparison",
        "compare.nav_title": "Comparison",
        "compare.badge": "Powered by MongoDB Atlas — Vector Search vs $graphLookup",
        "compare.caption": "Same question, two pipelines, side by side",
        "compare.select_question": "Pick an example question from the sidebar to run both pipelines.",
        "compare.vector_placeholder": "Once you pick a question, this side will show the snippets found by semantic search alone, and the answer generated from just those snippets.",
        "compare.graph_placeholder": "Once you pick a question, this side will show the relationship path $graphLookup expanded, a subgraph visualization, and the full answer.",
        "compare.thinking": "Running both pipelines…",
        "compare.vector_column": "Vector RAG Only",
        "compare.graph_column": "Graph RAG",
        "compare.snippets_heading": "Snippets matched by semantic search",
        "compare.answer_heading": "Answer",
        "compare.path_heading": "Relationship path ($graphLookup expansion)",
        "compare.subgraph_heading": "Subgraph",
        "compare.no_path": "No additional relationships were expanded for this question.",
        "sidebar.language": "Language",
    },
}


def get_lang() -> str:
    return st.session_state.get("lang", "zh")


def t(key: str, **kwargs) -> str:
    lang = get_lang()
    text = STRINGS.get(lang, {}).get(key) or STRINGS["zh"].get(key, key)
    return text.format(**kwargs) if kwargs else text
