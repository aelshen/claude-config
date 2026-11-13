---
name: marketing
description: "One way to market every Side Quest Nexus product (arabayya, Checkpoint, PlayPatch, and the next one): community-first outreach in the owner's voice, faceless short videos from real app captures, a weekly packet the owner edits and posts, social accounts set up and tracked (driving a browser with the owner at the keyboard for passwords and codes), and one tracker of every account, post and outreach. Use when asked about marketing, outreach, social media, TikTok/Shorts/Reels, Reddit or Discord posts, Bluesky/X, university or creator outreach, making a social account, the weekly marketing packet, or what worked. Triggers on: marketing, outreach, promote, social account, TikTok, YouTube Shorts, Reels, Instagram, Bluesky, X, Reddit, subreddit, Discord, short video, launch post, weekly packet, growth."
---

# Marketing

Every product is marketed the same way: show up where its audience already gathers, as the person who built it,
with real material. Claude prepares; the owner edits and posts.

Why (owner, 2026-11-12): solo founder, marketing isn't their strength, 2 to 4 hours a week, no face on camera
(voice only if needed), and a real fear of content that reads as AI-made. Broadcasting from new accounts rarely
works for niche products; specific, useful, human posts in the right places do. The arabayya session reviewed the
plan and added the content, licensing and store rules below.

## Rules (every product)

1. **Claude never posts, comments, likes, follows or sends a message on the owner's behalf.** It drafts; the owner
   edits and sends. Setting an account up (profile, bio, avatar, links) is fine with the owner present; see
   Accounts.
2. **Real material only.** Real screen captures of the shipped app, real numbers, real stories from the work.
   No AI avatars, AI voices, stock footage, or generated images of the app. An app feature that speaks with an AI
   voice is labelled "AI voice" on screen when it is prominent, or muted.
3. **Show only what ships.** Each product's brief lists what is solid, what is early (say so) and what is not
   ready (never shown). Check every word, number and gloss on screen by hand before a clip goes out; a wrong fact in
   a niche community costs more than a missed post.
4. **Credit and license.** Never put someone else's text, footage or art on screen unless its license allows it.
   Credit it on screen in the form the license asks for. No news article bodies, no game footage, no other app's UI.
5. **Link only live stores.** The brief says which stores are live. "Coming soon" stays off until the owner has
   released it.
6. **No claims beyond what reviewers were told.** Store and API reviewers were given specific descriptions
   (data use, content sources, who it's for). Marketing copy must not contradict them. Prices are quoted exactly
   from the brief or not at all.
7. **Children's products market to parents only** (PlayPatch): never address, target or collect from children.
8. **Cost is stated first.** Making clips from existing captures is free. Any batch that needs new model calls,
   voice generation or paid tools says its estimated cost before running.
9. **The owner's voice**, not marketing voice: `references/voice.md`, including the banned AI tells. Read it before
   drafting anything.

## Where things live

| What | Where |
|---|---|
| This playbook | this skill (`references/` for voice, channels, shorts, accounts, the brief template) |
| Each product's brief | `marketing/BRIEF.md` in the product's repo, owned by that repo's session. Template: `references/brief.md` |
| Accounts, posts, outreach, results | `~/Work/marketing/` (one private folder for every product): `accounts.md`, `log.tsv`, `packets/` |
| Video and image templates | the `promo-assets` skill (vertical short template per brand) |
| Logins | the owner's password manager / Keychain. Never in a file, never in a chat, never on screen in a screenshot |

## The weekly loop (2 to 4 owner-hours)

0. **No brief yet?** A product without `marketing/BRIEF.md` gets one first: ask that repo's session to write it
   from `references/brief.md` (or draft it and send it to them to check). No packet for a product until its brief
   exists.
1. **Read** the product briefs, `~/Work/marketing/log.tsv` (what went out, what got replies) and anything the
   owner forwarded (comments, emails).
2. **Build the packet** in `~/Work/marketing/packets/<yyyy-mm-dd>.md`, per product:
   - 1 to 3 short videos (from `references/shorts.md`), rendered with `promo-assets`, each with its caption,
     hashtags, on-screen credits, and a "checked:" line listing what was verified by hand;
   - 1 to 2 community items: a helpful reply or post for a named thread or channel, within that place's rules
     (`references/channels.md`);
   - any outreach email (university, creator, wiki, newsletter), short and personal, from `references/voice.md`;
   - one build-in-public post for the Side Quest Nexus account if there's a real story that week.
   Every item is a draft the owner can post as-is or change.
3. **The owner posts**, then tells the session (or ticks the packet). The session adds a row to `log.tsv`.
4. **Follow up**: replies to answer (drafted), results a week later (views, clicks, installs if known, replies).
   Every few weeks, a short "what's working" note at the top of `log.tsv`'s companion `notes.md`: drop what
   doesn't work, do more of what does.

Start each new product with a 3-week pilot of one series and one community before adding more.

## Accounts (setup and tracking)

Read `references/accounts.md` before creating or changing any account. In short:

- One set of accounts per product (TikTok, YouTube, Instagram as needed) plus one Side Quest Nexus account on
  Bluesky (and X if the owner wants it). Each signs up with a product email alias on the owner's Fastmail, never a
  personal address.
- Claude drives the browser (Playwright) through the non-secret steps: handle availability, the sign-up form's
  name/email/birthday fields, profile, bio, avatar, links, privacy settings. **The owner types every password,
  verification code and phone number themselves**, solves any CAPTCHA, and accepts each platform's terms.
  No screenshot or snapshot of a page while a password or code is on it.
- Every account goes in `~/Work/marketing/accounts.md` (platform, handle, URL, sign-up email alias, 2FA method,
  owner-verified date, notes). No passwords, codes or recovery keys in that file.
- Automating sign-ups is against most platforms' terms. That is why the owner is at the keyboard for each one and
  Claude never creates accounts unattended, in bulk, or with fake details.

## Logging format

`~/Work/marketing/log.tsv`, one row per thing that went out or came back:

```
date	product	channel	kind	what	link	result	next
2026-11-20	arabayya	tiktok	short	"One verb, every form: كتب"	https://...	312 views, 4 saves	repeat with a Levantine verb
2026-11-21	arabayya	email	outreach	<university> Arabic program coordinator	-	replied, wants a class demo	send demo link + free-tier steps
```

`kind`: short, post, reply, outreach, account, follow-up. Keep it plain text so any session can read and append.

## Per-product state (2026-11-12)

| Product | Live | Pilot |
|---|---|---|
| arabayya | Google Play (iOS waiting for review: no App Store mentions) | 2 shorts a week + r/learnarabic replies + alma-mater email |
| Checkpoint | iOS (Play applied) | after arabayya's pilot: patch-change shorts, game communities, cited wikis and creators |
| PlayPatch | hosted beta | waits for the YouTube API review to close; parents only |

Update this table when a store state changes.
