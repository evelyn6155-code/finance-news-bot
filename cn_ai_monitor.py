# 放到仓库的 .github/workflows/cn-ai-monitor.yml
name: cn-ai-monitor

on:
  workflow_dispatch:
    inputs:
      mode:
        description: "head 或 full"
        default: "head"
  schedule:
    - cron: "30 23 * * *"

jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: pip install akshare pandas feedparser

      - name: Decide MODE
        id: m
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            echo "mode=${{ github.event.inputs.mode }}" >> $GITHUB_OUTPUT
          else
            if [ $(( $(date +%j | sed 's/^0*//') % 3 )) -eq 0 ]; then
              echo "mode=full" >> $GITHUB_OUTPUT
            else
              echo "mode=head" >> $GITHUB_OUTPUT
            fi
          fi

      - name: Collect (国内公告+快讯+行情)
        env:
          MODE: ${{ steps.m.outputs.mode }}
        run: python cn_ai_monitor.py

      - name: Collect intl (外媒 RSS)
        run: python intl_monitor.py

      - name: Write article & send mail
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          DEEPSEEK_BASE_URL: ${{ secrets.DEEPSEEK_BASE_URL }}
          DEEPSEEK_MODEL: ${{ secrets.DEEPSEEK_MODEL }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          MAIL_TO: ${{ secrets.MAIL_TO }}
        run: python write_and_send.py

      - name: Save report as artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: report-${{ steps.m.outputs.mode }}
          path: |
            report.md
            report.json
            report_intl.md
            report_intl.json
