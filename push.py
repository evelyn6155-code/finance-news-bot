"""
邮件推送模块（SMTP）。
把简报转成 HTML 发到你自己的邮箱，加粗标题能正常渲染。
支持 QQ / 163 / Gmail 等，用“授权码”而不是登录密码。
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import markdown as md


def _to_html(text: str) -> str:
    """把 Markdown 简报转成带简单排版的 HTML 邮件正文。"""
    body = md.markdown(text)
    return f"""\
<html><body style="font-family:-apple-system,Helvetica,Arial,sans-serif;
line-height:1.7;color:#222;max-width:680px;margin:0 auto;padding:16px;">
{body}
<hr style="border:none;border-top:1px solid #eee;margin-top:24px;">
<p style="color:#999;font-size:12px;">本邮件由财经定时简报机器人自动发送</p>
</body></html>"""


def send_email(subject: str, text: str) -> None:
    """
    发送邮件。所有参数从环境变量读取：
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, MAIL_TO
    端口 465 走 SSL，587 走 STARTTLS。
    """
    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    mail_to = os.environ.get("MAIL_TO", user)  # 默认发给自己

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = mail_to
    msg.set_content(text)                       # 纯文本兜底
    msg.add_alternative(_to_html(text), subtype="html")  # HTML 版本

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as s:
            s.login(user, password)
            s.send_message(msg)
    else:  # 587 等
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
