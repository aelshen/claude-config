#!/usr/bin/env python3
"""Morning marketing digest: what came in, what needs the owner.

Collects new items for every product in ~/Work/marketing/sources.json, keeps only what wasn't seen before,
flags what's worth a reply (product keywords, comments on our own channels, reviews), and writes
~/Work/marketing/digest/<date>.md. With --draft, asks Claude (`claude -p`) to draft replies for the
flagged items only, from the product brief and the skill's voice guide.

Collecting uses no model and no paid API. Secrets (API keys) come from the macOS Keychain
(service "marketing-digest", account named in sources.json) and are never printed.

Usage: digest.py [--draft] [--days N] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HOME = Path.home()
ROOT = Path(os.environ.get("MARKETING_HOME", HOME / "Work" / "marketing"))
SKILL = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) side-quest-marketing-digest/0.1"
ATOM = "{http://www.w3.org/2005/Atom}"
REDDIT_PAUSE_S = 12
SOURCE_ERRORS: list[str] = []  # shown at the top of the digest so a silent gap can't look like "nothing new"  # Reddit answers 429 to quick successive feed reads


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def fetch(url: str, timeout: int = 30) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except Exception as e:  # network trouble: report, keep going
        log(f"fetch failed: {url.split('?')[0]}: {type(e).__name__}")
        return 0, b""


def keychain(account: str) -> str | None:
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "marketing-digest", "-a", account, "-w"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


# --- sources -------------------------------------------------------------------------------------

def reddit_feed(url: str, label: str) -> list[dict]:
    for attempt in range(3):
        status, body = fetch(url)
        if status == 429:
            time.sleep(REDDIT_PAUSE_S * (attempt + 2))
            continue
        break
    if status != 200:
        log(f"reddit {label}: HTTP {status}")
        SOURCE_ERRORS.append(f"{label}: HTTP {status}, not checked")
        return []
    items = []
    root = ET.fromstring(body)
    for e in root.findall(f"{ATOM}entry"):
        link = e.find(f"{ATOM}link")
        items.append({
            "id": "reddit:" + (e.findtext(f"{ATOM}id") or ""),
            "source": label,
            "title": (e.findtext(f"{ATOM}title") or "").strip(),
            "text": strip_html(e.findtext(f"{ATOM}content") or "")[:1200],
            "url": link.get("href") if link is not None else "",
            "author": (e.findtext(f"{ATOM}author/{ATOM}name") or "").strip(),
            "date": e.findtext(f"{ATOM}updated") or e.findtext(f"{ATOM}published") or "",
        })
    return items


def youtube_comments(channel_id: str, key_env: str | None, key_account: str | None, label: str) -> list[dict]:
    # Infisical (via `infisical run` in the runner) puts the key in the environment; Keychain is the fallback.
    key = (os.environ.get(key_env) if key_env else None) or (keychain(key_account) if key_account else None)
    if not key:
        log(f"{label}: no key ({key_env or '-'} unset, Keychain marketing-digest/{key_account or '-'} empty)")
        SOURCE_ERRORS.append(f"{label}: no API key, comments were NOT checked")
        return []
    q = urllib.parse.urlencode({"part": "snippet,replies", "allThreadsRelatedToChannelId": channel_id,
                                "maxResults": 50, "order": "time", "key": key})
    threads, page = [], ""
    for _ in range(5):  # up to 250 threads a run; newest first
        status, body = fetch(f"https://www.googleapis.com/youtube/v3/commentThreads?{q}"
                             + (f"&pageToken={page}" if page else ""))
        if status != 200:
            msg = ""
            try:
                msg = json.loads(body).get("error", {}).get("message", "")
            except Exception:
                pass
            log(f"{label}: HTTP {status} {msg[:80]}")
            SOURCE_ERRORS.append(f"{label}: HTTP {status}, comments may be incomplete")
            break
        data = json.loads(body)
        threads += data.get("items", [])
        page = data.get("nextPageToken", "")
        if not page:
            break
    items = []
    for t in threads:
        top = t["snippet"]["topLevelComment"]["snippet"]
        replies = t.get("replies", {}).get("comments", [])
        mine = lambda c: c["snippet"].get("authorChannelId", {}).get("value") == channel_id
        if top.get("authorChannelId", {}).get("value") == channel_id:
            others = [r for r in replies if not mine(r)]
            if not others:
                continue  # our own comment, nobody answered it
            last = max(replies, key=lambda r: r["snippet"].get("publishedAt", ""))
            if mine(last):
                continue  # we already answered the latest reply
            top = others[-1]["snippet"]  # surface the viewer's reply
        latest = max([top.get("publishedAt", "")] + [r["snippet"].get("publishedAt", "") for r in replies])
        items.append({
            # thread id + latest activity: a new reply makes the thread new again
            "id": f"yt:{t['id']}:{latest}",
            "source": label,
            "title": "Comment on " + (t["snippet"].get("videoId") or "the channel"),
            "text": strip_html(top.get("textDisplay", ""))[:1200],
            "url": f"https://www.youtube.com/watch?v={t['snippet'].get('videoId','')}&lc={t['id']}",
            "author": top.get("authorDisplayName", ""),
            "date": latest,
            "replies": t["snippet"].get("totalReplyCount", 0),
            "own_channel": True,
            # answered = the newest comment in the thread is ours (only the 5 replies the API returns are seen)
            "answered": bool(replies) and mine(max(replies, key=lambda r: r["snippet"].get("publishedAt", ""))),
        })
    return items


def command_feed(cmd: str, cwd: str, label: str) -> list[dict]:
    """A product-owned command that prints JSON lines (e.g. store reviews). No secrets in its output."""
    try:
        out = subprocess.run(cmd, shell=True, cwd=os.path.expanduser(cwd), capture_output=True,
                             text=True, timeout=180)
    except Exception as e:
        log(f"{label}: {type(e).__name__}")
        return []
    if out.returncode != 0:
        log(f"{label}: exit {out.returncode}")
        SOURCE_ERRORS.append(f"{label}: failed (exit {out.returncode}), not checked")
        return []
    items = []
    for line in out.stdout.splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        items.append({
            "id": f"{label}:" + str(r.get("id")),
            "source": label,
            "title": r.get("title") or (f"{r['stars']}★ review" if r.get("stars") else "item"),
            "text": (r.get("text") or "")[:1200],
            "url": r.get("url", ""),
            "author": r.get("author", ""),
            "date": r.get("date", ""),
            "own_channel": True,
            "answered": bool(r.get("replied")),
        })
    return items


# --- flagging --------------------------------------------------------------------------------------

def flag(item: dict, keywords: list[str]) -> str | None:
    """Why this item may need the owner, or None."""
    if item.get("own_channel"):
        if item.get("answered"):
            return None
        return "on our own channel"
    hay = f"{item['title']} {item['text']}".lower()
    hits = [k for k in keywords if re.search(r"\b" + re.escape(k.lower()), hay)]
    return ("mentions: " + ", ".join(hits[:4])) if hits else None


# --- drafting ---------------------------------------------------------------------------------------

def draft_replies(product: str, flagged: list[dict], brief_path: Path | None,
                  place_rules: dict[str, str] | None = None) -> dict[str, str] | None:
    """None means drafting failed: the caller keeps the items unseen so the next run retries."""
    """One `claude -p` call per product for all its flagged items. Returns id -> draft."""
    if not flagged:
        return {}
    voice = (SKILL / "references" / "voice.md").read_text()
    brief = brief_path.read_text() if brief_path and brief_path.exists() else "(no brief)"
    place_rules = place_rules or {}
    items = [{"id": i["id"], "where": i["source"], "title": i["title"], "text": i["text"],
              "rules_there": place_rules.get(i["source"], "unknown: do not mention the product")} for i in flagged]
    prompt = f"""You draft short replies for the owner of {product}, who will edit and post them by hand.
