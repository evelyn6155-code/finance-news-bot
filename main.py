"""
主程序。

用法：
  python main.py --verify              # 自检所有新闻源是否可用（部署前先跑）
  python main.py --slot morning        # 指定时段跑（cron 用这个）
  python main.py                       # 不指定则按当前北京时间自动判断最近的时段
  python main.py --slot noon --dry     # 试运行：只打印，不推送到 Telegram
"""
from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

import config
from fetch import fetch_all, verify_feeds
from summarize import summarize
from push import send_email

load_dotenv()  # 本地开发时从 .env 读取；GitHub Actions 用 secrets 时此行无害


def _auto_slot() -> str:
    """按当前北京时间，选最接近的一个时段。"""
    now_h = datetime.now(ZoneInfo(config.LOCAL_TZ)).hour + \
            datetime.now(ZoneInfo(config.LOCAL_TZ)).minute / 60
    # 每个时段的目标小时
    best, best_gap = None, 999
    for name, s in config.SLOTS.items():
        gap = abs(now_h - s["hour"])
        if gap < best_gap:
            best, best_gap = name, gap
    return best


def run(slot: str, dry: bool = False) -> None:
    slot_cfg = config.SLOTS[slot]
    print(f"[info] 时段={slot} 覆盖过去 {slot_cfg['lookback_hours']}h")

    items = fetch_all(slot_cfg["lookback_hours"])
    print(f"[info] 抓到候选新闻 {len(items)} 条")

    brief = summarize(items, slot_cfg["label"])

    date_str = datetime.now(ZoneInfo(config.LOCAL_TZ)).strftime('%Y-%m-%d %H:%M')
    subject = f"{slot_cfg['label']} | {date_str}"
    header = f"{slot_cfg['label']}\n{date_str} 北京时间\n\n"
    message = header + brief

    if dry:
        print("\n===== 试运行（未推送）=====\n")
        print("[主题]", subject)
        print(message)
    else:
        send_email(subject, message)
        print("[info] 已发送邮件")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--slot", choices=list(config.SLOTS.keys()),
                   help="指定时段；不填则自动判断")
    p.add_argument("--verify", action="store_true", help="自检新闻源")
    p.add_argument("--dry", action="store_true", help="试运行，不推送")
    args = p.parse_args()

    if args.verify:
        verify_feeds()
        return

    slot = args.slot or _auto_slot()
    run(slot, dry=args.dry)


if __name__ == "__main__":
    main()
