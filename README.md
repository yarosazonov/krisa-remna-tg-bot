# Krisa tg bot for Remnawave

Telegram bot for managing VPN subscriptions via **Remnawave Panel**.

## ✨ Features

- **Panel sync** - Sync bot database with Remnawave panel
- **Trial activation** - One-time trial for new users
- **Status check** - View current subscription details
- **Payment service integration** - YooKassa
- **Webhook integration** - Receives panel & payment webhooks
- **Referral system** - Invite friends and earn balance for their purchases

## 📂 Directory Structure

```
krisa-remna-tg-bot/
├── app/                # FastAPI app entrypoint
├── bot/
│   ├── handlers/       # Telegram command & callback handlers
│   ├── keyboards/      # Inline keyboard layouts
│   ├── middlewares/    # Middlewares
│   └── services/       # Remnawave API & payment services
├── config/             # Pydantic settings & logging configuration
├── db/                 # SQLite database setup
└── helpers/            # Utils
```

## 🛠️ Stack

- **Bot Framework**: aiogram 3.x
- **Web Server**: FastAPI + uvicorn
- **Database**: SQLite (SQLAlchemy + aiosqlite)
- **Payments**: YooKassa
- **Containerization**: Docker

## 🚀 Getting Started

### Setup

1. **Environment Variables**
   ```bash
   cp .env.template .env
   nano .env  # Fill in necessary variables
   ```

2. **Deploy**
   ```bash
   docker compose up -d --build
   ```
   