Follow the voice guide and the product brief exactly. Only claim what the brief allows. Never pretend to be
a user. If the product is relevant, mention it once with "I made" (disclosure). If a reply would be
self-promotion where it isn't wanted, or nothing useful can be said, answer SKIP for that item.
Each item carries "rules_there": the place's own rules. They override everything: where self-promotion is
banned, never mention the product (a purely helpful reply is fine, or SKIP).

VOICE GUIDE:
{voice}

PRODUCT BRIEF:
{brief}

ITEMS (JSON):
{json.dumps(items, ensure_ascii=False, indent=1)}

Answer with JSON only: {{"<id>": "<draft reply or SKIP>", ...}}"""
    try:
        out = subprocess.run(["claude", "-p", "--model", "sonnet", "--output-format", "text"],
                             input=prompt, capture_output=True, text=True, timeout=600)
        m = re.search(r"\{.*\}", out.stdout, re.S)
        if out.returncode != 0 or not m:
            log(f"drafting failed for {product}: exit {out.returncode}")
            return None
        return json.loads(m.group(0))
    except Exception as e:
        log(f"drafting failed for {product}: {type(e).__name__}")
        return None


# --- main ---------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", action="store_true", help="draft replies for flagged items with claude -p")
    ap.add_argument("--days", type=int, default=3, help="ignore items older than this")
    ap.add_argument("--dry-run", action="store_true", help="don't update the seen list")
    args = ap.parse_args()

    cfg = json.loads((ROOT / "sources.json").read_text())
    seen_path = ROOT / "state" / "seen.json"
    seen: dict[str, str] = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    today = dt.date.today().isoformat()

    sections = []
    totals = {"new": 0, "flagged": 0}
    for product, p in cfg["products"].items():
        items: list[dict] = []
        first = True
        for sub in p.get("reddit_subs", []):
            if not first:
                time.sleep(REDDIT_PAUSE_S)
            first = False
            items += reddit_feed(f"https://www.reddit.com/r/{sub}/new/.rss", f"r/{sub}")
        for q in p.get("reddit_searches", []):
            time.sleep(REDDIT_PAUSE_S)
            items += reddit_feed("https://www.reddit.com/search.rss?" + urllib.parse.urlencode(
                {"q": q, "sort": "new", "t": "week"}), f"Reddit search “{q}”")
        for f in p.get("private_feeds", []):
            # e.g. a Reddit account's private inbox RSS; the URL holds a token, so it lives in the Keychain
            url = keychain(f["key_account"])
            if not url:
                SOURCE_ERRORS.append(f"{f['label']}: no feed URL in Keychain, NOT checked")
                continue
            for it in reddit_feed(url, f["label"]):
                it["own_channel"] = True  # replies and messages to us
                items.append(it)
        for ch in p.get("youtube_channels", []):
            items += youtube_comments(ch["id"], ch.get("key_env"), ch.get("key_account"),
                                      f"YouTube {ch.get('handle', ch['id'])}")
        for c in p.get("commands", []):
            items += command_feed(c["cmd"], c.get("cwd", "~"), c["label"])

        new = []
        for it in items:
            seen_key = f"{product}|{it['id']}"
            if seen_key in seen:
                continue
            try:
                when = dt.datetime.fromisoformat(it["date"].replace("Z", "+00:00"))
                if when.tzinfo is None:
                    when = when.replace(tzinfo=dt.timezone.utc)
                if when < cutoff:
                    continue
            except Exception:
                pass
            new.append(it)
            seen[seen_key] = today

        flagged = []
        for it in new:
            why = flag(it, p.get("keywords", []))
            if why:
                it["why"] = why
                flagged.append(it)
        drafts = draft_replies(product, flagged, Path(os.path.expanduser(p["brief"])) if p.get("brief") else None,
                               p.get("place_rules")) \
            if args.draft else {}
        if drafts is None:
            for it in flagged:  # retry these next run
                seen.pop(f"{product}|{it['id']}", None)
            drafts = {}

        totals["new"] += len(new)
        totals["flagged"] += len(flagged)
        lines = [f"## {product}", ""]
        if flagged:
            lines.append(f"### Needs you ({len(flagged)})")
            for it in flagged:
                lines += ["", f"- **{it['title'][:120]}** ({it['source']}, {it['why']})", f"  {it['url']}"]
                if it["text"]:
                    lines.append(f"  > {it['text'][:300]}")
                d = drafts.get(it["id"])
                if d and d.strip().upper() != "SKIP":
                    lines.append(f"  - Draft: {d.strip()}")
                elif d:
                    lines.append("  - Draft: skip (not worth a reply)")
        else:
            lines.append("Nothing needs you.")
        others = [it for it in new if not it.get("why")]
        if others:
            by_src: dict[str, int] = {}
            for it in others:
                by_src[it["source"]] = by_src.get(it["source"], 0) + 1
            lines += ["", "Also new, not flagged: " + ", ".join(f"{n} in {s}" for s, n in by_src.items())]
        sections.append("\n".join(lines))

    out_path = ROOT / "digest" / (f"{today}.dry-run.md" if args.dry_run else f"{today}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = f"{totals['flagged']} need you, {totals['new']} new in total."
    warn = ("\n**Sources that failed (check them by hand today):**\n" + "\n".join(f"- {e}" for e in SOURCE_ERRORS) + "\n\n") \
        if SOURCE_ERRORS else ""
    body = warn + "\n\n".join(sections) + "\n"
    if out_path.exists() and not args.dry_run:
        # A later run the same day: keep the earlier items (they're marked seen) and add this run below.
        stamp = dt.datetime.now().strftime("%H:%M")
        with out_path.open("a") as f:
            f.write(f"\n---\n\n# Later run {stamp}: {summary}\n\n" + body)
    else:
        out_path.write_text(f"# Marketing digest {today}\n\n{summary}\n" + body)
    if not args.dry_run:
        seen_path.parent.mkdir(parents=True, exist_ok=True)
        # forget ids older than 60 days
        keep = (dt.date.today() - dt.timedelta(days=60)).isoformat()
        seen_path.write_text(json.dumps({k: v for k, v in seen.items() if v >= keep}, indent=0))
    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
