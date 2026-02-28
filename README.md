# 🏈 Fantasy Football Messenger Bot

A Facebook Messenger bot that lets your friend group ask natural language questions about your Yahoo Fantasy Football league — powered by Claude AI.

---

## What it does

Message the bot things like:
- "What are the current standings?"
- "Who won last week?"
- "Show me this week's matchups"
- "What does Mike's roster look like?"
- "Any recent trades or pickups?"

---

## Setup Guide (Step by Step)

### Prerequisites
- A computer with Python 3.9+ installed
- A Yahoo Fantasy Football league
- A Facebook account

---

### STEP 1 — Install Python tools

Open **Terminal** (Mac) or **Command Prompt** (Windows) and run:

```bash
pip install -r requirements.txt
```

---

### STEP 2 — Get your Yahoo API credentials

1. Go to https://developer.yahoo.com/apps/
2. Click **"Create an App"**
3. Fill in:
   - **App Name**: Fantasy Bot (or anything)
   - **Application Type**: Web Application
   - **Redirect URI**: `https://localhost:8080`
   - **API Permissions**: Check **Fantasy Sports** → Read
4. Click **Create App**
5. Copy your **Client ID** and **Client Secret** — you'll need these

**Find your League ID:**
1. Go to https://football.fantasysports.yahoo.com
2. Click your league
3. Look at the URL: `https://football.fantasysports.yahoo.com/f1/XXXXXX`
4. The number at the end is your **League ID**

**Find your Game ID:**
- NFL 2024 season = `449`
- NFL 2023 season = `423`
- Use the current season's game ID. Check https://github.com/uberfastman/yfpy for updated IDs.

---

### STEP 3 — Get your Anthropic API key

1. Go to https://console.anthropic.com
2. Sign up or log in
3. Go to **API Keys** → **Create Key**
4. Copy the key

---

### STEP 4 — Set up your .env file

Copy the template:
```bash
cp .env.example .env
```

Open `.env` in a text editor and fill in:
```
YAHOO_CLIENT_ID=<from Step 2>
YAHOO_CLIENT_SECRET=<from Step 2>
YAHOO_LEAGUE_ID=<your league ID>
YAHOO_GAME_ID=449
ANTHROPIC_API_KEY=<from Step 3>
FB_VERIFY_TOKEN=make_up_any_random_string_here
```

---

### STEP 5 — Authenticate with Yahoo (one-time)

Run this script — it will open your browser to log into Yahoo:
```bash
python get_yahoo_token.py
```

After you approve access, it will print a big JSON blob. Copy the entire thing and paste it as the value of `YAHOO_TOKEN_JSON` in your `.env` file.

---

### STEP 6 — Test locally

Make sure everything works before touching Facebook:
```bash
python test_bot.py
```

Type questions like "What are the standings?" — you should get real answers from your league!

---

### STEP 7 — Create a Facebook Page

Your bot needs a Facebook Page (not a personal profile) to send messages.

1. Go to https://www.facebook.com/pages/create
2. Choose **Business or Brand** → click **Get Started**
3. Name it something like "Fantasy League Bot" 
4. Skip all the optional steps
5. Your page is created!

**Get your Page ID:**
1. Go to your page
2. Click **About** in the left sidebar
3. Scroll to the bottom — you'll see **Page ID**
4. Add this to your `.env` as `FB_PAGE_ID`

---

### STEP 8 — Create a Meta Developer App

1. Go to https://developers.facebook.com/apps/
2. Click **Create App**
3. Select **Other** → **Next**
4. Select **Business** → **Next**  
5. Give it a name like "Fantasy Bot"
6. Click **Create App**

**Add Messenger to your app:**
1. In your app dashboard, find **Messenger** and click **Set Up**
2. Under **Access Tokens**, click **Add or Remove Pages**
3. Select your Fantasy Bot page → authorize it
4. Copy the **Page Access Token** → add to `.env` as `FB_PAGE_ACCESS_TOKEN`

**Get your App Secret:**
1. Go to **Settings** → **Basic** in the left sidebar
2. Click **Show** next to **App Secret**
3. Copy it → add to `.env` as `FB_APP_SECRET`

---

### STEP 9 — Deploy to Railway

1. Go to https://railway.app and sign up (GitHub login is easiest)
2. Click **New Project** → **Deploy from GitHub repo**
   - First time: connect your GitHub account
   - Push your code to a GitHub repo first (see below)
3. Railway will auto-detect Python and deploy!

**Push code to GitHub:**
```bash
git init
git add .
git commit -m "Initial fantasy bot"
# Create a repo at github.com, then:
git remote add origin https://github.com/YOURUSERNAME/fantasy-bot.git
git push -u origin main
```

**Add environment variables in Railway:**
1. Click your project → **Variables**
2. Add every variable from your `.env` file
3. Railway will restart your app automatically

**Get your Railway URL:**
- In Railway, click your service → **Settings** → **Domains**
- Click **Generate Domain** 
- Your URL will be like: `https://fantasy-bot-production.up.railway.app`

---

### STEP 10 — Connect Facebook Webhook

1. Go back to https://developers.facebook.com → your app → **Messenger** → **Settings**
2. Scroll to **Webhooks** → click **Add Callback URL**
3. Enter:
   - **Callback URL**: `https://your-railway-url.up.railway.app/webhook`
   - **Verify Token**: the random string you put in `FB_VERIFY_TOKEN`
4. Click **Verify and Save**
5. Under **Webhook Fields**, subscribe to: `messages`, `messaging_postbacks`
6. Under **Subscriptions**, add your page

---

### STEP 11 — Add the bot to Messenger

**Option A — DM the bot (simplest):**
- Search for your Facebook Page in Messenger
- Start chatting!

**Option B — Add to a group chat:**
1. Open or create a group chat with your league friends
2. Click the group name at the top → **Members**
3. Add your Facebook Page as a member
4. Now anyone in the group can message and the bot will reply

---

## Troubleshooting

**Bot doesn't respond:**
- Check Railway logs: click your service → **Deployments** → **View Logs**
- Make sure all env vars are set in Railway
- Verify the webhook is confirmed (green checkmark in Meta dashboard)

**Yahoo auth errors:**
- Re-run `python get_yahoo_token.py` and update `YAHOO_TOKEN_JSON` in Railway

**"Error fetching data" responses:**
- Check that your `YAHOO_LEAGUE_ID` and `YAHOO_GAME_ID` are correct

---

## Example Questions to Ask

```
What are the standings?
Who's winning this week?
Show me the scoreboard
What's last week's results?
Who's on [team name]'s roster?
Did anyone make trades recently?
How many points has [team name] scored?
Who's the last place team?
```
