#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国内 AI 公司「重大公告 + 多源快讯 + 行情」采集器 (宁精勿滥版)。"""
import os, sys, json, re, datetime as dt
from zoneinfo import ZoneInfo

CN = ZoneInfo("Asia/Shanghai")

MAJOR_KW = ("业绩", "快报", "年报", "半年报", "季报", "预告", "预增", "预减", "扭亏",
            "中标", "合同", "订单", "收购", "重组", "并购", "增发", "配股", "定增",
            "可转债", "解禁", "回购", "减持", "增持", "股权激励", "风险提示", "澄清",
            "停牌", "复牌", "重大", "诉讼", "仲裁", "控制权", "分红", "派息",
            "增资", "减资", "设立", "战略合作", "投资")

COMPANIES = [
    {"name": "智谱AI",   "code": "02513", "market": "HK", "tier": "head", "aliases": ["智谱", "GLM", "Z.ai"]},
    {"name": "DeepSeek", "code": "",      "market": "NA", "tier": "head", "aliases": ["DeepSeek", "深度求索", "梁文锋", "幻方"]},
    {"name": "月之暗面",  "code": "",      "market": "NA", "tier": "head", "aliases": ["月之暗面", "Kimi", "Moonshot", "杨植麟"]},
    {"name": "MiniMax",  "code": "00100", "market": "HK", "tier": "head", "aliases": ["MiniMax", "稀宇"]},
    {"name": "阶跃星辰",  "code": "",      "market": "NA", "tier": "head", "aliases": ["阶跃星辰", "StepFun", "阶跃"]},
    {"name": "百川智能",  "code": "",      "market": "NA", "tier": "full", "aliases": ["百川智能", "王小川"]},
    {"name": "零一万物",  "code": "",      "market": "NA", "tier": "full", "aliases": ["零一万物", "李开复"]},
    {"name": "寒武纪",   "code": "688256", "market": "A",  "tier": "head", "aliases": ["寒武纪"]},
    {"name": "摩尔线程",  "code": "688795", "market": "A",  "tier": "head", "aliases": ["摩尔线程"]},
    {"name": "沐曦股份",  "code": "688802", "market": "A",  "tier": "full", "aliases": ["沐曦"]},
    {"name": "壁仞科技",  "code": "06082", "market": "HK", "tier": "full", "aliases": ["壁仞"]},
    {"name": "燧原科技",  "code": "",      "market": "NA", "tier": "full", "aliases": ["燧原"]},
    {"name": "天数智芯",  "code": "09903", "market": "HK", "tier": "full", "aliases": ["天数智芯"]},
    {"name": "黑芝麻智能", "code": "02533", "market": "HK", "tier": "full", "aliases": ["黑芝麻智能"]},
    {"name": "海光信息",  "code": "688041", "market": "A",  "tier": "head", "aliases": ["海光信息", "海光"]},
    {"name": "长鑫存储",  "code": "",      "market": "NA", "tier": "full", "aliases": ["长鑫存储", "长鑫", "CXMT"]},
    {"name": "长江存储",  "code": "",      "market": "NA", "tier": "full", "aliases": ["长江存储", "YMTC"]},
    {"name": "中科曙光",  "code": "603019", "market": "A",  "tier": "full", "aliases": ["中科曙光"]},
    {"name": "浪潮信息",  "code": "000977", "market": "A",  "tier": "full", "aliases": ["浪潮信息"]},
    {"name": "工业富联",  "code": "601138", "market": "A",  "tier": "head", "aliases": ["工业富联"]},
    {"name": "润泽科技",  "code": "300442", "market": "A",  "tier": "head", "aliases": ["润泽科技"]},
    {"name": "奥飞数据",  "code": "300738", "market": "A",  "tier": "full", "aliases": ["奥飞数据"]},
    {"name": "光环新网",  "code": "300383", "market": "A",  "tier": "full", "aliases": ["光环新网"]},
    {"name": "数据港",   "code": "603881", "market": "A",  "tier": "full", "aliases": ["数据港"]},
    {"name": "科华数据",  "code": "002335", "market": "A",  "tier": "full", "aliases": ["科华数据"]},
    {"name": "润建股份",  "code": "002929", "market": "A",  "tier": "full", "aliases": ["润建股份"]},
    {"name": "协鑫能科",  "code": "002015", "market": "A",  "tier": "full", "aliases": ["协鑫能科"]},
    {"name": "国电南瑞",  "code": "600406", "market": "A",  "tier": "full", "aliases": ["国电南瑞"]},
    {"name": "国网信通",  "code": "600131", "market": "A",  "tier": "full", "aliases": ["国网信通"]},
    {"name": "南网科技",  "code": "688248", "market": "A",  "tier": "full", "aliases": ["南网科技"]},
    {"name": "金盘科技",  "code": "688676", "market": "A",  "tier": "full", "aliases": ["金盘科技"]},
    {"name": "海博思创",  "code": "300288", "market": "A",  "tier": "full", "aliases": ["海博思创"]},
    {"name": "中恒电气",  "code": "002364", "market": "A",  "tier": "full", "aliases": ["中恒电气"]},
    {"name": "科大讯飞",  "code": "002230", "market": "A",  "tier": "head", "aliases": ["科大讯飞", "讯飞"]},
    {"name": "商汤",     "code": "00020", "market": "HK", "tier": "head", "aliases": ["商汤"]},
    {"name": "云知声",   "code": "09678", "market": "HK", "tier": "full", "aliases": ["云知声"]},
    {"name": "第四范式",  "code": "06682", "market": "HK", "tier": "full", "aliases": ["第四范式"]},
    {"name": "星环科技",  "code": "688031", "market": "A",  "tier": "full", "aliases": ["星环科技"]},
    {"name": "拓尔思",   "code": "300229", "market": "A",  "tier": "full", "aliases": ["拓尔思"]},
    {"name": "神州数码",  "code": "000034", "market": "A",  "tier": "full", "aliases": ["神州数码"]},
    {"name": "东方国信",  "code": "300166", "market": "A",  "tier": "full", "aliases": ["东方国信"]},
    {"name": "弘信电子",  "code": "300657", "market": "A",  "tier": "full", "aliases": ["弘信电子"]},
    {"name": "鸿博股份",  "code": "002229", "market": "A",  "tier": "full", "aliases": ["鸿博股份", "英博数科"]},
    {"name": "南威软件",  "code": "603636", "market": "A",  "tier": "full", "aliases": ["南威软件"]},
    {"name": "超讯通信",  "code": "603322", "market": "A",  "tier": "full", "aliases": ["超讯通信"]},
    {"name": "彩讯股份",  "code": "300634", "market": "A",  "tier": "full", "aliases": ["彩讯股份"]},
    {"name": "硅基流动",  "code": "",      "market": "NA", "tier": "full", "aliases": ["硅基流动", "SiliconFlow", "袁进辉"]},
    {"name": "无问芯穹",  "code": "",      "market": "NA", "tier": "full", "aliases": ["无问芯穹"]},
    {"name": "算力互联",  "code": "",      "market": "NA", "tier": "full", "aliases": ["算力互联"]},
    {"name": "迅策科技",  "code": "03317", "market": "HK", "tier": "full", "aliases": ["迅策科技", "迅策"]},
]

