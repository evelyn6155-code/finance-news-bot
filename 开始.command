#!/bin/bash
# 双击这个文件即可。它会：装依赖 → 帮你建配置文件 → 跑一次测试。
# 第一次双击若提示“无法打开（来自身份不明的开发者）”，
# 请右键点这个文件 → 选“打开” → 再点“打开”。

cd "$(dirname "$0")" || exit 1

echo "======================================"
echo "  财经简报机器人 · 一键脚本"
echo "======================================"
echo

# 1) 检查 python3
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ 没找到 python3。"
  echo "   请先安装：终端里输入 python3 --version 会弹出安装提示，按提示装即可。"
  echo
  read -r -p "按回车键关闭…" _
  exit 1
fi
echo "✅ 已检测到 python3"

# 2) 装依赖
echo
echo ">> 正在安装依赖（第一次会慢一点）…"
pip3 install -r requirements.txt --quiet
echo "✅ 依赖安装完成"

# 3) 处理配置文件 .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo
  echo "⚠️ 已为你创建配置文件 .env，现在需要你填写。"
  echo "   即将用文本编辑器打开它，请把里面的："
  echo "     ANTHROPIC_API_KEY（Claude 的 key）"
  echo "     SMTP_USER / SMTP_PASSWORD（你的QQ邮箱 和 授权码）"
  echo "   都改成你自己的，然后保存（Command+S）、关掉窗口，"
  echo "   再【双击一次本文件】即可。"
  echo
  open -a TextEdit .env
  read -r -p "填好并保存后，按回车键关闭本窗口…" _
  exit 0
fi
echo "✅ 已找到配置文件 .env"

# 4) 自检新闻源
echo
echo ">> 正在自检新闻源…"
python3 main.py --verify

# 5) 试运行（不发信，只打印）
echo
echo ">> 试运行（只打印，不发邮件）…"
python3 main.py --slot morning --dry

echo
echo "======================================"
echo "  如果上面能看到简报内容，说明基本跑通了。"
echo "  想真发一封到邮箱，在终端里运行："
echo "     python3 main.py --slot morning"
echo "======================================"
read -r -p "按回车键关闭…" _
