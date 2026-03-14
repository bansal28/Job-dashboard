"""
Gmail Application Tracker
Connects to Gmail via IMAP, fetches recent emails,
classifies them using Groq LLM into application status categories.

Setup:
  1. Enable IMAP in Gmail: Settings > Forwarding and POP/IMAP > Enable IMAP
  2. Generate App Password: https://myaccount.google.com/apppasswords
     (requires 2FA enabled on your Google account)
  3. Add to scrapers/config.py:
     GMAIL_ADDRESS = "your.jobs.email@gmail.com"
     GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
"""

import imaplib
import email
import re
import json
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════
# GMAIL CONNECTION
# ═══════════════════════════════════════════════════════════

def connect_gmail(email_addr: str, app_password: str) -> imaplib.IMAP4_SSL:
    """Connect to Gmail via IMAP SSL."""
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail._encoding = "utf-8"
    mail.login(email_addr, app_password)
    return mail


def fetch_emails(email_addr: str, app_password: str, days: int = 30) -> list[dict]:
    """
    Fetch emails from the last N days.
    Returns list of {subject, sender, sender_email, date, body_preview}.
    """
    if not email_addr or not app_password:
        return []

    try:
        mail = connect_gmail(email_addr, app_password)
        mail.select("INBOX")

        since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        _, message_ids = mail.search(None, f'(SINCE "{since_date}")')

        if not message_ids[0]:
            mail.logout()
            return []

        emails = []
        ids = message_ids[0].split()

        # Fetch latest first, limit to 100 most recent
        for msg_id in reversed(ids[-100:]):
            try:
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                subject = _decode_header_value(msg["Subject"])
                sender_full = _decode_header_value(msg["From"])
                date_str = msg["Date"]

                # Extract email address from sender
                sender_email = ""
                email_match = re.search(r"<([^>]+)>", sender_full)
                if email_match:
                    sender_email = email_match.group(1).lower()
                elif "@" in sender_full:
                    sender_email = sender_full.strip().lower()

                # Extract sender name
                sender_name = re.sub(r"<[^>]+>", "", sender_full).strip().strip('"')

                # Extract body
                body = _extract_body(msg)

                # Parse date
                parsed_date = ""
                try:
                    dt = parsedate_to_datetime(date_str)
                    parsed_date = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass

                emails.append({
                    "subject": subject,
                    "sender_name": sender_name,
                    "sender_email": sender_email,
                    "date": parsed_date,
                    "body_preview": body[:1000],  # first 1000 chars for classification
                })
            except Exception as e:
                continue

        mail.logout()
        return emails

    except Exception as e:
        print(f"[Gmail] Connection error: {e}")
        raise


def _extract_body(msg) -> str:
    """Extract plain text body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except Exception:
                    pass
            elif content_type == "text/html" and not body:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    html = part.get_payload(decode=True).decode(charset, errors="replace")
                    body = re.sub(r"<[^>]+>", " ", html)
                    body = re.sub(r"\s+", " ", body).strip()
                except Exception:
                    pass
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(charset, errors="replace")
        except Exception:
            pass

    # Clean up — replace non-ASCII whitespace and control chars
    body = body.replace("\xa0", " ")
    body = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", body)
    body = re.sub(r"\r\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _decode_header_value(value: str) -> str:
    """Decode email header value safely."""
    if not value:
        return ""
    try:
        decoded_parts = decode_header(value)
        parts = []
        for content, charset in decoded_parts:
            if isinstance(content, bytes):
                parts.append(content.decode(charset or "utf-8", errors="replace"))
            else:
                parts.append(str(content))
        result = " ".join(parts)
        # Clean non-ASCII whitespace
        result = result.replace("\xa0", " ")
        return result
    except Exception:
        return str(value).replace("\xa0", " ")


# ═══════════════════════════════════════════════════════════
# LLM CLASSIFICATION
# ═══════════════════════════════════════════════════════════

def classify_emails_batch(emails: list[dict], api_key: str) -> list[dict]:
    """
    Classify a batch of emails using Groq LLM.
    Much more accurate than keyword matching.
    Processes in batches of 10 for efficiency.
    """
    import requests

    if not emails:
        return []

    results = []
    batch_size = 10

    for i in range(0, len(emails), batch_size):
        batch = emails[i:i + batch_size]
        classified = _classify_batch(batch, api_key)
        results.extend(classified)

    return results


def _classify_batch(emails: list[dict], api_key: str) -> list[dict]:
    """Classify a batch of emails with one LLM call."""
    import requests

    # Build email summaries for the prompt
    email_summaries = []
    for idx, em in enumerate(emails):
        summary = f"Email {idx + 1}:\n"
        summary += f"  From: {em.get('sender_name', '')} <{em.get('sender_email', '')}>\n"
        summary += f"  Subject: {em.get('subject', '')}\n"
        summary += f"  Body preview: {em.get('body_preview', '')[:300]}\n"
        email_summaries.append(summary)

    system = """You classify job application emails. For each email, determine:
1. Is it job-application related? (yes/no)
2. If yes, what category?
   - acknowledgement: "we received your application", "thank you for applying"
   - assignment: coding challenge, take-home test, assessment
   - interview: interview invitation, scheduling call
   - rejection: "we won't be moving forward", "other candidates"
   - offer: job offer, compensation details
   - follow_up: requesting more info, additional documents
   - update: general status update
3. Which company is it from?

Return ONLY a JSON array. No markdown, no backticks. Each element:
{"index": 1, "is_job_related": true, "category": "acknowledgement", "company": "Google", "summary": "brief one-line summary"}

For non-job emails, use: {"index": 1, "is_job_related": false, "category": "not_relevant", "company": "", "summary": ""}"""

    prompt = "Classify these emails:\n\n" + "\n".join(email_summaries)
    prompt += "\n\nReturn ONLY the JSON array. No other text."

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 2000,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]

        # Parse JSON
        result_text = result_text.strip()
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(lines[1:])
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        classifications = json.loads(result_text.strip())

        # Merge classifications back with email data
        enriched = []
        for cls in classifications:
            idx = cls.get("index", 0) - 1
            if 0 <= idx < len(emails):
                em = emails[idx].copy()
                em["is_job_related"] = cls.get("is_job_related", False)
                em["category"] = cls.get("category", "not_relevant")
                em["company"] = cls.get("company", "")
                em["ai_summary"] = cls.get("summary", "")
                enriched.append(em)

        return enriched

    except Exception as e:
        print(f"[Gmail] Classification error: {e}")
        # Return emails without classification on error
        return [
            {**em, "is_job_related": True, "category": "unknown", "company": "", "ai_summary": "Classification failed"}
            for em in emails
        ]