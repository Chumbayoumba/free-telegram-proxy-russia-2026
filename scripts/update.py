#!/usr/bin/env python3
"""Refresh the live proxy list in README.md and the machine-readable files.

Source: https://vnespiska.win/api/proxies-ru.json — proxies that connected from a
Russian server within the last 20 minutes (the same check the @vnespiska channel
uses). Run by .github/workflows/update.yml every 2 hours.

If the source is unreachable or empty, nothing is changed: an old list is better
than an empty one.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

SRC = "https://vnespiska.win/api/proxies-ru.json"
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CHANNEL = "https://t.me/+Si9-YyVaQTU1MjAy"


def fetch() -> dict:
    req = urllib.request.Request(SRC, headers={"User-Agent": "free-telegram-proxy-russia-2026/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def host_label(server: str) -> str:
    # Long rotating hostnames break the table on phones.
    return server if len(server) <= 28 else server[:25] + "…"


def ping_label(rtt) -> str:
    if not isinstance(rtt, (int, float)):
        return "—"
    if rtt < 80:
        return f"🟢 {int(rtt)} мс"
    if rtt < 200:
        return f"🟡 {int(rtt)} мс"
    return f"🟠 {int(rtt)} мс"


def render_table(doc: dict) -> str:
    rows = [
        "| # | Сервер | Порт | Пинг из РФ | Подключить |",
        "|---|--------|------|-----------|------------|",
    ]
    for i, p in enumerate(doc["proxies"], 1):
        rows.append(
            f"| {i} | `{host_label(p['server'])}` | `{p['port']}` | {ping_label(p.get('rtt_ms'))} "
            f"| **[⚡ Подключить]({p['url']})** |"
        )
    return "\n".join(rows)


def replace_block(text: str, name: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"README has no {name} markers")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def main() -> int:
    try:
        doc = fetch()
    except Exception as exc:  # keep the old list
        print(f"source unavailable: {exc}", file=sys.stderr)
        return 0
    proxies = [p for p in doc.get("proxies", []) if p.get("server") and p.get("secret")]
    if not proxies:
        print("source returned no proxies, keeping the old list", file=sys.stderr)
        return 0
    doc["proxies"] = proxies[:10]
    stamp = doc.get("updated_msk") or doc.get("updated", "")[:16]
    n = len(doc["proxies"])

    text = README.read_text(encoding="utf-8")
    text = replace_block(text, "UPDATED",
                         f"> 🟢 **Обновлено: {stamp} МСК** · рабочих прокси: **{n}** · "
                         f"каждый проверен подключением с российского сервера")
    text = replace_block(text, "LIVE", render_table(doc))
    badge_date = stamp.split(" ")[0] if stamp else "2026"
    text = re.sub(r"https://img\.shields\.io/badge/updated-[0-9.]+-orange",
                  f"https://img.shields.io/badge/updated-{badge_date}-orange", text)
    text = re.sub(r"https://img\.shields\.io/badge/proxies_online-\d+-brightgreen",
                  f"https://img.shields.io/badge/proxies_online-{n}-brightgreen", text)
    README.write_text(text, encoding="utf-8")

    first = doc["proxies"]
    (ROOT / "proxies.txt").write_text(
        "# Free Telegram MTProto Proxy List 2026 — Russia\n"
        "# Checked from a Russian server. Format: host:port:secret\n"
        f"# Updated: {doc.get('updated', '')}\n"
        f"# Fresh proxies every hour: {CHANNEL}\n"
        + "".join(f"{p['server']}:{p['port']}:{p['secret']}\n" for p in first),
        encoding="utf-8",
    )
    (ROOT / "proxy-list.txt").write_text(
        "".join(f"{p['tg']}\n{p['url']}\n" for p in first), encoding="utf-8")
    (ROOT / "mtproto.json").write_text(json.dumps({
        "updated": doc.get("updated"),
        "country": "RU",
        "checked_from": "RU",
        "type": "mtproto",
        "price": "free",
        "source": "https://t.me/vnespiska",
        "proxies": [{
            "server": p["server"], "host": p["server"], "port": p["port"], "secret": p["secret"],
            "type": "mtproto", "country": "RU", "ping_ms": p.get("rtt_ms"), "tg_url": p["url"],
        } for p in first],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "tg.json").write_text(json.dumps([
        {"server": p["server"], "port": p["port"], "secret": p["secret"], "type": "mtproto"}
        for p in first
    ], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated: {n} proxies, {stamp} MSK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
