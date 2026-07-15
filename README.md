
# OnTreq - Trekking Management Application
This is a complete web application for managing treks, trek staff, and trekkers, built for the MAD-II (Modern Application Development II) project.
It is a Flask REST API backend (SQLite database, JWT authentication, Redis caching, Celery background jobs) paired with a Vue 3 (CDN) + Bootstrap 5 frontend, served as a PWA. The application supports three user roles with full authentication and role-based access: **Admin**, **Trek Staff**, and **User (Trekker)**.

## Technologies Used
* **Backend:** Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-Cors, Flask-Caching
* **Database:** SQLite
* **Caching:** Redis (Flask-Caching)
* **Background Jobs:** Celery + Celery Beat (daily reminders, monthly report, async CSV export)
* **Frontend:** HTML, Vue 3 (CDN), Bootstrap 5, Chart.js, PWA (manifest.json + service worker)

## How to Run the Code
To run this project on your local machine, please follow these steps.

### 1. Unzip the Project
Unzip the submission file. You will have a single project root folder (`OnTreq-Trekking-Management-Application`), containing a `backend/` folder, a `frontend/` folder, an empty `instance/` folder, and a `.gitignore` file. No virtual environment and no database file are included — these are created in the steps below.

### 2. Open a Terminal
Open your terminal (Command Prompt, PowerShell, or bash) and navigate into the `backend` folder — this is where all commands below are run from:
```
cd path/to/OnTreq-Trekking-Management-Application/backend
```

### 3. Create and Activate a Virtual Environment
It is essential to create a virtual environment to manage the project's dependencies.
```
# Create the venv
python -m venv venv

# Activate the venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 4. Install Dependencies
Install all the required Python libraries from the requirements.txt file.
```
pip install -r requirements.txt
```

### 5. Install and Start Redis
Redis is required for both caching and Celery. If you don't already have it installed:
* **Mac:** `brew install redis` then `redis-server`
* **Linux:** `sudo apt install redis-server` then `redis-server`
* **Windows:** install via WSL/Memurai, then run `redis-server`

Leave this terminal running, and open a new terminal (re-activating the venv) for the next steps.

### 6. Set Up the Database
The database file is **not** included in this submission (only an empty `instance/` folder is). From the `backend` folder, run:
```
python setup_db.py
```
This creates the SQLite database, all tables, and a default Admin account (see credentials below). It is safe to re-run — it will detect an existing admin and won't overwrite data.

### 7. Run the Flask Server
This single server serves both the API and the frontend.
```
python app.py
```
The server will start and be running on http://127.0.0.1:5000.

### 8. (Optional) Start Celery Worker and Beat
These power the async CSV export and the scheduled daily reminder / monthly report jobs. Open two more terminals (each with the venv activated, from the `backend` folder):
```
# Terminal A - Celery worker (handles async jobs like CSV export)
celery -A app.celery_app worker --loglevel=info
# On Windows, add --pool=solo

# Terminal B - Celery Beat (triggers the scheduled jobs)
celery -A app.celery_app beat --loglevel=info
```
The core app (browsing, booking, admin/staff management) works fine without these — they're only needed to test background/scheduled features.

### 9. Access the Application
Open your web browser and go to:
http://127.0.0.1:5000

### Default Login Credentials
The database comes pre-loaded with a default Admin account. You can use this to log in and manage the site.
```
Email: admin@ontreq.com
Password: ontreq4942
```
Trek Staff accounts are created by the Admin from the "Manage Staff" page.
New User (Trekker) accounts can be self-registered from the "Register" page.

## Roles
| Role | Access |
|---|---|
| Admin | Pre-created via `setup_db.py`. Manages treks, staff, users, bookings, reports, blacklisting. |
| Trek Staff | Created by Admin (Manage Staff page). Manages only assigned treks: slots, status, participants, completion. |
| User (Trekker) | Self-registers. Browses/searches/filters treks, books, cancels, views history, exports CSV, edits profile. |

## Key Business Rules Implemented
- Booking allowed only when trek status is **Open**
- No overbooking beyond available slots
- No duplicate active booking of the same trek
- Cancelling a booking releases the slot back
- Only assigned staff can manage their trek
- Blacklisted users/staff cannot log in
- Marking a trek Completed cascades booking statuses to Completed
- Redis caching on trek listings, public stats, admin stats/analytics with automatic invalidation on every mutation