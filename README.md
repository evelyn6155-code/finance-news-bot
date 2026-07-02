# 财经定时简报机器人（邮件 + DeepSeek）

每天四个时段自动抓取影响国内外资本市场的宏观新闻，用 DeepSeek 筛选改写成中文简报，发到你的邮箱。

- 🌅 07:00 前：隔夜要闻（含美股收盘）
- 🕛 12:00 前：上午要闻（亚洲早盘）
- 🕟 16:30 前：午后要闻（A股收盘）
- 🌆 21:00 前：傍晚要闻（欧洲盘 + 美股盘前）

---

## 一、准备三样东西

### 1. DeepSeek API Key
1. 电脑浏览器登录 https://platform.deepseek.com ，注册/登录。
2. 左侧「API keys」→「创建 API key」，起个名字，**创建后立刻复制**那串 sk- 开头的 key
   （只显示这一次，关掉就看不到了，丢了就重建一个）。
3. 到「充值」看下余额。新用户是否赠额度不确定，若余额为 0 需要先充一点
   （这类改写任务很便宜，几块钱能用很久）。
简报任务每次成本很低（一天四次，花费很小）。

### 2. 邮箱 SMTP 授权码
脚本用你现有邮箱把简报发给你自己。你需要开启 SMTP 服务并拿一个「授权码」
（不是邮箱登录密码）。以 QQ 邮箱为例（163、Gmail 同理，服务器地址不同）：

**QQ 邮箱：**
1. 电脑登录 mail.qq.com → 顶部「设置」→「账号」（或「账户」）。
2. 找到「POP3/IMAP/SMTP…服务」，开启「IMAP/SMTP 服务」，按提示发短信验证。
3. 验证后会给你一串 **授权码**，复制保存好。这串就是 `SMTP_PASSWORD`。
   - 服务器 `smtp.qq.com`，端口 `465`。

**163 邮箱：** 设置里开启「POP3/SMTP/IMAP」，拿「客户端授权密码」；
服务器 `smtp.163.com`，端口 `465`。

**Gmail：** 需先开启两步验证，再生成「应用专用密码」（App Password）；
服务器 `smtp.gmail.com`，端口 `465` 或 `587`。
（Gmail 在国内本地测试可能连不上，但脚本跑在 GitHub 海外服务器上没问题。）

> 各家邮箱设置页的菜单文字可能随版本略有不同，认准关键词
> 「SMTP」「授权码 / 客户端授权密码」即可。
> 授权码等于密码，别外泄、别提交到公开仓库。

### 3. Python 环境（本地测试用）
Python 3.10+。

---

## 二、本地先跑通

```bash
pip install -r requirements.txt
cp .env.example .env      # 然后编辑 .env 填入你的 key

# 第一步：自检新闻源，把失效的换掉（重要！）
python main.py --verify

# 第二步：试运行，只打印不推送
python main.py --slot morning --dry

# 第三步：真发一封邮件给自己
python main.py --slot morning
```

`--verify` 会逐个测试 `config.py` 里的源，标出哪些 ❌ 失败或 ⚠️ 返回 0 条。
把这些换成可用的源再往下走。

---

## 三、部署到 GitHub Actions（免费、无需服务器）

1. 把这个文件夹推到一个 **私有** GitHub 仓库（含 `.github/workflows/schedule.yml`）。
   `.env` 不要提交（已在 .gitignore）。
2. 仓库 → **Settings → Secrets and variables → Actions → New repository secret**，
   逐个添加：
   - `DEEPSEEK_API_KEY`
   - `DEEPSEEK_MODEL`（可选，默认 deepseek-chat）
   - `DEEPSEEK_BASE_URL`（可选，默认 https://api.deepseek.com）
   - `SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`、`MAIL_TO`
3. 到 **Actions** 标签页启用工作流。可先用 **Run workflow**（workflow_dispatch）手动触发一次测试。
4. 之后就会按 `schedule.yml` 里的四个时段自动跑。

### 关于定时精度（要知道的坑）
GitHub Actions 的定时任务**不保证准点**，高峰时可能延迟 5～30 分钟甚至更多。
所以工作流里已把触发时间设在目标时间前 20 分钟。如果你要**硬准点**，
更稳的做法是租一台便宜 VPS 用系统 `cron`（见下）。

---

## 四、（可选）用 VPS + cron 替代，准点更可靠

在服务器上：
```bash
crontab -e
```
加入（服务器时区若为 UTC，用下面；若已是 CST，把小时改成 6/11/16/20）：
```
40 22 * * *  cd /path/to/finance-news-bot && /usr/bin/python3 main.py --slot morning
40 3  * * *  cd /path/to/finance-news-bot && /usr/bin/python3 main.py --slot noon
10 8  * * *  cd /path/to/finance-news-bot && /usr/bin/python3 main.py --slot afternoon
40 12 * * *  cd /path/to/finance-news-bot && /usr/bin/python3 main.py --slot evening
```

---

## 五、按需调整

- **改新闻源**：编辑 `config.py` 的 `RSS_FEEDS`。
- **改编辑标准/输出风格**：编辑 `summarize.py` 里的 `SYSTEM_PROMPT`——这是质量核心。
- **改时段/覆盖时长**：编辑 `config.py` 的 `SLOTS`。
- **换模型**：改 `DEEPSEEK_MODEL`。`deepseek-chat` 已够用；`deepseek-reasoner` 会更慢且输出思考过程，不建议。

## 已知限制（诚实说明）
- 国内实时源（财联社/金十等）多数没有稳定公开 RSS，本项目默认只覆盖国际英文源。
  国内一侧若要覆盖，通常需付费数据接口或你公司现有终端，可另做。
- RSS 源会失效，定期跑 `--verify` 检查。
