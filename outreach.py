# === CONFIGURATION ===
SEND_START_HOUR = 8
SEND_END_HOUR = 9
DELAY_BETWEEN_EMAILS = 10
MAX_EMAILS_PER_RUN = 150

CSV_FILE = "Directory.csv"
LOG_FILE = "sent_log.json"
FAILED_FILE = "failed_log.json"
ERROR_LOG_FILE = "error_log.json"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"

# === LIBRARIES ===
import pandas as pd
import smtplib
import time
import os
import json
import re
import email
import imaplib
from dotenv import load_dotenv
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

print("🚀 [INFO] Starting outreach script...")

# === HELPER FUNCTIONS ===
def is_valid_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

def format_name(name):
    name = name.strip()
    if not name:
        return "Principal"
    name_parts = name.split()
    prefix = name_parts[0].upper()
    last_name = name_parts[-1].capitalize()
    return f"{'Mr.' if prefix == 'MR' else 'Mrs.' if prefix == 'MRS' else 'Ms.' if prefix == 'MS' else 'Principal'} {last_name}"

def is_within_sending_window():
    now = datetime.now()
    return SEND_START_HOUR <= now.hour < SEND_END_HOUR

def wait_until_start_time():
    while not is_within_sending_window():
        now = datetime.now()
        print(f"⏳ Waiting until sending window ({SEND_START_HOUR}:00–{SEND_END_HOUR}:00)... Now: {now.strftime('%H:%M:%S')}")
        time.sleep(60)

def check_bounced_emails():
    bounced = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, 'SUBJECT "Delivery Status Notification"')

        for num in messages[0].split():
            _, data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode(errors="ignore")
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            matches = re.findall(r"(?i)Final-Recipient:.*?;\s*(\S+@\S+)", body)
            bounced += matches

        mail.logout()
    except Exception as e:
        print(f"⚠️ [IMAP] Error checking for bounces: {e}")
    return list(set(bounced))

