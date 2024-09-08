# Maestro Bot for Molecular Momentum

Join our community: Molecular Momentum, on [Discord](https://discord.com/invite/Mtxa35wD5V) to declare your habits and start tracking, share ideas, and improve the community & Maestro together!

Maestro Bot is a Discord bot designed to help users create, track, and manage their habits in an engaging and structured way. The bot allows users to declare habits, track their progress, and receive weekly check-ins to help build consistency over time.

## Features

- **Habit Declaration:** Users can declare new habits using a structured format to ensure habits are clear and actionable.
- **Habit Tracking:** Users are grouped into tracking channels, each containing up to 8 users, where they can track their progress with weekly habit checks.
- **Automated Habit Check:** The bot sends weekly reminders to users to check whether they have completed their habits.
- **Personalized Habit Streaks:** The bot keeps track of streaks, helping users maintain their motivation by visualizing their progress.
- **Cloud Integration:** The bot periodically stores its database on cloud.
- **Admin Controls:** Admins can manually trigger habit checks.

## Setup

### Prerequisites

- Python 3.8+
- Discord.py library
- Google Drive API credentials (for database backup)
- SQLite3 for local database management

### Environment Variables

Create a `.env` file in the root directory of your project and add the necessary environment variables, including your Discord bot token, Google Drive folder ID, and Google service account JSON.

### Installation

1. Clone this repository.
2. Install the required dependencies by running the appropriate package installer (for example, pip).
3. Set up your Google Drive API by creating a service account and providing the necessary credentials in the `.env` file.
4. Run the bot using your Python interpreter.

## Commands

### User Commands

- **/declare**: Declare a new habit.
- **/habits**: View all your current habits and their details.

### Admin Commands

- **/check**: Trigger a manual habit check for all users in the tracking channels. (Admin only)

## Habit Tracking Channels

- Users are automatically placed into tracking channels containing up to 8 users.
- Each week, users receive a prompt asking whether they completed their habit.
- Progress is tracked, and habit streaks are recorded for each user.
- If a user fails to track their habits for 3 consecutive weeks, they will be removed from the tracking channel and will need to declare a new habit to restart the tracking process.

## Database Management

The bot uses an SQLite database (`discord_bot.db`) to store user information, declared habits, and progress. The database is periodically uploaded to Google Drive to ensure data is backed up regularly.

## Google Drive Integration

The bot downloads the latest version of the database from Google Drive when it starts if the local database does not exist. It also uploads the database every 10 minutes to keep a backup.

## Logging

The bot logs various events, errors, and warnings using Python's built-in logging module. Log files can help diagnose issues or understand the bot's behavior over time.

## Contributing

Feel free to open issues or submit pull requests if you would like to contribute to the project.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

