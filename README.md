# WhatsApp HappyBDay 🎉

Automated WhatsApp birthday and congratulation message sender for OpenClaw.

## What is it?
WhatsApp HappyBDay is an AI-friendly skill that dynamically monitors your active WhatsApp groups to detect when someone is being congratulated (birthdays, achievements, welcomes, etc.). It uses a score-based NLP approach and customizable dictionaries to identify the person being celebrated and automatically sends a random, natural-sounding congratulatory message on your behalf.

## What is it for?
It prevents you from missing important celebrations in busy WhatsApp groups. It runs quietly in the background (via a cron job and `wacli`), keeping track of messages and sending warm wishes exactly when appropriate, without false positives.

For detailed configuration, environment variables, and OpenClaw agent integration, please check the [SKILL.md](./SKILL.md) file.

## Contributing
Contributions, issues, and feature requests are always welcome! Feel free to open an issue or submit a pull request if you want to improve the scoring system, add new languages, or enhance the logic.

## License
This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
