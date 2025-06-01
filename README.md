# Telegram Bot with Message Control Features

A Telegram bot that manages message editing, sticker permissions, and bio link monitoring.

## Features

- Message editing control
- Sticker permission management
- Bio link monitoring
- Message deletion with reasons
- Bot owner privileges
- Copyright protection with similarity detection

## Quick Deployment on Render

1. Fork this repository
2. Go to [Render](https://render.com)
3. Sign up/Login with your GitHub account
4. Click "New +" and select "Blueprint"
5. Connect your forked repository
6. Add your `TELEGRAM_BOT_TOKEN` in the environment variables
7. Click "Apply" and wait for deployment

## Manual Deployment on Render

1. Fork this repository
2. Go to [Render](https://render.com)
3. Click "New +" and select "Worker"
4. Connect your GitHub repository
5. Configure the service:
   - Name: `telegram-bot` (or any name you prefer)
   - Environment: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
6. Add environment variable:
   - Key: `TELEGRAM_BOT_TOKEN`
   - Value: Your bot token from [@BotFather](https://t.me/BotFather)
7. Click "Create Worker"

## Environment Variables

Create a `.env` file with the following variables:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Local Development

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create `.env` file with your bot token
4. Run the bot:
```bash
python bot.py
```

## Bot Owner

The bot owner (ID: 7798461429) has full privileges:
- Can delete any message
- Can send stickers freely
- Can edit messages
- Can approve users for stickers

## Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/info` - Show bot information
- `/approve <user_id>` - Approve a user's bio link (Admin only)
- `/reset_warnings <user_id>` - Reset user warnings (Admin only)
- `/delete <reason>` - Delete a message (Admin only, reply to message)
- `/approve_sticker <user_id>` - Approve a user to send stickers (Group owner only)
- `/copyright` - Toggle copyright protection (Admin only)

## Autoreply Triggers

The bot will automatically reply to the following messages:
- "What is the rule?"
- "How can I get approved?"
- General help queries

## Note

Make sure to add the bot as an admin in your Telegram group with the following permissions:
- Delete messages
- Ban users
- Mute users

## Credits

Bot designed by 𐏓  𝅥‌꯭𝆬ᷟ𝐣‌‌‌➥‌𝗭𝗲‌𝗳𝗿𝗼‌𝗻 ‌🔥❰⎯꯭ ꭗ‌‌  🍂
Username: @crush_hu_tera 