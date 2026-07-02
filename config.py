"""
配置：新闻源、时段定义、筛选参数。
把不想用的源注释掉即可；跑 `python main.py --verify` 会告诉你哪些源当前是活的。
"""

# ----------------------------------------------------------------------
# 1) 新闻源（RSS）
#    这些是候选源，不保证全部长期有效——RSS 地址会失效。
#    部署前务必先跑一次自检：  python main.py --verify
#    把返回“失败/0 条”的源换成活的。
# ----------------------------------------------------------------------
RSS_FEEDS = [
    # 已在检索中确认存在的：
    {"name": "Yahoo Finance",   "url": "https://finance.yahoo.com/news/rssindex"},
    {"name": "Investing.com",   "url": "https://www.investing.com/rss/news.rss"},

    # 以下为常见但需你自检确认的候选（CNBC 经典 feed 格式）：
    {"name": "CNBC-TopNews",    "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"},
    {"name": "CNBC-Markets",    "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"},
    {"name": "CNBC-Economy",    "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"},
    {"name": "MarketWatch-Top", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},

    # 央行/官方（信噪比高，强烈建议加）：
    # 欧洲央行、美联储等官网通常提供 RSS，请自行到官网确认当前地址后填入。
    # {"name": "ECB-Press",     "url": "https://www.ecb.europa.eu/rss/press.html"},
]

# ----------------------------------------------------------------------
# 2) 时段定义（按中国标准时间 CST / UTC+8）
#    lookback_hours = 本次推送覆盖“往前多少小时”的新闻。
#    四个时段刚好对应不同市场时段：
#      morning   07:00  -> 覆盖隔夜（含美股收盘）
#      noon      12:00  -> 覆盖亚洲早盘
#      afternoon 16:30  -> 覆盖亚洲午后 + A股收盘
#      evening   21:00  -> 覆盖欧洲盘 + 美股盘前/开盘
# ----------------------------------------------------------------------
SLOTS = {
    "morning":   {"label": "🌅 隔夜要闻（美股收盘 + 全球隔夜）", "hour": 7,  "lookback_hours": 11},
    "noon":      {"label": "🕛 上午要闻（亚洲早盘）",           "hour": 12, "lookback_hours": 5},
    "afternoon": {"label": "🕟 午后要闻（A股收盘 + 亚洲午后）", "hour": 16, "lookback_hours": 5},
    "evening":   {"label": "🌆 傍晚要闻（欧洲盘 + 美股盘前）",   "hour": 21, "lookback_hours": 5},
}

# 抓取时给 lookback 再加一点冗余，避免 cron 延迟漏掉临界新闻（小时）
LOOKBACK_BUFFER_HOURS = 1

# 送进模型前，最多保留多少条候选新闻（防止 prompt 过长 / 控成本）
MAX_ITEMS_TO_MODEL = 60

# 时区（用于把 CST 时段换算、以及给模型标注时间）
LOCAL_TZ = "Asia/Shanghai"
