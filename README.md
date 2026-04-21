# FDPP EMS Frontend

React + Vite frontend for the FDPP Employee Management System API.

## Features

- JWT authentication with login route and protected app pages
- Automatic access-token refresh using refresh token
- Public quick attendance check-in/check-out actions on the login page
- Dashboard with employee stats, daily/weekly/monthly attendance summaries, and pending leave queue
- Employee management with documented fields and full CRUD
- Attendance operations with check-in/check-out and record filtering
- Leave management with request creation, pending approvals, approve/reject, and employee leave history
- Shift management with create/update/delete workflows
- Report tools for payout calculation and employee attendance analytics

## Quick Start

1. Install dependencies

```bash
npm install
```

2. Set environment values

```bash
copy .env.example .env
```

3. Run development server

```bash
npm run dev
```

4. Build for production

```bash
npm run build
```

## Environment

- `VITE_API_URL` default: `http://localhost:8000/api`

## Authentication

- Public routes:
	- `/login`
- Protected routes:
	- `/`, `/employees`, `/attendance`, `/leave`, `/shifts`, `/reports`
- Frontend behavior:
	- Saves `access` + `refresh` tokens in browser storage after login
	- Adds `Authorization: Bearer <access>` to protected requests
	- Automatically calls `/api/token/refresh/` and retries once when access token expires
	- Handles refresh-token rotation when backend returns a new refresh token
	- Redirects to login when refresh fails or session is invalid

User registration is intentionally disabled in the frontend UI.

## Backend Notes

- API should follow `references/UPDATED_API_DOCUMENTATION.md`
- Ensure CORS is enabled on the Django backend
- Frontend expects trailing-slash DRF endpoints

## Developer Notes

- Biometric attendance:
	- Uses `VITE_ATTENDANCE_WS_URL` (or derives from `VITE_API_URL`) for a websocket at `/ws/biometric/`.
	- Recent activity list is limited to the last 6 entries (see `src/pages/BiometricAttendance.jsx`).
	- Activity items change visual state for `check_in` vs `check_out` (left border and subtle background).
	- The profile card updates in-place (no remount) to preserve visual state.

- Employees:
	- `designation` field was added to the employee form and is sent to the backend when creating/updating employees (`src/pages/Employees.jsx`).
	- Managers have restricted UI: update/delete buttons and pending-approval lists are hidden for users with role `manager`.

If you'd like these notes expanded (build details, local test commands, or CI), tell me what to include.
