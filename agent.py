import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

from jobspy import scrape_jobs
import pandas as pd

# Load secrets from .env
load_dotenv()

EMAIL_ADDRESS = os.environ.get("palarup1978@gmail.com")
EMAIL_PASSWORD = os.environ.get("moyc rkga fgtn rzpy")  # Gmail App Password
RECIPIENT = EMAIL_ADDRESS  # Send to yourself

# --- 1. YOUR PROFILE (edit these if your skills change) ---
PROFILE_KEYWORDS = [
    # Software Support Track
    "support", "technical support", "application support", "it support",
    "hardware", "networking", "pos", "lan", "wan", "java", "j2ee",
    # Electrical Automation Track
    "plc", "scada", "hmi", "automation", "electrical", "switchgear",
    "ht", "lt", "testing", "commissioning", "power plant", "vcv", "sf6"
]

LOCATION = "West Bengal, India"  # You can also try "Kolkata, India" or "Remote"

# --- 2. SCRAPER ---
def fetch_jobs():
    """Scrape Naukri, Indeed, and LinkedIn for matching roles."""
    search_terms = [
        "Software Support Engineer",
        "Electrical Automation Engineer",
        "PLC SCADA Engineer"
    ]
    
    all_jobs = []
    
    for term in search_terms:
        print(f"🔍 Searching for: {term}")
        try:
            jobs = scrape_jobs(
                site_name=["naukri", "indeed", "linkedin"],
                search_term=term,
                location=LOCATION,
                results_wanted=30,
                hours_old=72, # Only jobs posted in the last 3 days
                fetch_description=True # Needed for accurate matching
            )
            if jobs is not None and not jobs.empty:
                jobs['search_term'] = term
                all_jobs.append(jobs)
        except Exception as e:
            print(f"⚠️ Could not scrape for '{term}': {e}")
    
    if not all_jobs:
        return pd.DataFrame()
        
    combined = pd.concat(all_jobs, ignore_index=True)
    # Remove duplicates based on title + company
    combined = combined.drop_duplicates(subset=['title', 'company'], keep='first')
    return combined

# --- 3. MATCHING & SCORING ---
def score_jobs(df):
    """Score each job 0-100 based on keyword matches in the description."""
    if df.empty:
        return df
        
    def calculate_score(row):
        text = f"{row.get('title', '')} {row.get('description', '')}".lower()
        # Count how many of your keywords appear in the job description
        matches = sum(1 for keyword in PROFILE_KEYWORDS if keyword in text)
        # Normalize to a 0-100 scale (max 20 matches gives ~100)
        score = min(100, int((matches / 15) * 100))
        return score

    df['match_score'] = df.apply(calculate_score, axis=1)
    # Filter: keep only jobs with a score of 50 or above (adjust as needed)
    df = df[df['match_score'] >= 50]
    return df.sort_values(by='match_score', ascending=False)

# --- 4. EMAIL BUILDER ---
def build_email_html(df):
    """Create a clean HTML table for the email body."""
    if df.empty:
        return "<p>No matching jobs found today. Keep trying!</p>"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #1a5276;">Daily Job Matches for Arup Pal</h2>
        <p>Found <b>{len(df)}</b> roles matching your profile on Naukri, Indeed, and LinkedIn.</p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th>Score</th>
                <th>Title</th>
                <th>Company</th>
                <th>Source</th>
                <th>Link</th>
            </tr>
    """
    for _, row in df.iterrows():
        score_color = "#27ae60" if row['match_score'] >= 80 else "#f39c12"
        html += f"""
            <tr>
                <td style="color: {score_color}; font-weight: bold;">{row['match_score']}%</td>
                <td>{row.get('title', 'N/A')}</td>
                <td>{row.get('company', 'N/A')}</td>
                <td>{row.get('site', 'N/A').capitalize()}</td>
                <td><a href="{row.get('job_url', '#')}" style="color: #2980b9;">Apply Here</a></td>
            </tr>
        """
    html += "</table><p>Generated automatically by your AI Job Agent.</p></body></html>"
    return html

# --- 5. SEND EMAIL ---
def send_email(subject, body_html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT

    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
    print(f"✅ Email sent to {RECIPIENT}")

# --- 6. MAIN WORKFLOW ---
def main():
    print(f"🚀 Starting Job Agent at {datetime.now()}")
    raw_jobs = fetch_jobs()
    scored_jobs = score_jobs(raw_jobs)

    if scored_jobs.empty:
        print("No jobs matched the criteria today. No email sent.")
        return

    print(f"✅ Found {len(scored_jobs)} matching jobs. Sending email...")
    email_body = build_email_html(scored_jobs)
    send_email(
        subject=f"🎯 Job Matches for Arup Pal ({len(scored_jobs)} roles)",
        body_html=email_body
    )

if __name__ == "__main__":
    main()
