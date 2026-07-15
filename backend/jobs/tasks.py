from app import celery_app
from models import db, Booking, Trek, User
import csv
import os
from datetime import datetime, timedelta
import time
import urllib.request
import json
from xhtml2pdf import pisa  # Library to turn HTML templates into clean PDFs

GCHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAo_KaZs4/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=zzHzVa_tzgzkYXY20HVsw7ZxK05XgIkjbv2M-DRVhnQ"

def send_gchat_to_user(text):
    """Sends immediate outward alerts directly to the User's Google Chat space."""
    try:
        req = urllib.request.Request(
            GCHAT_WEBHOOK_URL,
            data=json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[WEBHOOK FAILED] {e}")


# =====================================================================
# 1. User Asynchronous CSV Export (Batch Job)
# =====================================================================
@celery_app.task
def export_booking_history(user_id, email):
    time.sleep(4)  # Simulate processing delay
    bookings = db.session.query(Booking, Trek).join(Trek).filter(Booking.user_id == user_id).all()
    
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
    os.makedirs(export_dir, exist_ok=True)
    filename = f"history_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    filepath = os.path.join(export_dir, filename)
    
    with open(filepath, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['User ID', 'Trek Name', 'Location', 'Booking Status', 'Booking Date', 'Start Date'])
        for b, t in bookings:
            b_date = b.booking_date.strftime('%Y-%m-%d') if b.booking_date else 'N/A'
            t_date = t.start_date.strftime('%Y-%m-%d') if t.start_date else 'N/A'
            writer.writerow([user_id, t.name, t.location, b.status, b_date, t_date])
            
    # Notify the specific user over their dashboard channel once compilation finishes
    send_gchat_to_user(f"🔔 Notification for {email}: Your background trekking history CSV export is complete! File: {filename}")
    return {"status": "Complete", "file": filename}


# =====================================================================
# 2. Daily Automatic Trek Reminder Job
# =====================================================================
@celery_app.task
def send_daily_reminders():
    """Finds treks starting tomorrow and alerts the assigned target users."""
    print("--- RUNNING SCHEDULED JOB: DAILY REMINDERS ---")
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    upcoming_treks = Trek.query.filter(db.func.date(Trek.start_date) == tomorrow).all()
    
    for trek in upcoming_treks:
        bookings = Booking.query.filter_by(trek_id=trek.id, status='Booked').all()
        for booking in bookings:
            user = User.query.get(booking.user_id)
            if user and user.is_active:
                # Dispatches user-facing reminders cleanly over the chat hook space
                reminder_msg = f"🌲 Reminder for {user.email}: Your trek '{trek.name}' starts tomorrow ({tomorrow})! Pack your gear and review coordinates."
                print(f"[LOG] {reminder_msg}")
                send_gchat_to_user(reminder_msg)
    return "Daily reminders processed."


# =====================================================================
# 3. Private Monthly Admin Report Job (Generates strict PDF output)
# =====================================================================
@celery_app.task
def generate_monthly_report():
    """Generates an official PDF analytics snapshot for Admin viewing."""
    print("--- RUNNING SCHEDULED JOB: MONTHLY REPORT (PDF) ---")
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Gathers analytical metrics
    recent_bookings = Booking.query.filter(Booking.booking_date >= thirty_days_ago).all()
    total_participants = len(recent_bookings)
    
    # Number of treks conducted/active in past 30 days
    conducted_treks_count = Trek.query.filter(Trek.start_date >= thirty_days_ago).count()
    
    # Calculate Top 3 popular treks
    popular_query = db.session.query(
        Trek.name, db.func.count(Booking.id).label('total')
    ).join(Booking).filter(Booking.booking_date >= thirty_days_ago).group_by(Trek.id).order_by(db.desc('total')).limit(3).all()
    
    popular_rows = "".join([f"<li><strong>{name}</strong> — {count} registrations</li>" for name, count in popular_query])
    if not popular_rows:
        popular_rows = "<li>No operational data recorded during this cycle.</li>"
    
    # Clean HTML Template explicitly styled for safe standard PDF rendering engines
    html_template = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Helvetica, Arial, sans-serif; color: #2d3436; padding: 30px; }}
            h1 {{ color: #d63031; border-bottom: 2px solid #d63031; padding-bottom: 10px; }}
            .metric {{ font-size: 14px; margin-bottom: 8px; }}
            .footer {{ margin-top: 40px; font-size: 11px; color: #b2bec3; font-style: italic; }}
        </style>
    </head>
    <body>
        <h1>OnTreq Management Platform</h1>
        <h2>Monthly Performance Executive Report</h2>
        <p><strong>Reporting Cycle Date:</strong> {datetime.utcnow().strftime('%B %Y')}</p>
        <hr>
        
        <h3>Core Operational Metrics (Past 30 Days)</h3>
        <div class="metric">Total Expeditions Conducted: <strong>{conducted_treks_count}</strong></div>
        <div class="metric">Total Registered Trekking Participants: <strong>{total_participants}</strong></div>
        
        <h3>Trending / Popular Routes</h3>
        <ul>
            {popular_rows}
        </ul>
        
        <p class="footer">* Confidential document built by the OnTreq Automated Celery Infrastructure for Admin eyes only.</p>
    </body>
    </html>
    """
    
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
    os.makedirs(export_dir, exist_ok=True)
    filename = f"Admin_Report_{datetime.utcnow().strftime('%b_%Y')}.pdf"
    filepath = os.path.join(export_dir, filename)
    
    # Build the binary PDF output stream safely 
    with open(filepath, "w+b") as pdf_file:
        pisa_status = pisa.CreatePDF(html_template, dest=pdf_file)
        
    if pisa_status.err:
        print("❌ Error compiling HTML into PDF report.")
        return "Failed to build PDF report."
        
    # NOTE: GChat webhooks omitted entirely here to protect secure admin structural analytics.
    print(f"[EMAIL SIMULATION] System safely sent official PDF document attachment to admin@ontreq.com. File: {filename}")
    return "Monthly PDF report generated."