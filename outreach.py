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

# === LOAD .env CREDENTIALS ===
load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")

# === CONFIGURATION ===
CSV_FILE = "/Users/varunbhadurgattenagaraj/Downloads/HallHop/HallHop OutReach/Directory.csv"
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
        print(f"⏳ Waiting for 8:00 AM... Current time: {now.strftime('%H:%M:%S')}")
        time.sleep(60)

# === LOAD SENT LOG ===
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r') as f:
        sent_log = json.load(f)
else:
    sent_log = {}

# === LOAD CONTACTS ===
df = pd.read_csv(CSV_FILE)
df = df.drop_duplicates(subset=['School Email Address'])
df = df[df['School Email Address'].notna()]
df = df[~df['School Email Address'].isin(sent_log.keys())]

# === SCALE DAILY LIMIT BASED ON PROGRESS ===
base_limit = 20
total_days = len(set([v.get("date") for v in sent_log.values() if "date" in v]))
DAILY_LIMIT = min(200, base_limit + total_days * 30)

print(f"📊 Sending up to {DAILY_LIMIT} emails today based on warm-up logic.")

# === WAIT UNTIL 8AM TO START ===
wait_until_9am()

# === CONNECT TO SMTP ===
try:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
except smtplib.SMTPAuthenticationError:
    print("❌ SMTP authentication failed. Check .env settings.")
    exit(1)
except Exception as e:
    print(f"❌ SMTP connection error: {e}")
    exit(1)

# === EMAIL LOOP ===
sent_count = 0
error_log = {}

for index, row in df.iterrows():
    now = datetime.now()
    if not is_within_sending_window():
        print("⏰ Time window passed. Stopping email sends.")
        break
    if sent_count >= DAILY_LIMIT:
        print("✅ Daily send limit reached.")
        break

    to_email = row['School Email Address']
    if not is_valid_email(to_email):
        print(f"⚠️ Skipping invalid email: {to_email}")
        continue

    principal = row['School Principal'] if pd.notna(row['School Principal']) else "Principal"
    district = row['District Name']

    subject = f"HallHop – Digital Hall Pass for {district}"
    body_plain = f"""Dear {principal},

My name is Varun, and I’m a high school junior in Round Rock and the founder of HallHop — a student-built, privacy-conscious digital hall pass system created to help schools like those in {district} modernize hallway management without needing expensive tech or complicated systems.

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

    <p>My name is Varun, and I’m a high school junior in Round Rock and the founder of <strong>HallHop</strong> — a student-built, privacy-conscious digital hall pass system created to help schools like those in <strong>{district}</strong> modernize hallway management without needing expensive tech or complicated systems.</p>

    <p>HallHop helps staff track hallway activity in real time, reduce disruptions, and increase student accountability — all while keeping things simple and transparent for everyone.</p>

    <p>I truly believe tools like this can make a meaningful difference, and I’d love to share it with your campus. You can learn more or request access at <a href="https://hallhop.com">hallhop.com</a>, or just reply to this message — I’m always happy to answer questions personally.</p>

    <p>Thank you so much for the work you do to support students and your school. I’d be excited for the chance to support your efforts in any way I can.</p>

    <p><em>If you'd prefer not to receive future updates, just reply with "unsubscribe".</em></p>

    <p>
      Warmly,<br>
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
        print(f"✅ Sent to {to_email}")
        sent_log[to_email] = {
            "principal": principal,
            "district": district,
            "subject": subject,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        sent_count += 1

        # Save after each send
        with open(LOG_FILE, 'w') as f:
            json.dump(sent_log, f, indent=2)

        time.sleep(DELAY_SECONDS)

    except smtplib.SMTPException as e:
        print(f"⚠️ Error sending to {to_email}: {e}")
        error_log[to_email] = str(e)

# === CLOSE SMTP ===
server.quit()

# === ERROR LOG ===
if error_log:
    with open(ERROR_LOG_FILE, 'w') as f:
        json.dump(error_log, f, indent=2)
    print(f"\n⚠️ Some emails failed. Errors logged to {ERROR_LOG_FILE}")

print(f"\n🎉 Finished. {sent_count} emails sent and logged.")
