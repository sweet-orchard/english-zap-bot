# Deploying English Zap Bot to Raspberry Pi

Welcome to the Raspberry Pi deployment guide for English Zap Bot! This guide will help you (or OpenCode) configure the bot to run continuously from your flash drive.

## 1. Initial Setup

1. **Plug in the Flash Drive**: Ensure the flash drive containing `english_zap_bot_rpi.zip` is mounted on the Raspberry Pi.
2. **Extract the Archive**:
   ```bash
   unzip english_zap_bot_rpi.zip -d ~/english_zap_bot
   cd ~/english_zap_bot
   ```

## 2. Install System Dependencies

You will need Python 3, pip, python virtual environments, tmux (for background processes), and Cloudflared (for the HTTPS tunnel).

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv tmux
```

Install Cloudflared (if not already installed):
```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm.deb
sudo dpkg -i cloudflared.deb
```
*(Note: If you are on a 64-bit Pi, download `cloudflared-linux-arm64.deb` instead)*

## 3. Setup Python Environment

Create a clean virtual environment and install the required packages.

```bash
cd "english zap bot"  # Enter the inner code directory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Run the API Server and Tunnel (Background)

We will use `tmux` to keep the API server and the Cloudflare Tunnel running even after you close your SSH/terminal window.

1. Start a new tmux session:
   ```bash
   tmux new -s zap_api
   ```
2. Activate the environment and run the API:
   ```bash
   source venv/bin/activate
   ./run_api.sh
   ```
3. Press `Ctrl+b` then `d` to detach from this session.

4. Start another tmux session for the tunnel:
   ```bash
   tmux new -s zap_tunnel
   ```
5. Run the tunnel:
   ```bash
   ./run_tunnel.sh
   ```
6. **IMPORTANT**: Look at the output of the tunnel and copy the `https://....trycloudflare.com` URL.
7. Press `Ctrl+b` then `d` to detach.

## 5. Configure the Bot

1. Open the `.env` file:
   ```bash
   nano .env
   ```
2. Update the `ENGLISH_ZAP_WEBAPP_URL` variable with the Cloudflare URL you just copied. Save and exit (Ctrl+O, Enter, Ctrl+X).

## 6. Run the Main Telegram Bot (Background)

Finally, start the main bot process in the background.

1. Start a tmux session:
   ```bash
   tmux new -s zap_bot
   ```
2. Activate the environment and run the bot:
   ```bash
   source venv/bin/activate
   ./run_bot.sh
   ```
3. Press `Ctrl+b` then `d` then `d` (standard detach) to leave the session running.

## Summary of Tmux Commands

If you ever need to check the logs or restart a service, you can re-attach to the sessions:
- **List sessions**: `tmux ls`
- **Attach to API**: `tmux attach -t zap_api`
- **Attach to Tunnel**: `tmux attach -t zap_tunnel`
- **Attach to Bot**: `tmux attach -t zap_bot`
- **Detach**: `Ctrl+b` then `d`

Your English Zap Bot is now running continuously on your Raspberry Pi!

---

# 🛠 Troubleshooting (If Mini App Fails to Load)

If your Telegram Bot works but the **Mini App** (the "English Zap" button) shows a Connection Error or Blank Screen, follow these steps:

### 1. Check if the API & Tunnel are Alive
Run `tmux ls` to see your active sessions.
- If `zap_api` or `zap_tunnel` is missing, you need to restart them (see steps 4 & 6 above).

### 2. Verify the Cloudflare URL
The most common issue is an outdated or wrong URL in the `.env` file.
1. Re-attach to the tunnel: `tmux attach -t zap_tunnel`
2. **Double-check** the `https://....trycloudflare.com` address.
3. Detach (`Ctrl+b`, then `d`).
4. Check your `.env` file: `cat .env | grep WEBAPP_URL`
5. If they don't match **exactly**, edit the `.env` file (`nano .env`) and paste the correct URL.

### 3. Restart the Bot
After updating the `.env` file, the bot **must** be restarted:
```bash
tmux attach -t zap_bot
# Press Ctrl+C to stop it
./run_bot.sh
# Press Ctrl+b then d to detach
```

### 4. Check API Logs
If everything looks correct but it still fails, check the server log for errors:
```bash
cat api.log
```
Look for any "Address already in use" or "File not found" errors.
