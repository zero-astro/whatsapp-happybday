# WhatsApp HappyBDay Skill 🎉

Automatically detect birthday and congratulatory messages in WhatsApp groups and send personalized congratulations.

## Overview

This skill monitors WhatsApp groups for congratulatory messages using intelligent keyword scoring, identifies who is being celebrated, and automatically sends a warm, customizable greeting. Perfect for keeping track of birthdays and special moments in busy group chats!

## Features

- **🎯 Smart Detection**: Score-based NLP system distinguishes real celebrations from casual mentions
- **👥 Dynamic Group Monitoring**: Automatically discovers active WhatsApp groups (no hardcoding needed)
- **🌍 Language Agnostic**: Customize dictionaries for any language or culture
- **⚡ Zero False Positives**: Multi-factor validation prevents accidental congratulations
- **📝 State Tracking**: Remembers who's been congratulated to avoid duplicates
- **🧪 Safe Simulation Mode**: Test before going live

## How It Works

1. **Sync**: Pulls recent messages from all WhatsApp groups via `wacli`
2. **Score**: Analyzes each message with weighted keywords (e.g., "birthday" = +40pts, "family" = -50pts)
3. **Identify**: Extracts names using regex and dictionary filtering
4. **Validate**: Confirms threshold scores and minimum message counts
5. **Celebrate**: Sends a random congratulatory message with emojis

## Installation

### Prerequisites

- Python 3.x
- `wacli` skill configured and working
- OpenClaw CLI installed

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (create `.env` file):
```bash
# Names to skip (your own, close family, etc.)
BIRTHDAY_SKIP_LIST="John,Jane,Alice"

# Minimum messages mentioning name before triggering
BIRTHDAY_MIN_MESSAGES=3

# Confidence threshold score
BIRTHDAY_CONFIDENCE_THRESHOLD=120

# Simulation mode (true=dry-run, false=send real messages)
BIRTHDAY_SIMULATE=true
```

3. Customize dictionaries (optional):
   - `scoring_words.json` - Define keywords and point values
   - `messages.json` - Set your congratulatory message templates

## Usage

### Manual Test
```bash
python3 scripts/whatsapp_happybday.py --simulate
```

### Automated Monitoring

Add to your workspace's `HEARTBEAT.md`:

```markdown
## WhatsApp Birthday Monitor

- **Time Window**: 08:00-20:00 local time only
- **Action**: Run `wacli sync --once`, then execute the happybday script
- **Silence Rule**: If no congratulations sent and no errors, respond ONLY with `HEARTBEAT_OK`
```

Set up a cron job to run hourly:

```bash
openclaw cron add \
  --name "WhatsApp HappyBDay Monitor" \
  --cron "0 * * * *" \
  --message "Run python3 ~/.openclaw/skills/whatsapp-happybday/scripts/whatsapp_happybday.py. Report any congratulations sent or errors encountered."
```

## Configuration Files

### `scoring_words.json`
Define which words trigger positive/negative scores:
```json
{
  "birthday": {"words": ["birthday", "years", "candle"], "points": 40},
  "general": {"words": ["congrats", "celebrate", "party"], "points": 15},
  "negative": {"words": ["family", "work", "job"], "points": -50}
}
```

### `messages.json`
Customize congratulatory messages:
```json
{
  "greetings": ["Happy birthday, {name}!", "Congrats {name}!!"],
  "wishes": ["Have a great day!", "Wishing you the best!"],
  "emojis": ["🎉", "🎂", "🥳"]
}
```

## State Management

The skill maintains `data/name_counter.json` to track:
- Processed message IDs (prevents reprocessing)
- Accumulated scores per detected name
- Message counts per person
- List of people congratulated today

Data older than 7 days is automatically purged.

## Safety Features

- ✅ **Simulation Mode**: Test without sending real messages
- ✅ **Skip Lists**: Exclude specific names from monitoring
- ✅ **Rate Limiting**: One message per person per day
- ✅ **Threshold Validation**: Requires multiple signals before acting

## Troubleshooting

### No messages detected?
- Ensure `wacli sync` has been run recently
- Check that groups have recent activity
- Verify `BIRTHDAY_MIN_MESSAGES` threshold isn't too high

### False positives?
- Increase `BIRTHDAY_CONFIDENCE_THRESHOLD`
- Add more negative keywords to `scoring_words.json`
- Expand `BIRTHDAY_SKIP_LIST`

### Messages not sending?
- Set `BIRTHDAY_SIMULATE=false` (carefully!)
- Check wacli connection status
- Verify WhatsApp is properly authenticated

## Contributing

Feel free to submit PRs with:
- New language dictionaries
- Additional scoring keywords
- Bug fixes or performance improvements

## License

MIT License - See LICENSE file

---

**Built with ❤️ for busy WhatsApp groups everywhere**
