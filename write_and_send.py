#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_and_send.py —— 把 report.md(采集清单)交给 DeepSeek 写成三维度中文稿, 再用 QQ 邮箱推送。
与你已有的 DeepSeek + QQ SMTP 自动化同源, 可直接替换成你现成的发信函数。

环境变量(GitHub Actions Secrets):
  DEEPSEEK_API_KEY   DeepSeek key
  QQ_USER            发件 QQ 邮箱, 如 xxx@qq.com
  QQ_AUTH            QQ 邮箱 SMTP 授权码(不是登录密码)
  MAIL_TO            收件邮箱(可逗号分隔多个)

用法:
  python write_and_send.py            # 正式: 读 report.md → DeepSeek 成稿 → 发信
  python write_and_send.py --dryrun   # 离线: 只拼 prompt 并打印, 不联网不发信
"""
import os, sys, ssl, smtplib, json, urllib.request
from email.mime.text import MIMEText
from email.header import Header

SYSTEM = "你是凤凰网财经的资深财经编辑, 文字中立、克制, 采用路透/彭博中文通讯社风格, 不用破折号, 不臆测。"

INSTRUCTION = """下面是脚本抓取到的国内AI公司动态清单(每条都带日期与来源链接)。
请据此写一份中文简报, 严格遵守:
1. 按公司分组, 每家公司在“业务动态 / 资本市场 / 外界观点”三个维度里, 有内容才写, 没有就略过该维度。
2. 只依据清单内的事实, 不补充清单外信息, 不编造数字; 每条保留其来源与链接。
3. 清单里“本期无动态”的公司, 集中成一行列出即可。
4. 结尾加一句“整体观察”(2-3句, 点出本期最值得关注的1-2条主线)。
清单如下:
---
{payload}
"""

def build_prompt(md_text):
    return INSTRUCTION.format(payload=md_text)

def call_deepseek(prompt):
    key = os.environ["DEEPSEEK_API_KEY"]
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]

def send_qq(subject, body):
    user, auth = os.environ["QQ_USER"], os.environ["QQ_AUTH"]
    to = [x.strip() for x in os.environ["MAIL_TO"].split(",") if x.strip()]
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = user
    msg["To"] = ", ".join(to)
    msg["Subject"] = Header(subject, "utf-8")
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.qq.com", 465, context=ctx) as s:
        s.login(user, auth)
        s.sendmail(user, to, msg.as_string())

def main():
    with open("report.md", encoding="utf-8") as f:
        md = f.read()
    prompt = build_prompt(md)
    if "--dryrun" in sys.argv:
        print("=== DRYRUN: 将发给 DeepSeek 的 prompt(前 1200 字) ===\n")
        print(prompt[:1200])
        print("\n=== [dryrun] 未联网、未发信。逻辑通过。 ===")
        return
    article = call_deepseek(prompt)
    import datetime
    subject = f"AI公司动态简报 {datetime.date.today():%Y-%m-%d}"
    send_qq(subject, article)
    print("[sent]", subject)

if __name__ == "__main__":
    main()
