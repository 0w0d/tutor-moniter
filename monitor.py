#!/usr/bin/env python3
"""
1111家教網 新案件監控腳本
------------------------------------
抓取指定的家教案件搜尋結果頁，比對是否有「以前沒看過」的案件編號，
若有新案件，就透過 Discord Webhook 推播通知。

需要的環境變數（在 GitHub Actions 的 Secrets 裡設定）：
  SEARCH_URL            要監控的搜尋結果網址（可含篩選條件）
  DISCORD_WEBHOOK_URL   Discord 頻道的 Webhook 網址

狀態檔：
  seen_cases.json  記錄已經通知過的案件編號，避免重複通知。
  由 GitHub Actions 用 actions/cache 在每次執行間保留。
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATE_FILE = Path(__file__).parent / "seen_cases.json"

# 這組正則對應目前(2026-09)頁面的文字結構：
#   連絡人 王小姐 71929761 需試教! 需求科目 數學,理化 需求對象 國中二年級
#   案件薪資 500 ~ 600 應徵人數 15 上課地區 : 桃園市平鎮區 案件更新日 : 2026-09-17
CASE_PATTERN = re.compile(
    r"連絡人\s*([^\d]{1,10}?)\s*(\d{7,9})\s*(需試教!)?\s*"
    r"需求科目\s*(.+?)\s*需求對象\s*(.+?)\s*"
    r"案件薪資\s*(.+?)\s*應徵人數\s*(\d+)"
    r".*?上課地區\s*:\s*(.+?)\s*"
    r"案件更新日\s*:\s*(\d{4}-\d{2}-\d{2})",
    re.S,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_cases(url: str) -> list[dict]:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text)

    cases = []
    for m in CASE_PATTERN.finditer(text):
        contact, case_no, needs_trial, subject, target, salary, applicants, area, date = m.groups()
        cases.append(
            {
                "case_no": case_no.strip(),
                "contact": contact.strip(),
                "needs_trial": bool(needs_trial),
                "subject": subject.strip(),
                "target": target.strip(),
                "salary": salary.strip(),
                "applicants": applicants.strip(),
                "area": area.strip(),
                "date": date.strip(),
            }
        )
    return cases


def load_seen() -> set[str]:
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def save_seen(seen: set[str]) -> None:
    STATE_FILE.write_text(
        json.dumps(sorted(seen), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def send_discord(webhook_url: str, content: str) -> None:
    resp = requests.post(
        webhook_url,
        json={"content": content},
        timeout=30,
    )
    # Discord 回 204 No Content 表示成功
    if resp.status_code not in (200, 204):
        print(f"[警告] Discord 推播失敗: {resp.status_code} {resp.text}", file=sys.stderr)


def format_message(c: dict) -> str:
    trial = "（需試教）" if c["needs_trial"] else ""
    return (
        f"🆕 **新家教案件** {trial}\n"
        f"案號：{c['case_no']}\n"
        f"聯絡人：{c['contact']}\n"
        f"科目：{c['subject']}\n"
        f"對象：{c['target']}\n"
        f"薪資：{c['salary']}\n"
        f"應徵人數：{c['applicants']}\n"
        f"地區：{c['area']}\n"
        f"更新日：{c['date']}"
    )


def main() -> int:
    search_url = os.environ.get("SEARCH_URL")
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not search_url:
        print("[錯誤] 缺少環境變數 SEARCH_URL", file=sys.stderr)
        return 1
    if not webhook_url:
        print("[錯誤] 缺少 DISCORD_WEBHOOK_URL", file=sys.stderr)
        return 1

    cases = fetch_cases(search_url)
    if not cases:
        print("[警告] 這次沒有解析到任何案件，可能是網站改版或暫時性錯誤，先不更新狀態。")
        return 0

    seen = load_seen()
    is_first_run = len(seen) == 0

    new_cases = [c for c in cases if c["case_no"] not in seen]
    seen.update(c["case_no"] for c in cases)
    save_seen(seen)

    if is_first_run:
        # 第一次執行只建立基準名單，不要一次推播 56 筆舊案件
        print(f"[初始化] 已記錄 {len(cases)} 筆現有案件，之後只會通知新案件。")
        send_discord(
            webhook_url,
            f"🟢 監控已啟動，記錄了 {len(cases)} 筆現有案件作為基準，之後有新案件會通知。",
        )
        return 0

    if not new_cases:
        print("[執行完成] 沒有新案件。")
        # 除錯用：就算沒有新案件，也發一則「心跳」訊息，方便確認排程有沒有在跑。
        # 確認排程正常之後，把下面這行拿掉，改回只有新案件才通知。
        send_discord(webhook_url, "⚪ 監控正常執行中，這次沒有新案件。")
        return 0

    print(f"[執行完成] 發現 {len(new_cases)} 筆新案件，開始推播。")
    for c in new_cases:
        send_discord(webhook_url, format_message(c))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
