# TCG Price Bot (Pokémon + One Piece)

Telegram bot that checks card prices from:

1. **PriceCharting** – English & Japanese raw
2. **eBay** – Last sold by condition (Mint → Damaged) + average of last 10 sales
3. **SNKRDUNK** – Japanese raw grades A / B / C / D

When a search returns multiple cards, the bot shows each card **with its photo** so you can confirm it is the correct one.

---

## Deploy on Render Free + Uptime Monitor (Recommended)

This setup uses Render’s **free Web Service** and an external uptime monitor so the bot stays awake.

### 1. Create Telegram Bot

1. Talk to **@BotFather** on Telegram
2. Send `/newbot` and follow the steps
3. Copy the token it gives you

### 2. Put code on GitHub

Upload the entire `tcg_price_bot` folder to a new GitHub repository.

### 3. Create Free Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com) → **New +** → **Web Service**
2. Connect your GitHub repository
3. Use these settings:

| Setting         | Value                              |
|-----------------|------------------------------------|
| Name            | `tcg-price-bot`                    |
| Runtime         | Python 3                           |
| Build Command   | `pip install -r requirements.txt`  |
| Start Command   | `python bot.py`                    |
| Instance Type   | **Free**                           |

4. Add Environment Variable:
   - Key: `TELEGRAM_BOT_TOKEN`
   - Value: your token from @BotFather

5. Click **Create Web Service**

After deploy finishes, Render will give you a URL like:  
`https://tcg-price-bot-xxxx.onrender.com`

### 4. Keep it awake with a free uptime monitor

Render free services sleep after ~15 minutes of no traffic.  
We added a health endpoint (`/` and `/health`) so an uptime service can ping it.

**Recommended free monitors:**

- [UptimeRobot](https://uptimerobot.com) (easiest)
- [Better Stack](https://betterstack.com)
- [cron-job.org](https://cron-job.org)

**UptimeRobot setup (example):**

1. Create free account on UptimeRobot
2. Add New Monitor
3. Monitor Type: **HTTP(s)**
4. URL: `https://your-render-url.onrender.com/health`
5. Monitoring Interval: **5 minutes**
6. Save

That’s it. The monitor will ping your bot every 5 minutes and keep the free Render service awake.

---

## How it works

- The bot runs Telegram long-polling as usual
- At the same time it starts a tiny HTTP server on the port Render provides
- When the uptime monitor hits `/` or `/health`, Render sees traffic and does not put the service to sleep

---

## Current status of price sources

Right now the three sources return realistic **mock data** so you can test the full flow immediately.

| Source        | Status | Next step                          |
|---------------|--------|------------------------------------|
| PriceCharting | Mock   | Real API / scraper                 |
| eBay last sold| Mock   | Sold-listings API                  |
| SNKRDUNK      | Mock   | ReefAPI or scraper                 |

---

## Project structure

```
tcg_price_bot/
├── bot.py                  # Telegram + health server
├── config.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── .env.example
├── providers/
│   ├── base.py
│   ├── pricecharting.py
│   ├── ebay.py
│   └── snkrdunk.py
└── utils/
    ├── search.py
    └── currency.py
```

---

## Next steps

Tell me when the bot is online and we can start connecting the real price sources (PriceCharting, eBay, SNKRDUNK).