def window(mode):
    hours = int(os.getenv("WINDOW_HOURS", "24" if mode == "head" else "72"))
    now = dt.datetime.now(CN)
    return now - dt.timedelta(hours=hours), now

def _parse(ts):
    if ts is None:
        return None
    s = str(ts).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s[:19].strip(), fmt).replace(tzinfo=CN)
        except ValueError:
            continue
    m = re.match(r"^(\d{1,2}):(\d{2})(:\d{2})?$", s)
    if m:
        d = dt.datetime.now(CN).date()
        return dt.datetime.combine(d, dt.time(int(m.group(1)), int(m.group(2))), tzinfo=CN)
    return None

def _norm(t):
    return re.sub(r"[\s\W_]+", "", str(t))[:60]

def _ak():
    import akshare as ak
    return ak

def fetch_cninfo(code, market, start, end):
    out = []
    try:
        ak = _ak()
        mk = "港股" if market == "HK" else "沪深京"
        df = ak.stock_zh_a_disclosure_report_cninfo(
            symbol=code, market=mk,
            start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d"))
        for _, r in df.iterrows():
            title = str(r.get("公告标题", "")).strip()
            t = _parse(r.get("公告时间"))
            if t is None or t < start or not any(k in title for k in MAJOR_KW):
                continue
            ann, org = r.get("announcementId", ""), r.get("orgId", "")
            url = (f"http://www.cninfo.com.cn/new/disclosure/detail?"
                   f"stockCode={code}&announcementId={ann}&orgId={org}&announcementTime={t:%Y-%m-%d}")
            out.append({"title": title, "time": t, "url": url, "src": "巨潮资讯网·公告"})
    except Exception as e:
        out.append({"_err": f"cninfo {code}: {e}"})
    return out

def fetch_flash_all():
    rows = []
    ak = _ak()
    def grab(fn, kw, mk):
        try:
            df = fn() if kw is None else fn(symbol=kw)
            for _, r in df.iterrows():
                rows.append(mk(r))
        except Exception as e:
            rows.append({"_err": f"{getattr(fn,'__name__','?')}: {e}"})
    grab(ak.stock_info_global_cls, "全部",
         lambda r: {"title": str(r.get("标题") or "").strip(), "text": str(r.get("内容") or "").strip(),
                    "time": _parse(r.get("发布时间")), "src": "财联社快讯", "url": "https://www.cls.cn/telegraph"})
    grab(ak.stock_info_global_sina, None,
         lambda r: {"title": "", "text": str(r.get("内容") or "").strip(),
                    "time": _parse(r.get("时间")), "src": "新浪财经快讯", "url": "https://finance.sina.com.cn/7x24/"})
    grab(ak.stock_info_global_ths, None,
         lambda r: {"title": str(r.get("标题") or "").strip(), "text": str(r.get("内容") or "").strip(),
                    "time": _parse(r.get("发布时间")), "src": "同花顺快讯",
                    "url": str(r.get("链接") or "https://news.10jqka.com.cn/").strip()})
    grab(ak.stock_info_global_em, None,
         lambda r: {"title": str(r.get("标题") or "").strip(), "text": str(r.get("摘要") or "").strip(),
                    "time": _parse(r.get("发布时间")), "src": "东方财富快讯",
                    "url": str(r.get("链接") or "https://kuaixun.eastmoney.com/").strip()})
    return rows

def match_flash(flash, aliases, start):
    out = []
    for it in flash:
        if "_err" in it:
            continue
        t = it["time"]
        if t is None or t < start:
            continue
        hay = (it.get("title", "") + it.get("text", ""))
        if any(a and a in hay for a in aliases):
            title = it.get("title") or it.get("text", "")[:44]
            out.append({"title": title, "time": t, "url": it["url"], "src": it["src"]})
    return out

def fetch_spot():
    quotes = {}
    for fn, ytd in (("stock_zh_a_spot_em", True), ("stock_hk_spot_em", False)):
        try:
            df = getattr(_ak(), fn)()
            for _, r in df.iterrows():
                quotes[str(r["代码"])] = {"price": r.get("最新价"), "chg": r.get("涨跌幅"),
                                          "ytd": r.get("年初至今涨跌幅") if ytd else None}
        except Exception:
            pass
    return quotes

def dedup(items):
    seen, out = set(), []
    for it in sorted([i for i in items if "_err" not in i], key=lambda x: x["time"], reverse=True):
        key = (_norm(it["title"]), it.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out

def build(mode, flash=None, quotes=None):
    start, end = window(mode)
    scope = [c for c in COMPANIES if mode == "full" or c["tier"] == "head"]
    flash = flash if flash is not None else fetch_flash_all()
    quotes = quotes if quotes is not None else fetch_spot()
    records, errors = [], [f["_err"] for f in flash if "_err" in f]
    for c in scope:
        items = []
        if c["code"] and c["market"] in ("A", "HK"):
            items += fetch_cninfo(c["code"], c["market"], start, end)
        items += match_flash(flash, c["aliases"], start)
        errors += [i["_err"] for i in items if "_err" in i]
        q = quotes.get(c["code"]) if c["code"] else None
        records.append({"company": c["name"], "code": c["code"], "market": c["market"],
                        "quote": q, "items": dedup(items)})
    return {"mode": mode, "generated_at": end.isoformat(), "window_start": start.isoformat(),
            "records": records, "errors": errors}

def render_md(report):
    start = dt.datetime.fromisoformat(report["window_start"])
    end = dt.datetime.fromisoformat(report["generated_at"])
    L = [f"# 国内AI公司要闻清单 | {end:%Y-%m-%d %H:%M} (回溯至 {start:%m-%d %H:%M}, MODE={report['mode']})", ""]
    empty = []
    for rec in report["records"]:
        if not rec["items"]:
            empty.append(rec["company"]); continue
        head = f"## {rec['company']}"
        if rec["code"]:
            head += f" ({rec['code']}.{rec['market']})"
        L.append(head)
        for it in rec["items"]:
            L.append(f"- [{it['time']:%m-%d %H:%M}] {it['title']} （{it['src']}）{it['url']}")
        q = rec["quote"]
        if q and q.get("chg") is not None:
            ytd = f", 年初至今 {q['ytd']}%" if q.get("ytd") is not None else ""
            L.append(f"- 辅助·行情: 最新 {q['price']}, 涨跌幅 {q['chg']}%{ytd}")
        L.append("")
    if empty:
        L += ["## 本期无重大动态", "、".join(empty), ""]
    if report["errors"]:
        L.append(f"> 抓取告警 {len(report['errors'])} 条(见 report.json)")
    return "\n".join(L)

if __name__ == "__main__":
    mode = os.getenv("MODE", "head").lower()
    if mode not in ("head", "full"):
        mode = "head"
    report = build(mode)
    with open("report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    md = render_md(report)
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    print(f"\n[done] mode={mode} 公司={len(report['records'])} 告警={len(report['errors'])}")
