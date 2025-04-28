# Onager - Telegram Content Triage Bot

Onager is a Telegram bot that helps users process their read-it-later content by generating concise podcast scripts. It accepts various types of content (links, documents, text), processes them, and generates summaries that help users decide which content deserves their full attention.

## 📋 Features

- **Content Reception**: Send links, documents, or text to the bot
- **Script Generation**: Create easy-to-consume podcast scripts from your content
- **Content Management**: Keep track of what you've processed and what's in your queue
- **Multiple Content Types**: Supports web articles, YouTube videos, PDFs, and Word documents

## 🛠 Tech Stack

- Python with python-telegram-bot
- OpenRouter API for AI-powered content summarization
- JSON-based file storage (for simplicity in the MVP)

## 🚀 Setup & Deployment

### Prerequisites

- Python 3.8 or higher
- A Telegram bot token (from @BotFather)
- An OpenRouter API key (optional, as one is provided by default)

### Local Development

1. **Clone this repository**

2. **Set up a virtual environment (optional but recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Rename `.env.example` to `.env`
   - Update the `TELEGRAM_BOT_TOKEN` with your bot token
   - Optionally update the `OPENROUTER_API_KEY` with your own key

5. **Run the bot**
   ```bash
   python main.py
   ```

### Deployment on Replit

1. **Create a new Repl**
   - Go to [Replit](https://replit.com/)
   - Create a new Repl and select Python
   - Upload all the project files or sync with your GitHub repository

2. **Configure Secrets**
   - In Replit, go to the "Secrets" tab on the left sidebar
   - Add the following secrets:
     - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
     - `OPENROUTER_API_KEY`: (Optional) Your OpenRouter API key

3. **Install Dependencies**
   - Replit will automatically install the dependencies from requirements.txt
   - If needed, run `pip install -r requirements.txt` in the Replit Shell

4. **Run the Bot**
   - Click the "Run" button or configure the run command to `python main.py`

5. **Keep the Bot Running**
   - To keep your bot running 24/7 on Replit, you can:
     - Use Replit's Always On feature (requires Replit Pro)
     - Set up a service like UptimeRobot to ping your Repl regularly

### Deployment on TimeWeb

1. **Prepare your server**
   - Log in to your TimeWeb server via SSH
   - Install Python and required system dependencies:
     ```bash
     sudo apt update
     sudo apt install python3 python3-pip python3-venv
     ```

2. **Upload your project**
   - Use SFTP to upload the project files or clone from your repository:
     ```bash
     git clone <your-repository-url>
     cd onager
     ```

3. **Set up a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your actual values
   ```

5. **Run with systemd for persistence**
   - Create a systemd service file:
     ```bash
     sudo nano /etc/systemd/system/onager.service
     ```
   - Add the following content:
     ```
     [Unit]
     Description=Onager Telegram Bot
     After=network.target

     [Service]
     User=<your-username>
     WorkingDirectory=/path/to/onager
     ExecStart=/path/to/onager/venv/bin/python /path/to/onager/main.py
     Restart=always

     [Install]
     WantedBy=multi-user.target
     ```
   - Enable and start the service:
     ```bash
     sudo systemctl enable onager
     sudo systemctl start onager
     ```
   - Check status:
     ```bash
     sudo systemctl status onager
     ```

## 📱 How to Use the Bot

1. **Start the bot**
   - Search for your bot on Telegram and start a conversation
   - Send `/start` to get an introduction

2. **Add content to your queue**
   - Send links, documents, or text directly to the bot
   - The bot will confirm when it has processed each item

3. **Generate a podcast script**
   - Send `/generate` when you're ready to create a podcast script
   - The bot will process all items in your queue and send you a script

4. **Manage your queue**
   - Send `/queue` to see what's in your content queue
   - Send `/clear` to clear your queue and start fresh

## 🔜 Future Development

The next iteration of Onager will include:
- Generating audio podcasts from scripts
- Integration with read-it-later services (Pocket, Instapaper)
- Personalization based on user preferences
- Twitter integration
- Scheduled script generation

## 📄 Project Structure

- `main.py`: Main application file that runs the Telegram bot
- `content_processor.py`: Handles processing different types of content
- `script_generator.py`: Generates podcast scripts using the OpenRouter API
- `database.py`: Handles data persistence
- `.env`: Environment variables
- `requirements.txt`: Python dependencies
- `data/`: Directory for storing content data
- `temp/`: Temporary directory for downloaded files

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## 📜 License

This project is licensed under the MIT License.
