#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
live.py —— 实时监测采集器(喂 GitHub Pages 网页)
================================================
两档模式, 由 workflow 按 cron 决定:
  MODE=fast  每 15 分钟: 只拉 4 个国内快讯流(4 个请求, 几十秒), 匹配全部公司。
             注意: 财联社/东财等国内快讯也报英伟达/OpenAI, 所以国外公司也用中文别名匹配。
  MODE=slow  每小时:     巨潮公告(逐家) + 外媒 Google News(逐家) + 行情。慢, 但覆盖全。

两档结果都并进同一份 docs/data.json(累积 + 去重 + 只保留 48 小时), 网页读它。

本地自检: python live.py --selftest   (不联网)
"""
import os, sys, json, re, hashlib, datetime as dt
from zoneinfo import ZoneInfo

CN = ZoneInfo("Asia/Shanghai")
UTC = dt.timezone.utc
DATA = "docs/data.json"
KEEP_HOURS = 48
MAX_ITEMS = 1500

# 只保留这些类别的公告, 琐碎公告丢弃
MAJOR_KW = ("业绩", "快报", "年报", "半年报", "季报", "预告", "预增", "预减", "扭亏",
            "中标", "合同", "订单", "收购", "重组", "并购", "增发", "配股", "定增",
            "可转债", "解禁", "回购", "减持", "增持", "股权激励", "风险提示", "澄清",
            "停牌", "复牌", "重大", "诉讼", "仲裁", "控制权", "分红", "派息",
            "增资", "设立", "战略合作", "投资", "辅导", "上市", "招股", "聆讯")

# ── 公司总表 ────────────────────────────────────────────────────────────────
# name 显示名 / group 国内|国外 / code 代码 / market A|HK|NA
# cn   中文别名(用于国内快讯匹配, 必须够特指, 否则误命中)
# en   Google News 英文查询词(留空则不查外媒)
# pri  重要性(越小越靠前)
C = lambda n, g, code, mk, cn, en, pri: {
    "name": n, "group": g, "code": code, "market": mk, "cn": cn, "en": en, "pri": pri}

COMPANIES = [
    # ── 国内: 大模型 ──
    C("DeepSeek", "国内", "", "NA", ["DeepSeek", "深度求索", "梁文锋", "幻方"], "DeepSeek", 1),
    C("智谱AI", "国内", "02513", "HK", ["智谱", "GLM", "Z.ai"], "Zhipu AI", 2),
    C("月之暗面", "国内", "", "NA", ["月之暗面", "Kimi", "Moonshot", "杨植麟"], "Moonshot AI Kimi", 3),
    C("MiniMax", "国内", "00100", "HK", ["MiniMax", "稀宇"], "MiniMax AI China", 4),
    C("阶跃星辰", "国内", "", "NA", ["阶跃星辰", "StepFun"], "StepFun AI", 5),
    C("百川智能", "国内", "", "NA", ["百川智能", "王小川"], "Baichuan AI", 30),
    C("零一万物", "国内", "", "NA", ["零一万物", "李开复"], "01.AI Kai-Fu Lee", 31),
    # ── 国内: 芯片 ──
    C("寒武纪", "国内", "688256", "A", ["寒武纪"], "Cambricon", 6),
    C("海光信息", "国内", "688041", "A", ["海光信息", "海光"], "Hygon chip", 7),
    C("摩尔线程", "国内", "688795", "A", ["摩尔线程"], "Moore Threads", 8),
    C("沐曦股份", "国内", "688802", "A", ["沐曦"], "MetaX GPU China", 20),
    C("壁仞科技", "国内", "06082", "HK", ["壁仞"], "Biren Technology", 21),
    C("燧原科技", "国内", "", "NA", ["燧原"], "Enflame chip", 32),
    C("天数智芯", "国内", "09903", "HK", ["天数智芯"], "Iluvatar CoreX", 33),
    C("黑芝麻智能", "国内", "02533", "HK", ["黑芝麻智能"], "Black Sesame chip", 34),
    # ── 国内: 存储 ──
    C("长鑫存储", "国内", "", "NA", ["长鑫存储", "长鑫", "CXMT"], "CXMT memory China", 9),
    C("长江存储", "国内", "", "NA", ["长江存储", "YMTC"], "YMTC", 10),
    # ── 国内: 服务器/算力 ──
    C("工业富联", "国内", "601138", "A", ["工业富联"], "Foxconn Industrial Internet", 11),
    C("中科曙光", "国内", "603019", "A", ["中科曙光"], "Dawning Information Sugon", 22),
    C("浪潮信息", "国内", "000977", "A", ["浪潮信息"], "Inspur", 23),
    C("润泽科技", "国内", "300442", "A", ["润泽科技"], "", 24),
    C("奥飞数据", "国内", "300738", "A", ["奥飞数据"], "", 40),
    C("光环新网", "国内", "300383", "A", ["光环新网"], "", 41),
    C("数据港", "国内", "603881", "A", ["数据港"], "", 42),
    # ── 国内: 算电协同 ──
    C("科华数据", "国内", "002335", "A", ["科华数据"], "", 43),
    C("润建股份", "国内", "002929", "A", ["润建股份"], "", 44),
    C("协鑫能科", "国内", "002015", "A", ["协鑫能科"], "", 45),
    C("国电南瑞", "国内", "600406", "A", ["国电南瑞"], "", 46),
    C("国网信通", "国内", "600131", "A", ["国网信通"], "", 47),
    C("南网科技", "国内", "688248", "A", ["南网科技"], "", 48),
    C("金盘科技", "国内", "688676", "A", ["金盘科技"], "", 49),
    C("海博思创", "国内", "300288", "A", ["海博思创"], "", 50),
    C("中恒电气", "国内", "002364", "A", ["中恒电气"], "", 51),
    # ── 国内: AI 软件 / Token ──
    C("科大讯飞", "国内", "002230", "A", ["科大讯飞", "讯飞"], "iFlytek", 12),
    C("商汤", "国内", "00020", "HK", ["商汤"], "SenseTime", 13),
    C("云知声", "国内", "09678", "HK", ["云知声"], "Unisound", 52),
    C("第四范式", "国内", "06682", "HK", ["第四范式"], "4Paradigm", 53),
    C("星环科技", "国内", "688031", "A", ["星环科技"], "", 54),
    C("拓尔思", "国内", "300229", "A", ["拓尔思"], "", 55),
    C("神州数码", "国内", "000034", "A", ["神州数码"], "", 56),
    C("东方国信", "国内", "300166", "A", ["东方国信"], "", 57),
    C("弘信电子", "国内", "300657", "A", ["弘信电子"], "", 58),
    C("鸿博股份", "国内", "002229", "A", ["鸿博股份", "英博数科"], "", 59),
    C("南威软件", "国内", "603636", "A", ["南威软件"], "", 60),
    C("超讯通信", "国内", "603322", "A", ["超讯通信"], "", 61),
    C("彩讯股份", "国内", "300634", "A", ["彩讯股份"], "", 62),
    C("硅基流动", "国内", "", "NA", ["硅基流动", "SiliconFlow", "袁进辉"], "SiliconFlow", 63),
    C("无问芯穹", "国内", "", "NA", ["无问芯穹"], "Infinigence AI", 64),
    C("算力互联", "国内", "", "NA", ["算力互联"], "", 65),
    C("迅策科技", "国内", "03317", "HK", ["迅策科技", "迅策"], "", 66),
    # ── 国外 ──
    C("OpenAI", "国外", "", "NA", ["OpenAI", "ChatGPT", "奥特曼", "Sora"], "OpenAI", 1),
    C("英伟达", "国外", "", "NA", ["英伟达", "NVIDIA", "黄仁勋"], "Nvidia", 2),
    C("Anthropic", "国外", "", "NA", ["Anthropic", "Claude"], "Anthropic Claude", 3),
    C("台积电", "国外", "", "NA", ["台积电"], "TSMC", 4),
    C("ASML", "国外", "", "NA", ["ASML", "阿斯麦"], "ASML", 5),
    C("谷歌/Gemini", "国外", "", "NA", ["谷歌", "Gemini", "Alphabet"], "Google Gemini AI", 6),
    C("微软", "国外", "", "NA", ["微软"], "Microsoft AI", 7),
    C("Meta", "国外", "", "NA", ["Meta", "扎克伯格"], "Meta AI", 8),
    C("xAI", "国外", "", "NA", ["xAI", "Grok"], "xAI Grok", 9),
    C("AMD", "国外", "", "NA", ["AMD"], "AMD chip", 10),
    C("美光", "国外", "", "NA", ["美光"], "Micron", 11),
    C("博通", "国外", "", "NA", ["博通"], "Broadcom", 12),
    C("SK海力士", "国外", "", "NA", ["海力士"], "SK Hynix", 13),
    C("三星电子", "国外", "", "NA", ["三星电子"], "Samsung chip", 14),
    C("英特尔", "国外", "", "NA", ["英特尔"], "Intel chip", 15),
    C("甲骨文", "国外", "", "NA", ["甲骨文"], "Oracle AI cloud", 16),
    C("CoreWeave", "国外", "", "NA", ["CoreWeave"], "CoreWeave", 17),
    C("Palantir", "国外", "", "NA", ["Palantir"], "Palantir", 18),
    C("亚马逊", "国外", "", "NA", ["亚马逊", "AWS"], "Amazon AWS AI", 19),
    C("特斯拉", "国外", "", "NA", ["特斯拉", "马斯克"], "Tesla AI", 20),
    C("苹果", "国外", "", "NA", ["苹果公司", "Apple Intelligence"], "Apple AI", 21),
    C("Arista", "国外", "", "NA", ["Arista"], "Arista Networks", 22),
    C("Crusoe", "国外", "", "NA", ["Crusoe"], "Crusoe Energy AI", 23),
    C("高意Coherent", "国外", "", "NA", ["高意", "Coherent"], "Coherent Corp", 24),
    C("Salesforce", "国外", "", "NA", ["Salesforce"], "Salesforce AI", 25),
]

def _ak():
    import akshare as ak
    return ak

def _parse(ts, tz=CN):
    if ts is None:
        return None
    s = str(ts).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s[:19].strip(), fmt).replace(tzinfo=tz)
        except ValueError:
            continue
    m = re.match(r"^(\d{1,2}):(\d{2})(:\d{2})?$", s)
    if m:
        d = dt.datetime.now(tz).date()
        return dt.datetime.combine(d, dt.time(int(m.group(1)), int(m.group(2))), tzinfo=tz)
    return None


TIME_KEYS = ("publishTime", "pubTime", "showTime", "createTime", "updateTime",
             "newsTime", "time", "date", "publishDate", "pubDate")

def _parse_epoch_or_str(d):
    """从一条原始记录里找出真实时间; 找不到返回 None(调用方必须丢弃该条)。"""
    for k in TIME_KEYS:
        v = d.get(k)
        if v in (None, "", 0):
            continue
        # 毫秒/秒时间戳
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
            n = int(v)
            if n > 1e12:
                n //= 1000
            if 1e9 < n < 4e9:
                return dt.datetime.fromtimestamp(n, CN)
            continue
        t = _parse(str(v))
        if t:
            return t
    return None

def _norm(t):
    return re.sub(r"[\s\W_]+", "", str(t)).lower()[:60]

def mk_id(company, title):
    return hashlib.md5((company + "|" + _norm(title)).encode()).hexdigest()[:12]

def mk_item(co, title, time, url, src, kind, exact=True):
    """exact=False 表示只知道日期、不知道具体时分, 页面不会显示“几分钟前”, 也不算新。"""
    return {"id": mk_id(co["name"], title), "company": co["name"], "group": co["group"],
            "code": co["code"], "market": co["market"], "pri": co["pri"],
            "title": title.strip(), "time": time.isoformat(), "url": url,
            "src": src, "kind": kind, "exact": bool(exact)}

# ── fast: 国内快讯5源 + 东财公告大全 + 财新 ────────────────────────────────
def collect_fast():
    ak = _ak()
    flash, errs = [], []
    def grab(fn, kw, mapper, src, url):
        try:
            df = fn() if kw is None else fn(symbol=kw)
            for _, r in df.iterrows():
                title, text, t, u = mapper(r)
                if t:
                    flash.append({"title": title, "text": text, "time": t,
                                  "src": src, "url": u or url})
        except Exception as e:
            errs.append(f"{src}: {e}")

    grab(ak.stock_info_global_cls, "全部",
         lambda r: (str(r.get("标题") or "").strip(), str(r.get("内容") or "").strip(),
                    _parse(r.get("发布时间")), ""),
         "财联社", "https://www.cls.cn/telegraph")
    grab(ak.stock_info_global_sina, None,
         lambda r: ("", str(r.get("内容") or "").strip(), _parse(r.get("时间")), ""),
         "新浪财经", "https://finance.sina.com.cn/7x24/")
    grab(ak.stock_info_global_ths, None,
         lambda r: (str(r.get("标题") or "").strip(), str(r.get("内容") or "").strip(),
                    _parse(r.get("发布时间")), str(r.get("链接") or "")),
         "同花顺", "https://news.10jqka.com.cn/")
    grab(ak.stock_info_global_em, None,
         lambda r: (str(r.get("标题") or "").strip(), str(r.get("摘要") or "").strip(),
                    _parse(r.get("发布时间")), str(r.get("链接") or "")),
         "东方财富", "https://kuaixun.eastmoney.com/")
    grab(ak.stock_info_global_futu, None,   # 富途: 港美股为主, 补国外公司与港股
         lambda r: (str(r.get("标题") or "").strip(), str(r.get("内容") or "").strip(),
                    _parse(r.get("发布时间")), str(r.get("链接") or "")),
         "富途牛牛", "https://news.futunn.com/")

    items = []
    for co in COMPANIES:
        for f in flash:
            hay = f["title"] + f["text"]
            if any(a and a in hay for a in co["cn"]):
                items.append(mk_item(co, f["title"] or f["text"][:60],
                                     f["time"], f["url"], f["src"], "快讯"))

    # 财新: akshare 封装把时间字段丢了, 这里直连原始接口取真实发布时间。
    # 原则: 拿不到可靠时间就整条丢弃, 绝不用“抓取时刻”冒充发布时间。
    try:
        import requests
        r = requests.get("https://cxdata.caixin.com/api/dataplus/sjtPc/news",
                         params={"pageNum": "1", "pageSize": "100", "showLabels": "true"},
                         headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                                "Chrome/143.0.0.0 Safari/537.36",
                                  "referer": "https://cxdata.caixin.com/index/newsTab?tab=latest"},
                         timeout=20)
        rows = r.json()["data"]["data"]
        if rows:
            print("[debug] 财新原始字段:", sorted(rows[0].keys())[:20])
            print("[debug] 财新首条样例:", {k: str(v)[:40] for k, v in list(rows[0].items())[:8]})
        got, skipped = 0, 0
        for d in rows:
            t = _parse_epoch_or_str(d)
            if t is None:
                skipped += 1
                continue
            txt = str(d.get("summary") or d.get("title") or "").strip()
            if not txt:
                continue
            for co in COMPANIES:
                if any(a and a in txt for a in co["cn"]):
                    items.append(mk_item(co, txt[:80], t, str(d.get("url") or ""),
                                         "财新网", "快讯", exact=True))
                    got += 1
        if skipped:
            errs.append(f"财新: {skipped} 条无可靠时间已丢弃(字段可能变了)")
        print(f"[debug] 财新命中 {got} 条, 丢弃 {skipped} 条")
    except Exception as e:
        errs.append(f"财新: {e}")

    # 东财公告大全: A股全市场公告一次拉完(比逐家查巨潮快得多), 时间取发现时刻
    try:
        a_map = {c["code"]: c for c in COMPANIES if c["market"] == "A" and c["code"]}
        now = dt.datetime.now(CN)
        for d in (now, now - dt.timedelta(days=1)):
            stamp = d.replace(hour=0, minute=0, second=0, microsecond=0)  # 只有日期, 不编时分
            df = ak.stock_notice_report(symbol="全部", date=d.strftime("%Y%m%d"))
            for _, r in df.iterrows():
                code = str(r.get("代码", "")).strip()
                co = a_map.get(code)
                if not co:
                    continue
                title = str(r.get("公告标题", "")).strip()
                if not any(k in title for k in MAJOR_KW):
                    continue
                items.append(mk_item(co, title, stamp, str(r.get("网址") or ""),
                                     "东财公告", "公告", exact=False))
    except Exception as e:
        errs.append(f"东财公告大全: {e}")
    return items, errs

# ── slow: 巨潮公告 + 外媒 RSS ───────────────────────────────────────────────
def collect_slow():
    items, errs = [], []
    start = dt.datetime.now(CN) - dt.timedelta(hours=KEEP_HOURS)
    ak = _ak()
    # 公告
    for co in COMPANIES:
        if not co["code"] or co["market"] != "HK":   # A股公告已由快线的东财公告大全覆盖
            continue
        try:
            df = ak.stock_zh_a_disclosure_report_cninfo(
                symbol=co["code"], market=("港股" if co["market"] == "HK" else "沪深京"),
                start_date=start.strftime("%Y%m%d"),
                end_date=dt.datetime.now(CN).strftime("%Y%m%d"))
            for _, r in df.iterrows():
                title = str(r.get("公告标题", "")).strip()
                t = _parse(r.get("公告时间"))
                if t is None or t < start or not any(k in title for k in MAJOR_KW):
                    continue
                url = ("http://www.cninfo.com.cn/new/disclosure/detail?"
                       f"stockCode={co['code']}&announcementId={r.get('announcementId','')}"
                       f"&orgId={r.get('orgId','')}&announcementTime={t:%Y-%m-%d}")
                items.append(mk_item(co, title, t, url, "巨潮公告", "公告"))
        except Exception as e:
            errs.append(f"cninfo {co['name']}: {e}")
    # 外媒
    try:
        import feedparser, urllib.parse
        s_utc = dt.datetime.now(UTC) - dt.timedelta(hours=KEEP_HOURS)
        for co in COMPANIES:
            if not co["en"]:
                continue
            try:
                q = urllib.parse.quote(co["en"])
                feed = feedparser.parse(
                    f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")
                for e in feed.entries[:12]:
                    tp = getattr(e, "published_parsed", None)
                    if not tp:
                        continue
                    t = dt.datetime(*tp[:6], tzinfo=UTC)
                    if t < s_utc:
                        continue
                    title = getattr(e, "title", "").strip()
                    src = ""
                    if getattr(e, "source", None) and getattr(e.source, "title", None):
                        src = e.source.title
                    elif " - " in title:
                        title, src = title.rsplit(" - ", 1)
                    items.append(mk_item(co, title.strip(), t,
                                         getattr(e, "link", ""), src or "外媒", "外媒"))
            except Exception as e:
                errs.append(f"gnews {co['name']}: {e}")
    except ImportError:
        errs.append("feedparser 未安装, 跳过外媒")
    return items, errs

# ── 合并 / 落盘 ─────────────────────────────────────────────────────────────
# ── 阿里云 OSS(香港桶): 数据既从这里读, 也写回这里 ──────────────────────────
def _bucket():
    """有 OSS 环境变量才启用; 没有就退回本地文件(便于本地调试)。"""
    kid = os.getenv("OSS_KEY_ID")
    if not kid:
        return None
    import oss2
    auth = oss2.Auth(kid, os.environ["OSS_KEY_SECRET"])
    ep = os.getenv("OSS_ENDPOINT", "oss-cn-hongkong.aliyuncs.com")
    return oss2.Bucket(auth, "https://" + ep, os.environ["OSS_BUCKET"])

def load_data():
    b = _bucket()
    if b is not None:
        try:
            return json.loads(b.get_object("data.json").read())
        except Exception as e:
            print("[info] OSS 上还没有 data.json(首次运行属正常):", e)
    try:
        with open(DATA, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": [], "updated_fast": "", "updated_slow": ""}

def save(data):
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(DATA, "w", encoding="utf-8") as f:
        f.write(body)
    b = _bucket()
    if b is None:
        print("[info] 未配置 OSS, 只写了本地文件")
        return
    # data.json 必须不缓存, 否则记者刷新还是旧数据
    b.put_object("data.json", body.encode("utf-8"), headers={
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-cache, max-age=0"})
    # index.html 顺带同步(改了页面不用手动传)
    try:
        with open("docs/index.html", "rb") as f:
            b.put_object("index.html", f.read(), headers={
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "max-age=300"})
    except FileNotFoundError:
        pass
    print("[oss] 已上传 data.json + index.html")

def _t(v):
    try:
        return dt.datetime.fromisoformat(str(v))
    except Exception:
        return dt.datetime(1970, 1, 1, tzinfo=UTC)

def merge(old_items, new_items):
    by_id = {i["id"]: i for i in old_items}
    added = 0
    for it in new_items:
        if it["id"] not in by_id:
            by_id[it["id"]] = it
            added += 1
    cutoff = dt.datetime.now(UTC) - dt.timedelta(hours=KEEP_HOURS)
    keep = [i for i in by_id.values() if _t(i["time"]) >= cutoff]
    keep.sort(key=lambda i: _t(i["time"]), reverse=True)
    return keep[:MAX_ITEMS], added

def run(mode):
    data = load_data()
    if mode == "slow":
        new, errs = collect_slow()
    else:
        new, errs = collect_fast()
    items, added = merge(data.get("items", []), new)
    now = dt.datetime.now(UTC).isoformat()
    data["items"] = items
    data["updated_" + mode] = now
    data["updated_at"] = now
    data["errors"] = errs[:20]
    data["companies_total"] = len(COMPANIES)
    save(data)
    print(f"[{mode}] 抓到 {len(new)} 条, 新增 {added} 条, 现存 {len(items)} 条, 告警 {len(errs)}")
    for e in errs[:5]:
        print("   warn:", e)

def selftest():
    now = dt.datetime.now(CN)
    co = COMPANIES[0]
    fake = [mk_item(co, "DeepSeek 完成新一轮融资", now - dt.timedelta(minutes=10),
                    "https://x", "财联社", "快讯"),
            mk_item(co, "DeepSeek 完成新一轮融资", now - dt.timedelta(minutes=10),
                    "https://x", "财联社", "快讯"),
            mk_item(COMPANIES[-1], "Salesforce beats estimates", now - dt.timedelta(hours=60),
                    "https://y", "Reuters", "外媒")]
    items, added = merge([], fake)
    assert added == 2, f"去重失败 added={added}"
    assert len(items) == 1, f"48h 裁剪失败 剩 {len(items)}"
    names = {c["name"] for c in COMPANIES}
    assert len(names) == len(COMPANIES), "公司名有重复"
    print(f"[selftest] OK — 公司 {len(COMPANIES)} 家 "
          f"(国内 {sum(1 for c in COMPANIES if c['group']=='国内')}, "
          f"国外 {sum(1 for c in COMPANIES if c['group']=='国外')}); "
          "去重 / 48h裁剪 / 唯一性 均通过")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); sys.exit(0)
    m = os.getenv("MODE", "fast").lower()
    run("slow" if m == "slow" else "fast")
