#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_and_send.py —— 读 report.md → DeepSeek 写三维度中文稿 → 邮件推送。
复用仓库里已有的 Secrets 命名(SMTP_* / DEEPSEEK_*), 无需新建任何密钥。
"""
import os, sys, ssl, smtplib, json, urllib.request
from email.mime.text import MIMEText
from email.header import Header

SYSTEM = "你是凤凰网财经的资深财经编辑, 文字中立、克制, 采用路透/彭博中文通讯社风格, 不用破折号, 不臆测。"

INSTRUCTION = """下面是脚本抓取到的国内AI公司要闻清单(每条都带日期与来源链接)。
请据此写一份中文简报, 严格遵守:
1. 按公司分组, 每家公司在“业务动态 / 资本市场 / 外界观点”三个维度里, 有内容才写, 没有就略过该维度。
2. 只依据清单内的事实, 不补充清单外信息, 不编造数字; 每条保留其来源与链接。
3. 清单里“本期无重大动态”的公司, 集中成一行列出即可。
4. 结尾加一句“整体观察”(2-3句, 点出本期最值得关注的1-2条主线)。
清单如下:
---
{payload}
"""

def build_prompt(md_text):
    return INSTRUCTION.format(payload=md_text)

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
    with open("report.md", encoding="utf-8") as f:
        md = f.read()
    prompt = build_prompt(md)
    if "--dryrun" in sys.argv:
        print("=== DRYRUN ===")
        print(prompt[:1000])
        return
    article = call_deepseek(prompt)
    import datetime
    subject = f"国内AI公司要闻 {datetime.date.today():%Y-%m-%d}"
    send_mail(subject, article)
    print("[sent]", subject)

if __name__ == "__main__":
    main()
