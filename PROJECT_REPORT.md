# Problem Statement 12 — Health Record Vault

## Objective
Develop a secure web application where patients can upload, store and manage personal health records such as lab reports and prescriptions. Patients can share selected records with doctors using limited-time access links and can revoke access when required. The system maintains audit logs for transparency.

## Description
Patients often lose or cannot access old medical documents when needed. Health Record Vault provides one place to upload, categorize, search and download records. Patients control sharing permissions. Doctors can access only records shared with their account. Admin users can monitor system usage and audit events.

## User roles and responsibilities

### Patient
- Register and log in.
- Upload health records with metadata.
- Organize records by title/category/date.
- Search, view and download personal records.
- Share selected records with a doctor or using an expiring link.
- Grant and revoke doctor access.
- Review access logs.

### Doctor
- Register and log in.
- View records shared with their doctor account.
- Download authorized records.
- Add an optional note to a shared record.

### Admin
- Monitor system usage.
- View registered users.
- Review audit/access logs.
- Admin role is not available through public registration.

## Core modules
1. Authentication and authorization.
2. File upload and private storage.
3. Search and record management.
4. Sharing and access control.
5. Audit logs.
6. Optional doctor notes.
7. Admin monitoring.

## Technology stack
- Frontend: HTML, CSS, JavaScript.
- Backend: Python Flask.
- Database: SQLite.
- File storage: private local uploads folder for this demo; can be replaced by private AWS S3 storage.
- Authentication: Flask session and Werkzeug password hashing.

## Security and privacy considerations
- Passwords are stored as hashes, not plain text.
- Role checks restrict patient, doctor and admin actions.
- Uploaded files are checked by extension and size.
- Random share tokens and expiry times are used.
- Patients can revoke access.
- Record actions are written to audit logs.
- Files are not served from the public static directory.
- Real deployment needs HTTPS, CSRF protection, encryption at rest, malware scanning, backups and security review.

## Deliverables
- Working web application.
- Backend and frontend source code.
- Database schema.
- API route documentation.
- Setup instructions.
- Project demonstration flow.
- Source ZIP archive.
