#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
intl_monitor.py —— 外媒采集器(Google News RSS, 按公司英文名逐个查)
====================================================================
目的: 抓“外媒报道了名单里的中国AI公司 / 国外巨头”的新闻。很多对中国企业的
敏感或负面报道只在外媒出现, 国内媒体不发, 这一层专门补这个缺口。

数据源: Google News RSS 搜索(每家一个查询), 每条带来源媒体 + 原文链接。
  · 跑在 GitHub 境外 runner 上可正常访问(本地在国内会被墙, 所以别挪本地)。
  · 链接是 Google 的跳转地址, 能解析到原文。

窗口: 默认回溯 24 小时(与国内日报一致), 可用 WINDOW_HOURS 覆盖。
输出: report_intl.md + report_intl.json
"""
import os, sys, json, re, datetime as dt, urllib.parse, urllib.request

UTC = dt.timezone.utc

# (公司显示名, 分组, Google News 查询词)  —— 中国公司用英文名, 易撞词的加一个限定词
COMPANIES_INTL = [
    # ── 中国公司(重点: 外媒的敏感/负面多在这里)──
    ("DeepSeek",        "中国", "DeepSeek"),
    ("智谱AI",          "中国", "Zhipu AI"),
    ("月之暗面/Kimi",   "中国", "Moonshot AI Kimi"),
    ("MiniMax",         "中国", "MiniMax AI China"),
    ("阶跃星辰",        "中国", "StepFun"),
    ("寒武纪",          "中国", "Cambricon"),
    ("摩尔线程",        "中国", "Moore Threads"),
    ("沐曦",            "中国", "MetaX GPU China"),
    ("壁仞科技",        "中国", "Biren chip"),
    ("海光信息",        "中国", "Hygon chip"),
    ("长鑫存储",        "中国", "CXMT memory"),
    ("长江存储",        "中国", "YMTC"),
    ("科大讯飞",        "中国", "iFlytek"),
    ("商汤",            "中国", "SenseTime"),
    # ── 国外巨头(噪音会大)──
    ("NVIDIA",          "国外", "Nvidia"),
    ("TSMC",            "国外", "TSMC"),
    ("ASML",            "国外", "ASML"),
    ("AMD",             "国外", "AMD chip"),
    ("Micron",          "国外", "Micron"),
    ("SK Hynix",        "国外", "SK Hynix"),
    ("Samsung",         "国外", "Samsung chip"),
    ("Broadcom",        "国外", "Broadcom"),
    ("Intel",           "国外", "Intel chip"),
    ("OpenAI",          "国外", "OpenAI"),
    ("Anthropic",       "国外", "Anthropic Claude"),
    ("Microsoft",       "国外", "Microsoft AI"),
    ("Google/Gemini",   "国外", "Google Gemini AI"),
    ("Meta",            "国外", "Meta AI"),
    ("xAI",             "国外", "xAI Grok"),
    ("CoreWeave",       "国外", "CoreWeave"),
    ("Palantir",        "国外", "Palantir"),
    ("Oracle",          "国外", "Oracle AI cloud"),
]

def window():
    hours = int(os.getenv("WINDOW_HOURS", "24"))
    now = dt.datetime.now(UTC)
    return now - dt.timedelta(hours=hours), now

def _norm(t):
    return re.sub(r"[\s\W_]+", "", str(t)).lower()[:70]

def gnews_url(query):
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

def fetch_one(query, start):
    """抓一个公司的 Google News RSS, 返回窗口内的 [{title,time,url,src}]。"""
    import feedparser
    out = []
    try:
        feed = feedparser.parse(gnews_url(query))
        for e in feed.entries:
            tp = getattr(e, "published_parsed", None)
            if not tp:
                continue
            t = dt.datetime(*tp[:6], tzinfo=UTC)
            if t < start:
                continue
            title = getattr(e, "title", "").strip()
            src = ""
            if getattr(e, "source", None) and getattr(e.source, "title", None):
                src = e.source.title
            elif " - " in title:            # Google 标题常以 " - 媒体名" 结尾
                title, src = title.rsplit(" - ", 1)
            out.append({"title": title.strip(), "time": t,
                        "url": getattr(e, "link", ""), "src": src or "外媒"})
    except Exception as e:
        out.append({"_err": f"{query}: {e}"})
    return out

def dedup(items):
    seen, out = set(), []
    for it in sorted([i for i in items if "_err" not in i],
                     key=lambda x: x["time"], reverse=True):
        k = _norm(it["title"])
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out

def build(_mock=None):
    start, end = window()
    records, errors = [], []
    for name, group, query in COMPANIES_INTL:
        items = _mock.get(name, []) if _mock is not None else fetch_one(query, start)
        errors += [i["_err"] for i in items if "_err" in i]
        records.append({"company": name, "group": group, "items": dedup(items)})
    return {"generated_at": end.isoformat(), "window_start": start.isoformat(),
            "records": records, "errors": errors}

def render_md(rep):
    start = dt.datetime.fromisoformat(rep["window_start"])
    end = dt.datetime.fromisoformat(rep["generated_at"])
    L = [f"# 外媒动态清单 | {end:%Y-%m-%d %H:%M} UTC (回溯 {start:%m-%d %H:%M}~)", ""]
    for grp, label in (("中国", "外媒·中国公司"), ("国外", "外媒·国外巨头")):
        L.append(f"### 【{label}】")
        empty = []
        for rec in rep["records"]:
            if rec["group"] != grp:
                continue
            if not rec["items"]:
                empty.append(rec["company"]); continue
            L.append(f"## {rec['company']}")
            for it in rec["items"][:5]:      # 每家最多 5 条, 控噪音
                L.append(f"- [{it['time']:%m-%d %H:%M}] {it['title']} （{it['src']}）{it['url']}")
            L.append("")
        if empty:
            L += [f"本组本期无外媒动态: {'、'.join(empty)}", ""]
    if rep["errors"]:
        L.append(f"> 抓取告警 {len(rep['errors'])} 条(见 report_intl.json)")
    return "\n".join(L)

def selftest():
    now = dt.datetime.now(UTC)
    mock = {
        "DeepSeek": [
            {"title": "DeepSeek faces scrutiny over data practices, report says",
             "time": now - dt.timedelta(hours=5), "url": "https://news.google.com/x", "src": "Reuters"},
            {"title": "DeepSeek faces scrutiny over data practices, report says",  # 重复
             "time": now - dt.timedelta(hours=5), "url": "https://news.google.com/x", "src": "Reuters"},
        ],
        "NVIDIA": [
            {"title": "Nvidia stock slips as AI trade cools",
             "time": now - dt.timedelta(hours=3), "url": "https://news.google.com/y", "src": "CNBC"},
        ],
        "寒武纪": [],
    }
    global COMPANIES_INTL
    COMPANIES_INTL = [c for c in COMPANIES_INTL if c[0] in mock]
    rep = build(_mock=mock)
    print(render_md(rep))
    ds = next(r for r in rep["records"] if r["company"] == "DeepSeek")
    assert len(ds["items"]) == 1, f"去重失败:{len(ds['items'])}"
    print("\n[selftest] OK — 外媒装配 / 去重 / 分组 / 渲染 均通过")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); sys.exit(0)
    rep = build()
    with open("report_intl.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2, default=str)
    md = render_md(rep)
    with open("report_intl.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    print(f"\n[done] 外媒公司={len(rep['records'])} 告警={len(rep['errors'])}")
