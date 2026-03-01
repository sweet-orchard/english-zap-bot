# ☁️ VPS Setup Guide (Bot Farm)

This guide explains how to set up a professional "Bot Farm" on a VPS (DigitalOcean, Hetzner, Vultr, etc.) to run multiple bots 24/7 with auto-restart.

## 1. Initial VPS Setup
After creating your VPS (Ubuntu 22.04 or 24.04 recommended):
1. **Connect via SSH**: `ssh root@your_vps_ip`
2. **Update system**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3-pip python3-venv git ufw
   ```
3. **Setup Firewall**:
   ```bash
   sudo ufw allow ssh
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

## 2. Directory Structure for Multiple Bots
Create a dedicated folder for all your bots:
```bash
mkdir -p ~/bots
cd ~/bots
```

For each bot, clone its repository (replace with your actual URLs):
```bash
# Bot 1: English Zap
git clone https://github.com/sweet-orchard/english-zap-bot.git
# Bot 2: Krishna Book
git clone https://github.com/sweet-orchard/krishna-book-bot.git
# Bot 3: Water Notifications
git clone https://github.com/sweet-orchard/water-notifications-bot.git
# Bot 4: Workout Tracker
git clone https://github.com/sweet-orchard/workout-tracker-bot.git
```

## 3. Setup Virtual Environments
For **each** bot folder, run these setup commands:
```bash
cd ~/bots/[BOT_FOLDER_NAME]
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Create your .env file manually (copy-paste from your local machine)
nano .env 
```

## 4. Persistent Services with Systemd
Create a service file for each bot in `/etc/systemd/system/`.

### Service List:
- `zap-api.service` & `zap-bot.service`
- `krishna-bot.service`
- `water-bot.service`
- `workout-bot.service`

### How to Start any Service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable [SERVICE_NAME]
sudo systemctl start [SERVICE_NAME]
```

## 5. Why this is better?
- **Stability**: If the server reboots at 3 AM, your bots come back online instantly.
- **Monitoring**: Check status with `systemctl status [SERVICE_NAME]`.
- **Logs**: View real-time logs with `journalctl -u [SERVICE_NAME] -f`.
