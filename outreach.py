import pandas as pd
import smtplib
import time
import os
import json
import re
from dotenv import load_dotenv
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

print("🚀 [INFO] Starting outreach script...")

# === LOAD .env CREDENTIALS ===
load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")

print(f"🔐 [INFO] EMAIL_USER loaded: {'✔️' if EMAIL_ADDRESS else '❌ MISSING'}")
print(f"🔐 [INFO] EMAIL_PASS loaded: {'✔️' if EMAIL_PASSWORD else '❌ MISSING'}")

# === CONFIGURATION ===
CSV_FILE = "Directory.csv"
LOG_FILE = "sent_log.json"
ERROR_LOG_FILE = "error_log.json"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
DELAY_SECONDS = 10

# === EMAIL VALIDATION ===
def is_valid_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

# === TIME WINDOW ===
def is_within_sending_window():
    now = datetime.now()
    return now.hour == 9  # Between 9:00 and 9:59 AM

def wait_until_9am():
    while True:
        now = datetime.now()
        if now.hour == 9:
            break
        print(f"⏳ Waiting for 9:00 AM... Current time: {now.strftime('%H:%M:%S')}")
        time.sleep(60)

# === LOAD SENT LOG ===
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r') as f:
        sent_log = json.load(f)
    print(f"📁 [INFO] Loaded sent log with {len(sent_log)} entries")
else:
    sent_log = {}
    print("📁 [INFO] No existing sent_log.json file. Starting fresh.")

# === LOAD CONTACTS ===
try:
    df = pd.read_csv(CSV_FILE)
    print(f"📋 [INFO] Loaded {len(df)} total rows from {CSV_FILE}")
except FileNotFoundError:
    print(f"❌ [ERROR] CSV file not found: {CSV_FILE}")
    exit(1)

df = df.drop_duplicates(subset=['School Email Address'])
df = df[df['School Email Address'].notna()]
df = df[~df['School Email Address'].isin(sent_log.keys())]

print(f"📬 [INFO] {len(df)} valid, unsent contacts to process")

# === SCALE DAILY LIMIT BASED ON PROGRESS ===
base_limit = 20
total_days = len(set([v.get("date") for v in sent_log.values() if "date" in v]))
DAILY_LIMIT = min(200, base_limit + total_days * 30)

print(f"📊 [INFO] Daily send limit based on warm-up: {DAILY_LIMIT} emails")

# === WAIT UNTIL 9AM TO START ===
wait_until_9am()

# === CONNECT TO SMTP ===
print("🌐 [INFO] Connecting to SMTP server...")
try:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    print("✅ [INFO] SMTP login successful.")
except smtplib.SMTPAuthenticationError:
    print("❌ [ERROR] SMTP authentication failed. Check your .env or GitHub Secrets.")
    exit(1)
except Exception as e:
    print(f"❌ [ERROR] SMTP connection error: {e}")
    exit(1)

# === EMAIL LOOP ===
sent_count = 0
error_log = {}

print("\n📨 [INFO] Beginning email outreach...\n")

for index, row in df.iterrows():
    now = datetime.now()
    if not is_within_sending_window():
        print("⏰ [INFO] Time window passed. Stopping email sends.")
        break
    if sent_count >= DAILY_LIMIT:
        print("✅ [INFO] Daily send limit reached.")
        break

    to_email = row['School Email Address']
    if not is_valid_email(to_email):
        print(f"⚠️ [WARN] Skipping invalid email: {to_email}")
        continue

    principal = row['School Principal'] if pd.notna(row['School Principal']) else "Principal"
    district = row['District Name']

    subject = f"HallHop – Digital Hall Pass for {district}"
    body_plain = f"""Dear {principal}, ...

(Shortened for brevity. You already have full HTML/plainbody here.)"""

    body_html = f"""<html> ... </html>"""

    msg = MIMEMultipart("alternative")
    msg['From'] = formataddr(("Varun Bhadurgatte Nagaraj", EMAIL_ADDRESS))
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.add_header("Reply-To", EMAIL_ADDRESS)
    msg.attach(MIMEText(body_plain, 'plain'))
    msg.attach(MIMEText(body_html, 'html'))

    try:
        print(f"📧 [SEND] Sending to {to_email} ... ", end='')
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        print("✅ success")
        sent_log[to_email] = {
            "principal": principal,
            "district": district,
            "subject": subject,
            "date": now.strftime("%Y-%m-%d")
        }
        sent_count += 1

        # Save after each send
        with open(LOG_FILE, 'w') as f:
            json.dump(sent_log, f, indent=2)

        time.sleep(DELAY_SECONDS)

    except smtplib.SMTPException as e:
        print(f"❌ fail: {e}")
        error_log[to_email] = str(e)

# === CLOSE SMTP ===
server.quit()

# === ERROR LOG ===
if error_log:
    with open(ERROR_LOG_FILE, 'w') as f:
        json.dump(error_log, f, indent=2)
    print(f"\n⚠️ [INFO] Some emails failed. See {ERROR_LOG_FILE} for details.")

print(f"\n🎉 [DONE] Finished. {sent_count} emails sent.")
