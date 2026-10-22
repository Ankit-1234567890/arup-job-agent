import os
import time
import random
import requests # Add this at the top of your file
from datetime import datetime
from dotenv import load_dotenv
from jobspy import scrape_jobs
import pandas as pd
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load secrets from .env
load_dotenv()

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY") # We are using SendGrid now
RECIPIENT = EMAIL_ADDRESS 

# --- 1. YOUR PROFILE ---
PROFILE_KEYWORDS = [
    "support", "technical support", "application support", "it support",
    "hardware", "networking", "pos", "lan", "wan", "java", "j2ee",
    "plc", "scada", "hmi", "automation", "electrical", "switchgear",
    "ht", "lt", "testing", "commissioning", "power plant", "vcv", "sf6"
]

LOCATION = "West Bengal, India"

# --- 2. SCRAPER ---
def fetch_jobs():
    search_terms = [
        "Software Support Engineer",
        "Electrical Automation Engineer",
        "PLC SCADA Engineer"
    ]
    
    all_jobs = []
    sites = ["naukri", "indeed", "linkedin"]
    
    for term in search_terms:
        print(f"🔍 Searching for: {term}")
        for site in sites:
            try:
                # Add a random delay to prevent rate limiting
                time.sleep(random.uniform(2.0, 5.0))
                
                jobs = scrape_jobs(
                    site_name=[site],
                    search_term=term,
                    location=LOCATION,
                    results_wanted=20,
                    hours_old=72,
                    fetch_description=True
                )
                if jobs is not None and not jobs.empty:
                    all_jobs.append(jobs)
            except Exception as e:
                print(f"⚠️ Could not scrape {site} for '{term}': {e}")
                continue # If one site fails (like Naukri 406), it moves to the next
    
    if not all_jobs:
        return pd.DataFrame()
        
    combined = pd.concat(all_jobs, ignore_index=True)
    combined = combined.drop_duplicates(subset=['title', 'company'], keep='first')
    return combined

# --- 3. MATCHING & SCORING ---
def score_jobs(df):
    if df.empty:
        return df
        
    def calculate_score(row):
        text = f"{row.get('title', '')} {row.get('description', '')}".lower()
        matches = sum(1 for keyword in PROFILE_KEYWORDS if keyword in text)
        score = min(100, int((matches / 15) * 100))
        return score

    df['match_score'] = df.apply(calculate_score, axis=1)
    df = df[df['match_score'] >= 50]
    return df.sort_values(by='match_score', ascending=False)

# --- 4. EMAIL BUILDER ---
def build_email_html(df):
    if df.empty:
        return "<p>No matching jobs found today.</p>"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #1a5276;">Daily Job Matches for Arup Pal</h2>
        <p>Found <b>{len(df)}</b> roles matching your profile.</p>
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
    html += "</table></body></html>"
    return html

# --- 5. SEND EMAIL VIA SENDGRID API ---


# --- REPLACE THE SEND_EMAIL FUNCTION WITH THIS ---
def send_email(subject, body_html):
    url = "https://api.brevo.com/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "api-key": os.environ.get("BREVO_API_KEY"),
        "content-type": "application/json"
    }
    
    payload = {
        "sender": {"name": "Job Agent", "email": EMAIL_ADDRESS},
        "to": [{"email": RECIPIENT}],
        "subject": subject,
        "htmlContent": body_html
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            print(f"✅ Email sent via Brevo! Status Code: {response.status_code}")
        else:
            print(f"❌ Failed to send: {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {e}")

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
