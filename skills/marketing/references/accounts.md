# Accounts: setting up and tracking social accounts

Claude drives the browser; the owner is at the keyboard for anything secret or legally binding.

## Before starting

1. Decide the handle. Check it's free on every platform the product needs (open each platform's sign-up or
   profile URL in the browser; note which are taken). Prefer the same handle everywhere (e.g. `arabayya.app`,
   `checkpoint.gg` style if `@arabayya` is taken). The owner picks.
2. The sign-up email: a product alias on the owner's Fastmail (e.g. `social@<product domain>` or
   `<product>@sidequest.nexus`). The owner creates the alias in Fastmail if it doesn't exist; Claude does not log
   into Fastmail.
3. The 2FA method: an authenticator app on the owner's phone (preferred) or passkey. Not SMS where avoidable.
4. Tell the owner the plan and the order (one platform at a time) and wait for "go".

## Doing it (one platform at a time)

The browser is the Playwright MCP server (`mcp__playwright__*` tools). If those tools aren't available, add it
once with `claude mcp add playwright -- npx @playwright/mcp@latest` (ask the owner first) and restart the session.

1. Open the platform's sign-up page in that browser (`mcp__playwright__browser_navigate`).
2. Fill the non-secret fields: email alias, display name, birthday (the owner's real one, or the business date the
   platform asks for; never invented), handle.
3. **Stop and hand over** for: password (the owner types it and saves it to their password manager), email or SMS
   codes, phone number, CAPTCHA, and the terms checkbox. Say exactly what's on screen and wait.
   No `browser_snapshot` or screenshot while a password or code field holds a value. After the owner says it's
   done, snapshot only to confirm the next step.
4. Profile: avatar and banner from the product brief's Assets section (a `promo-assets` brand, built-in or
   external, or the product's own brand folder); if the brief names none, ask the owner. Then the bio (from the brief, voice.md
   rules), website link (live store or product page only), category. Privacy: no contact syncing, no "find me by
   phone number", DMs from followers only where available.
5. Turn on 2FA with the owner (they scan the QR code; never screenshot it).
6. Record it in `~/Work/marketing/accounts.md` and add a `log.tsv` row (`kind: account`).
7. Close the browser tab.

## Traps seen (2026-11-13, arabayya)

- Passwords: the 1Password CLI (`op`, unlocked with Touch ID). Create the login item in the "Side Quest" vault
  with a generated password (title "<platform> - <product>", the product alias as username, the site URL, output
  to /dev/null), then copy its password field straight to the clipboard for the owner to paste.
  `~/.claude/hooks/op-guard.sh` blocks every other vault, deleting/editing/moving items, and any command that
  would print a secret (it also blocks example commands written through the shell, so edit docs with an editor).
  TikTok caps passwords at 20 characters.
- TikTok web sign-up in the automated browser hit "Maximum number of attempts reached" on Send code after one
  reload. Do TikTok from the phone app, or retry a day later.
- A new Google account on a non-Gmail alias forces phone verification, and numbers used too often are rejected.
  A product's YouTube channel runs on the Workspace account admin@sidequest.nexus instead.
- YouTube refuses handles that look like domains (`@arabayya.app`); use `_` (`@arabayya_app`).
- Instagram web: switching to Business works (category App page, hide contact info, skip Facebook); bio links
  can only be edited in the phone app.
- The home Pi-hole blocks `l.instagram.com`, which breaks Instagram OAuth hand-offs (e.g. Buffer). Take the `u=`
  parameter from the blocked URL in the network log, open it directly, and delete any file that captured it.
- Dark pages: `browser_emulate_media` with `colorScheme: light`. TikTok re-rendered and cleared its form.
- Avatar uploads only work from the Playwright MCP's allowed folder (`.playwright-mcp` in the session's working
  directory): copy the image there first.

## accounts.md format

```
| Product | Platform | Handle | URL | Sign-up email | 2FA | Set up | Notes |
|---|---|---|---|---|---|---|---|
| arabayya | TikTok | @arabayya.app | https://www.tiktok.com/@arabayya.app | social@... | authenticator | 2026-11-13 | creator account |
```

No passwords, recovery codes, backup codes or phone numbers in this file or anywhere on disk outside the owner's
password manager.

## Checking accounts (monthly, or when asked)

For each account: profile still up, bio and link still right (a store link that changed, a product that moved),
2FA still on, any platform warnings or strikes. Report in the packet; fix with the owner.

## Never

- Create accounts unattended, in bulk, with fake names or details, or to evade a ban.
- Use automation to follow, like, comment, DM or post.
- Buy followers, views or reviews, or join engagement groups.
- Log into the owner's personal accounts.