def send_email(row):
    to_email = row.get("School Email Address")
    principal = format_name(row.get("School Principal", "").strip())
    school_name = row.get("School Name", "").strip().title() or "your school"
    subject = f"HallHop – Digital Hall Pass for {school_name}"

    body_plain = f"""Dear {principal},

My name is Varun, and I’m a high school junior in Round Rock and the founder of HallHop — a student-built, privacy-conscious digital hall pass system created to help schools like {school_name} modernize hallway management without needing expensive tech or complicated systems.

HallHop helps staff track hallway activity in real time, reduce disruptions, and increase student accountability — all while keeping things simple and transparent for everyone.

I truly believe tools like this can make a meaningful difference, and I’d love to share it with your campus. You can learn more or request access at https://hallhop.com, or just reply to this message — I’m always happy to answer questions personally.

Thank you so much for the work you do to support students and your school. I’d be excited for the chance to support your efforts in any way I can.

If you'd prefer not to receive future updates, just reply with "unsubscribe".

Warmly,  
Varun Bhadurgatte Nagaraj  
512-212-6269  
HallHop Founder & CEO  
Junior at Round Rock High School  
hallhop.com – making hallways safer and smarter
"""

    body_html = f"""\
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <p>Dear {principal},</p>
    <p>My name is Varun, and I’m a high school junior in Round Rock and the founder of <strong>HallHop</strong> — a student-built, privacy-conscious digital hall pass system created to help schools like <strong>{school_name}</strong> modernize hallway management without needing expensive tech or complicated systems.</p>
    <p>HallHop helps staff track hallway activity in real time, reduce disruptions, and increase student accountability — all while keeping things simple and transparent for everyone.</p>
    <p>I truly believe tools like this can make a meaningful difference, and I’d love to share it with your campus. You can learn more or request access at <a href="https://hallhop.com">hallhop.com</a>, or just reply to this message — I’m always happy to answer questions personally.</p>
    <p><em>If you'd prefer not to receive future updates, just reply with "unsubscribe".</em></p>
    <p>Warmly,<br>
      Varun Bhadurgatte Nagaraj<br>
      512-212-6269<br>
      HallHop Founder & CEO<br>
      Junior at Round Rock High School<br>
      <a href="https://hallhop.com">hallhop.com</a> – making hallways safer and smarter
    </p>
  </body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg['From'] = formataddr(("Varun Bhadurgatte Nagaraj", EMAIL_ADDRESS))
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.add_header("Reply-To", EMAIL_ADDRESS)
    msg.attach(MIMEText(body_plain, 'plain'))
    msg.attach(MIMEText(body_html, 'html'))

    try:
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        print(f"📧 [SEND] Sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ [ERROR] Failed to send to {to_email}: {e}")
        return False

# === LOAD ENV ===
load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")

print(f"🔐 EMAIL_USER loaded: {'✔️' if EMAIL_ADDRESS else '❌'}")
print(f"🔐 EMAIL_PASS loaded: {'✔️' if EMAIL_PASSWORD else '❌'}")

# === LOAD LOGS ===
sent_log = {}
failed_log = {}
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r') as f:
        sent_log = json.load(f)
if os.path.exists(FAILED_FILE):
    with open(FAILED_FILE, 'r') as f:
        failed_log = json.load(f)

# === CLEAN BOUNCES ===
bounced = check_bounced_emails()
print(f"📮 [INFO] Detected {len(bounced)} bounces")
for b in bounced:
    if b in sent_log:
        del sent_log[b]
        failed_log[b] = {"reason": "bounce"}
        print(f"🧹 [CLEAN] Removed {b} from sent_log")

with open(LOG_FILE, 'w') as f:
    json.dump(sent_log, f, indent=2)
with open(FAILED_FILE, 'w') as f:
    json.dump(failed_log, f, indent=2)

# === CONNECT SMTP ===
print("🌐 Connecting to SMTP...")
try:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    print("✅ SMTP connected.")
except Exception as e:
    print(f"❌ SMTP error: {e}")
    exit(1)

# === LOAD CSV ===
df = pd.read_csv(CSV_FILE)
df = df.drop_duplicates(subset=['School Email Address'])
df = df[df['School Email Address'].notna()]
df = df[df['School Email Address'].str.contains("@", na=False)]
df = df[~df['School Email Address'].isin(sent_log.keys())]

# === WAIT FOR SEND WINDOW ===
wait_until_start_time()

# === SEND EMAILS ===
sent_count = 0
for _, row in df.iterrows():
    if not is_within_sending_window():
        print("⏰ Time window closed.")
        break
    if sent_count >= MAX_EMAILS_PER_RUN:
        print("✅ Max email limit reached.")
        break

    email_address = row['School Email Address']
    if not is_valid_email(email_address):
        continue

    if send_email(row):
        sent_log[email_address] = {
            "school": row.get("School Name", ""),
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        sent_count += 1
    else:
        failed_log[email_address] = {"reason": "send_error"}

    with open(LOG_FILE, 'w') as f:
        json.dump(sent_log, f, indent=2)
    with open(FAILED_FILE, 'w') as f:
        json.dump(failed_log, f, indent=2)

    time.sleep(DELAY_BETWEEN_EMAILS)

# === RETRY FAILED EMAILS ===
print("\n🔁 Retrying failed emails (not counted toward limit)...")
retry_df = pd.read_csv(CSV_FILE)
retry_df = retry_df[retry_df['School Email Address'].isin(failed_log.keys())]

for _, row in retry_df.iterrows():
    email_address = row['School Email Address']
    if email_address in sent_log:
        continue

    if send_email(row):
        sent_log[email_address] = {
            "school": row.get("School Name", ""),
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        del failed_log[email_address]
        print(f"✅ Retry succeeded: {email_address}")
    else:
        print(f"❌ Retry failed: {email_address}")

    with open(LOG_FILE, 'w') as f:
        json.dump(sent_log, f, indent=2)
    with open(FAILED_FILE, 'w') as f:
        json.dump(failed_log, f, indent=2)

# === CLOSE SMTP ===
server.quit()
print(f"\n🎉 DONE: Sent {sent_count} new emails. Retried {len(retry_df)} failures.")
