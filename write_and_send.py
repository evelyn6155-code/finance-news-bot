#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读 report.md(国内)+ report_intl.md(外媒)→ DeepSeek 合成一封中文简报 → 邮件推送。
复用仓库已有 Secrets(SMTP_* / DEEPSEEK_*), 无需新建密钥。"""
import os, sys, ssl, smtplib, json, urllib.request
from email.mime.text import MIMEText
from email.header import Header

SYSTEM = "你是凤凰网财经的资深财经编辑, 文字中立、克制, 采用路透/彭博中文通讯社风格, 不用破折号, 不臆测。"

INSTRUCTION = """你会收到两份清单:一份国内(巨潮公告+国内快讯), 一份外媒(Google News)。
请合成一封中文简报, 分【国内】和【外媒】两大块, 严格遵守:
1. 【国内】块: 按公司分组, 每家在“业务动态/资本市场/外界观点”里有内容才写。
2. 【外媒】块: 再分“中国公司”“国外巨头”两小节, 按公司分组。
   对“外媒·中国公司”里带敏感、负面、监管、制裁、调查、安全等含义的报道, 单独用【关注】标出。
3. 只依据清单内事实, 不补充清单外信息, 不编造; 每条保留来源与链接。
4. 两份清单里“无动态/无外媒动态”的公司, 各自集中成一行列出即可。
5. 结尾一句“整体观察”(2-3句, 点出本期国内外最值得关注的主线)。

【国内清单】
---
{cn}

【外媒清单】
---
{intl}
"""

def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "(本次无该清单)"

def build_prompt():
    return INSTRUCTION.format(cn=_read("report.md"), intl=_read("report_intl.md"))

def call_deepseek(prompt):
    key = os.environ["DEEPSEEK_API_KEY"]
    base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    url = base + "/chat/completions"
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]

def send_mail(subject, body):
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASSWORD"]
    to = [x.strip() for x in os.environ["MAIL_TO"].split(",") if x.strip()]
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = user
    msg["To"] = ", ".join(to)
    msg["Subject"] = Header(subject, "utf-8")
    if port == 465:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx) as s:
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())
    else:
        with smtplib.SMTP(host, port) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(user, pwd)
            s.sendmail(user, to, msg.as_string())

def main():
    prompt = build_prompt()
    if "--dryrun" in sys.argv:
        print("=== DRYRUN ===")
        print(prompt[:1200])
        return
    article = call_deepseek(prompt)
    import datetime
    subject = f"AI公司要闻(国内+外媒) {datetime.date.today():%Y-%m-%d}"
    send_mail(subject, article)
    print("[sent]", subject)

if __name__ == "__main__":
    main()
