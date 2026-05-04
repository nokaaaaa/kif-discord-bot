# Kishin Discord Bot

Discord に `go` と投稿すると、Shogi Wars の履歴ページから一番上にある Kishin Analytics ボタンを探し、棋譜を取り出して lishogi に読み込ませる bot です。

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
USER_ID=...
LISHOGI_USERNAME=...
LISHOGI_PASSWORD=...
```
