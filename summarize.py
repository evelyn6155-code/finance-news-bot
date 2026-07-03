"""
筛选 + 改写模块：把抓到的原始英文新闻，交给 DeepSeek 按财经简报标准
筛出“影响国内外资本市场的宏观大事”，并改写成中文简报。

DeepSeek 接口与 OpenAI 兼容，用 openai 库调用。
编辑标准写在下面的 SYSTEM_PROMPT 里，你可以按自己的口味随时改。
"""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import config

# ----------------------------------------------------------------------
# 编辑标准：这段决定输出质量，是整个系统的核心。按需修改。
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """你是一名资深财经新闻编辑，为专业读者制作定时市场简报。

【任务】从我提供的一批原始新闻里，筛选出真正“影响国内外资本市场的宏观大事”，
改写成中文简报。宁缺毋滥：只保留有市场影响力的宏观级事件，剔除个股八卦、软文、重复报道。

【筛选优先级（从高到低）】
1. 货币政策与央行动向（美联储/欧央行/人行/日银的利率、表态、官员讲话）
2. 重大经济数据（CPI、非农、GDP、PMI 等）及其超预期程度
3. 地缘政治与突发事件对市场的冲击（战争、制裁、能源、大宗）
4. 主要指数/汇率/大宗商品/国债收益率的显著异动
5. 影响整条产业链的重磅公司事件（如龙头财报、监管、并购）

【改写标准】
- 严格忠于原文的数据与因果，不臆测、不添油加醋；数据不确定就不写。
- 中性通讯社笔法（以路透/彭博中文为基准），不带个人观点。
- 用中文母语的句式，不要翻译腔；完整的主谓宾句子。
- 冲突/影响前置：先说“发生了什么、对市场意味着什么”。
- 含具体数字（幅度、点位、百分比）。
- 不使用破折号。段落之间有逻辑衔接。
- 每条简报：一句加粗要点标题 + 2~3 句正文。

【原文链接（重要）】每条简报正文之后，另起一行附上该条所依据的那条原始新闻的链接，
格式为：`原文：<链接>`。链接必须从我给你的候选列表里【逐字照抄】，严禁自行编造或改动。
若一条简报综合了多条新闻，选其中最核心的那条的链接。若找不到对应链接，就写 `原文：（无）`。

【输出格式】直接输出 Markdown，不要任何前言或解释。若没有任何够格的宏观大事，
只输出一行：`本时段无重大宏观事件。`

格式示例：
**美联储主席暗示年内或再降息一次，美股应声走高**
鲍威尔在...表示...。市场解读为...，标普500 收涨 X%，10 年期美债收益率降至 X%。
原文：https://example.com/fed-news

（各条之间空一行。总条数控制在 3~6 条以内。）
"""


def _build_user_message(items: list[dict], slot_label: str) -> str:
    now_local = datetime.now(ZoneInfo(config.LOCAL_TZ)).strftime("%Y-%m-%d %H:%M")
    lines = [
        f"当前北京时间：{now_local}",
        f"本时段：{slot_label}",
        f"以下是候选原始新闻（共 {len(items)} 条），请据此制作简报：",
        "",
    ]
    for i, it in enumerate(items, 1):
        t = ""
        if it["published"]:
            t = it["published"].astimezone(ZoneInfo(config.LOCAL_TZ)).strftime("%m-%d %H:%M")
        lines.append(f"[{i}] ({it['source']} {t}) {it['title']}")
        if it["summary"]:
            lines.append(f"    {it['summary'][:400]}")
        if it.get("link"):
            lines.append(f"    链接：{it['link']}")
    return "\n".join(lines)


def summarize(items: list[dict], slot_label: str) -> str:
    """调用 DeepSeek，返回改写好的中文简报（Markdown）。"""
    if not items:
        return "本时段无抓取到新闻（可能是所有源都失效了，请跑 --verify 检查）。"

    from openai import OpenAI  # 懒加载：--verify 时无需安装 SDK

    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(items, slot_label)},
        ],
        temperature=0.3,   # 低温度：更稳、更贴原文，少发挥
        max_tokens=2000,
    )
    return (resp.choices[0].message.content or "").strip()
