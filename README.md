# Health Record Vault — Complete Academic Project

This project follows the supplied **Problem Statement 12: Health Record Vault**. It is a full-stack local web application with a patient, doctor and admin role.

## 1. Problem statement coverage

| Requirement in your paper | Implemented feature |
|---|---|
| Patient can register and log in | Patient registration and login |
| Upload medical documents | PDF, JPG, JPEG, PNG, DOC and DOCX upload |
| Organize by tags/categories | Title, category, date and description |
| Search records | Search by title, category and description |
| View/download records | Owner and authorized doctor can view/download |
| Share selected records | Share with a registered doctor or time-limited secure link |
| Limited-time doctor access | Expiring share link; expiry can be 1–720 hours |
| Revoke access | Patient can revoke all shares for a record |
| Doctor login | Doctor account and role-specific dashboard |
| Doctor accesses shared records | Doctor sees only records shared with that doctor account |
| Doctor notes (optional) | Doctor can add notes to a shared record |
| Admin monitors usage | Admin can view user list and system activity logs |
| Audit logs | Register, login, logout, upload, view, download, share, grant, revoke, delete and note actions |
| Secure storage | Files stored in a private server folder, not exposed as public static files |
| Authentication and authorization | Password hashing, session login and role checks |

## 2. Project folder structure

```text
Health_Record_Vault_Complete/
│
├── run.py                 # Starts the Flask application
├── config.py              # App settings and upload restrictions
├── requirements.txt       # Python packages
├── README.md              # Setup and project explanation
├── API_GUIDE.md           # API endpoint list
├── PROJECT_REPORT.md      # Viva/project explanation
│
├── app/
│   ├── __init__.py        # Creates Flask app and registers routes
│   ├── database.py        # Creates SQLite tables and demo users
│   ├── security.py        # Login checks, roles, file validation, audit
│   ├── routes.py          # Backend API endpoints
│   ├── templates/
│   │   └── index.html     # Frontend page
│   └── static/
│       ├── style.css      # Blue and white design
│       └── app.js         # Frontend interactions and API calls
│
├── instance/              # Database is generated here on first run
├── uploads/               # Uploaded files stored privately
└── tests/
    └── TESTING_CHECKLIST.md
```

## 3. Installation — Windows PowerShell

**Important:** Open the folder that directly contains `run.py` and `requirements.txt`. Do not run commands from its parent folder.

1. Extract the ZIP.
2. In VS Code, choose **File → Open Folder** and open `Health_Record_Vault_Complete`.
3. In the VS Code terminal, run:

```powershell
dir
```

You must see `run.py`, `requirements.txt`, `config.py`, `app`, `docs`/project documents.

4. Create virtual environment:

```powershell
py -m venv venv
```

5. Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

6. Install packages:

```powershell
python -m pip install -r requirements.txt
```

7. Start the project:

```powershell
py run.py
```

8. Open this address in Chrome:

```text
http://127.0.0.1:5000
```

Keep the terminal open while using the website. Press `Ctrl + C` to stop the server.

## 4. Demo login accounts

| Role | Email | Password |
|---|---|---|
| Patient | patient@demo.com | Patient@123 |
| Doctor | doctor@demo.com | Doctor@123 |
| Admin | admin@demo.com | Admin@123 |

You can register new Patient and Doctor accounts from the Register tab. Admin accounts cannot be created from public registration.

## 5. Demonstration flow for your faculty

1. Login as Patient.
2. Upload a sample medical report.
3. Search the report by title/category.
4. Click **Share** and enter `doctor@demo.com`.
5. Logout and login as Doctor.
6. Doctor should see the record shared with that doctor account and can download it.
7. Doctor can add a note to a shared record.
8. Login as Patient again and click **Revoke**.
9. Open Access & Activity Logs and explain the actions.
10. Login as Admin and show registered users and logs.

To test an unassigned secure link, use Share with an empty doctor email. The user still needs to log in; the link is time-limited. For the doctor-specific share, login with the doctor account matching the email.

## 6. Database

SQLite database file is created automatically at `instance/health_vault.sqlite3`.

- `users`: user name, email, password hash and role.
- `records`: record metadata and private stored filename.
- `shares`: doctor assignment, random token, expiry and active/revoked state.
- `access_logs`: who performed which action and when.
- `doctor_notes`: optional doctor notes attached to shared records.

## 7. Security notes and limitations

This is an educational prototype, not a certified healthcare system. Do not upload real patient records. Before real deployment, add HTTPS, CSRF protection, rate limiting, stronger identity verification, encrypted cloud storage, backups, malware scanning, secure production secrets, secure cookie settings, retention controls and a privacy/security audit. The current local upload folder is not cloud storage. The architecture can later be extended to AWS S3 or another private object store.
