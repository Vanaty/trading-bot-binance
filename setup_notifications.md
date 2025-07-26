# Notification Setup Guide

## Prerequisites

Install Apprise:
```bash
pip install apprise
```

## Supported Services

### Telegram
1. Create a bot with @BotFather
2. Get your bot token
3. Get your chat ID
4. Format: `tgram://bot_token/chat_id`

### Discord
1. Create a webhook in your Discord server
2. Extract webhook_id and webhook_token from URL
3. Format: `discord://webhook_id/webhook_token`

### Email
1. Use your email provider settings
2. Format: `mailto://user:password@domain.com?to=recipient@domain.com`

### Slack
1. Create a Slack app and get tokens
2. Format: `slack://token_a/token_b/token_c/channel`

## Configuration

Set environment variables:
```bash
export APPRISE_SERVICES="tgram://your_bot_token/your_chat_id,discord://webhook_id/webhook_token"
export NOTIFY_ON_TRADES=true
export NOTIFY_ON_ERRORS=true
```

## Notification Types

- 📊 **Trade Signals**: When buy/sell signals are detected
- 💰 **Order Placed**: When orders are successfully placed
- ✅ **Position Closed**: When positions are closed
- ❌ **Errors**: API errors, connection issues
- ⚠️ **Warnings**: Low balance, risk management alerts
- ℹ️ **Status**: Bot startup/shutdown

## Testing

Test your notification setup:
```python
from main import send_notification
send_notification("Test", "Notification system working!", "success")
```
