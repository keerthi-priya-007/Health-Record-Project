# API Guide — Health Record Vault

All endpoints are served by Flask. JSON responses are used unless an upload form or file download is involved. Login is maintained using a server session cookie.

| Method | Route | Purpose | Role |
|---|---|---|---|
| POST | `/api/auth/register` | Create patient/doctor account | Public |
| POST | `/api/auth/login` | Login | Public |
| POST | `/api/auth/logout` | Logout | Logged-in |
| GET | `/api/auth/me` | Current user details | Logged-in |
| POST | `/api/records/upload` | Upload a medical record | Patient |
| GET | `/api/records` | List permitted records; optional `?q=term` | Logged-in |
| GET | `/api/records/search?q=term` | Search permitted records | Logged-in |
| GET | `/api/records/<id>` | View record metadata | Owner/shared doctor/admin |
| GET | `/api/records/<id>/download` | Download a record | Owner/shared doctor/admin |
| DELETE | `/api/records/<id>` | Delete a record | Owner/admin |
| POST | `/api/records/<id>/share` | Create expiring share link | Patient |
| POST | `/api/records/<id>/grant` | Grant doctor access for 30 days | Patient |
| POST | `/api/records/<id>/revoke` | Revoke active shares | Patient |
| GET | `/api/records/shared/<token>` | Open a valid shared record | Logged-in authorized user |
| GET | `/api/logs` | View activity logs | Logged-in |
| GET | `/api/admin/users` | List registered users | Admin |
| POST | `/api/records/<id>/notes` | Add note to a shared record | Doctor |

## Upload form fields
`multipart/form-data`: `file` (required), `title`, `category`, `record_date`, `description`.

## Share request example
```json
{
  "doctor_email": "doctor@demo.com",
  "expiry_hours": 24
}
```
For a generic time-limited link, set `doctor_email` to an empty string. For a doctor-specific share, the email must belong to a registered doctor.

## Grant request example
```json
{
  "doctor_email": "doctor@demo.com"
}
```
Grant access is set for 30 days.

## Revoke
Send an empty POST request to `/api/records/1/revoke`. This revokes all active shares for that record.

## Common status codes
- `200`: request succeeded.
- `201`: account/record/share created.
- `400`: missing or invalid input.
- `401`: not logged in or incorrect credentials.
- `403`: logged-in user does not have permission.
- `404`: record, doctor or share not found.
- `409`: duplicate registration email.
- `413`: upload exceeds 10 MB.
