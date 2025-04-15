# Kurikone Clan-Battle Discord Bot

A Discord bot designed to assist clans in managing their clan battles in *Princess Connect! Re:Dive*. This bot helps track boss health, player bookings, damage entries, and battle progress within a Discord server. It creates dedicated channels for each boss, provides interactive buttons for booking and submitting entries, and uses MariaDB to store battle data persistently.

It took almost same with the existing Japanese Bot 「アオイたん」 by T-niNe, I just recreate it to add some feature (especially the input validation because some peeps doing peeps things) and with English Language.
Btw this is My First (from zero) project using python (I'm your regular backend guy with C#), so point Me to right direction if My code weird as hell.

You can see my figma prototype at [here](https://www.figma.com/proto/C1qiBAUNZNNeChsM1usGzk/Discord---Purikone-CB-Bot?node-id=0-1&t=oIsnig840b2wEMJH-1)

## Features

- **Automated Channel Setup**: Creates a category and text channels for reporting and managing up to 5 bosses, plus a "TL Shifter" channel.
- **Boss Tracking**: Displays boss HP, round number, and status with embedded messages.
- **Player Interaction**:
  - Book a slot to attack a boss (Physical or Magic attack types).
  - Submit damage entries (in millions) via a modal form.
  - Mark an attack as "Done" or "Dead" to report leftover time when a boss is defeated.
  - Cancel a booking if needed.
- **Dynamic Updates**: Embeds update in real-time to reflect bookings, completed attacks, and boss HP.
- **Permission Management**: Restricts channel access to ensure only the bot can post updates, while allowing user interaction via buttons and modals.


## Prerequisites

- **Python 3.12**: Ensure you have Python 3.12 installed.
- **Discord Bot Token**: You can get the token by creating bot on [Discord Developer Portal](https://discord.com/developers/)
- **MariaDB**: A MariaDB database is required for persistent storage.
- **Dependencies**: Install required Python packages (see [Installation](#installation)).
- **Docker**: Install Docker from [docker.com](https://www.docker.com/). (If you use Docker Setup)

## Installation

### Docker Installation

1. **Install Docker** (if not already installed):
   - For Linux:
     ```bash
     curl -fsSL https://get.docker.com | sh
     sudo usermod -aG docker $USER
     ```
   - For Windows/Mac: Download Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)


2. **Set Up Environment**:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` with your configuration:
     ```bash
     nano .env  # or use your preferred text editor
     ```

3. **Run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

   Or manually with Docker:
   ```bash
   docker run -d \
     --name kurikone-bot \
     --env-file .env \
     --restart unless-stopped \
     kurisutaru/kurikone-cb-bot:latest
   ```

4. **View Logs**:
   ```bash
   docker logs -f kurikone-bot
   ```

### Manual Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Kurisutaru/kurikone-cb-bot.git
   cd kurikone-cb-bot
   ```

2. **Install Dependencies**:
   Install the required Python packages using `pip`. You’ll need `discord.py` and a MariaDB connector (e.g., `PyMySQL` or `mysql-connector-python`):
   ```bash
   pip install -r requirements.txt
   ```
   If you’re using a different MariaDB connector, adjust accordingly (e.g., `pip install mysql-connector-python`).

3. **Set Up Environment Variables**:
   - Create a `.env` file in the project root by copy and rename the `.env.example`
   - Replace `YOUR_BOT_TOKEN_HERE` with your Discord bot token from the [Discord Developer Portal](https://discord.com/developers/applications).
   - Update the `DB_*` variables with your MariaDB connection details.

4. **Run the Bot**:
   ```bash
   python -0 main.py
   ```
   
### Database Setup
The bot requires these database tables to be created:
1. Run the schema script:
   ```bash
   mysql -u your_db_user -p your_db_name < dbscript/schema.sql
   ```
2. Load master data:
   ```bash
   mysql -u your_db_user -p your_db_name < dbscript/master-data.sql
   ```
3. Load Time Zone tables:

   Read at here [MariaDB Time Zones](https://mariadb.com/kb/en/time-zones/#mysql-time-zone-tables)

## Usage

1. **Invite the Bot**: Add the bot to your Discord server using an invite link generated from the Discord Developer Portal.
2. **Channel Setup**: When the bot joins a server or starts, it automatically creates a category (e.g., "Clan Battle") and channels for reporting, bosses (Boss 1–5), and TL shifting.
3. **Interact with Bosses**: Profit ?

I suggest just read my personal handbook (free of charge) on here [アオイたん Complete BOT Tutorial](https://docs.google.com/document/d/1K51z0uQQuuUPViHRGTuhmeWVzCb7QO0gOwB72MZnKfY/edit?usp=sharing) or [just see the bot flowchart](https://i.imgur.com/JIOf1ic.png)


## Project Structure

- `main.py`: The main bot script containing the core logic, event handlers, and button/modal interactions.
- `.env`: Environment file for configuration (create this manually).
- `repository.py`: Assumed file for MariaDB repository classes (e.g., `GuildChannelRepository`, `CbBossEntryRepository`).
- `utils.py`: Assumed utility file with helper functions (e.g., `try_fetch_message`, `format_large_number`).
- `discord.log`: Log file generated by the bot for debugging.

## Contributing

Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit (`git commit -m "Add your feature"`).
4. Push to your branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.md) file for details.

## Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py).
- Uses [MariaDB](https://mariadb.org/) for persistent storage.
- Heavily inspired by **アオイたん** by T-niNe.

