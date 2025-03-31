# Telegram Bio Link Bot

A Telegram bot that monitors user bios for links and manages them with an approval system.

## Features

- Detects links in user bios when they join a group
- Admin approval system for bio links
- Warning system for users with unapproved links
- Auto-mute after 3 warnings
- Autoreply system for common queries
- Admin commands for managing users

## Setup

### Local Setup

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with your bot token:
   ```
   BOT_TOKEN=your_bot_token_here
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

### Deployment

#### Deploy to Render

1. Fork this repository
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Set the following environment variables:
   - `BOT_TOKEN`: Your Telegram bot token
5. Set the start command to: `python bot.py`

#### Deploy to Heroku

1. Fork this repository
2. Create a new app on Heroku
3. Connect your GitHub repository
4. Set the following environment variables:
   - `BOT_TOKEN`: Your Telegram bot token
5. Deploy the app

## Admin Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/info` - Show bot information
- `/approve <user_id>` - Approve a user's bio link (Admin only)
- `/reset_warnings <user_id>` - Reset user warnings (Admin only)

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