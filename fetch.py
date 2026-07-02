"""
抓取模块：从 RSS 源拉取新闻，按时间窗过滤、去重。
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import feedparser

import config


def _entry_time(entry) -> datetime | None:
    """尽力解析条目的发布时间，返回带时区的 UTC datetime；解析不到返回 None。"""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            # feedparser 给的是 UTC struct_time
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return None


def fetch_feed(feed: dict) -> list[dict]:
    """抓单个源，返回标准化后的条目列表。抓取失败抛异常由调用方处理。"""
    parsed = feedparser.parse(feed["url"])
    items = []
    for e in parsed.entries:
        items.append({
            "source": feed["name"],
            "title": (e.get("title") or "").strip(),
            "summary": (e.get("summary") or e.get("description") or "").strip(),
            "link": e.get("link") or "",
            "published": _entry_time(e),
        })
    return items


def fetch_all(lookback_hours: float) -> list[dict]:
    """
    抓取所有源，只保留 lookback 窗口内的新闻，按时间倒序，去重。
    """
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=lookback_hours + config.LOOKBACK_BUFFER_HOURS
    )
    all_items: list[dict] = []

    for feed in config.RSS_FEEDS:
        try:
            items = fetch_feed(feed)
        except Exception as exc:  # 单源失败不影响整体
            print(f"[warn] 抓取失败 {feed['name']}: {exc}")
            continue

        for it in items:
            # 没时间戳的条目：保守起见保留（宁可多送给模型也别漏掉突发）
            if it["published"] is None or it["published"] >= cutoff:
                all_items.append(it)

    # 去重（按标题归一化）
    seen = set()
    deduped = []
    for it in all_items:
        key = it["title"].lower().replace(" ", "")[:80]
        if key and key not in seen:
            seen.add(key)
            deduped.append(it)

    # 有时间的排前面、按时间倒序；无时间的排后面
    deduped.sort(key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc),
                 reverse=True)

    return deduped[: config.MAX_ITEMS_TO_MODEL]


def verify_feeds() -> None:
    """自检：逐个测试每个源当前是否可用、能返回多少条。部署前先跑这个。"""
    print("=== 新闻源自检 ===\n")
    for feed in config.RSS_FEEDS:
        try:
            items = fetch_feed(feed)
            n = len(items)
            latest = None
            for it in items:
                if it["published"]:
                    latest = it["published"].astimezone(ZoneInfo(config.LOCAL_TZ))
                    break
            latest_str = latest.strftime("%m-%d %H:%M") if latest else "无时间戳"
            status = "✅" if n > 0 else "⚠️ 0 条"
            print(f"{status}  {feed['name']:<18} 条数={n:<4} 最新={latest_str}")
        except Exception as exc:
            print(f"❌  {feed['name']:<18} 失败: {exc}")
    print("\n把 ❌ 或 ⚠️ 的源换掉再部署。")
