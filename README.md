# Kishin Discord Bot

shogi-extend の検索結果を定期的に確認し、新しい棋譜が取れるようになったら lishogi に読み込ませて Discord にURLを投稿する bot です。

## Server Requirements

This bot uses Selenium, so the server must have a Chrome-compatible browser installed.

On Ubuntu/Debian servers, install Chromium:

```bash
sudo apt-get update
sudo apt-get install -y chromium
```

If your server uses a non-standard browser path, set it in `.env`:

```env
CHROME_BINARY=/usr/bin/chromium
```

If Selenium cannot manage the driver automatically, also install or upload a matching ChromeDriver and set:

```env
CHROMEDRIVER_PATH=/path/to/chromedriver
```

The bot also requires:

```env
DISCORD_TOKEN=...
CHANNEL_ID=...
USER_ID=...
LISHOGI_USERNAME=...
LISHOGI_PASSWORD=...
POLL_INTERVAL_SECONDS=10
LAST_KIF_HASH_PATH=.last_kif_hash
CLIPBOARD_WAIT_SECONDS=5
```
