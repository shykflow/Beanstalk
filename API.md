# API Documentation

Base URL: `http://localhost:3001/api`

## Authentication

All authenticated endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### POST /auth/register

Register a new organization and owner user.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "password123",
  "fullName": "Admin User",
  "orgName": "My Organization"
}
```

**Response:**
```json
{
  "accessToken": "eyJhbGc...",
  "refreshToken": "eyJhbGc..."
}
```

### POST /auth/login

Login with email and password.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "accessToken": "eyJhbGc...",
  "refreshToken": "eyJhbGc..."
}
```

### POST /auth/refresh

Refresh access token using refresh token.

**Request:**
```json
{
  "refreshToken": "eyJhbGc..."
}
```

**Response:**
```json
{
  "accessToken": "eyJhbGc...",
  "refreshToken": "eyJhbGc..."
}
```

### POST /auth/logout

Logout and invalidate refresh tokens.

**Headers:** `Authorization: Bearer <token>`

**Response:** `204 No Content`

## Users

### GET /users

Get all users in the organization.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN, MANAGER

**Response:**
```json
[
  {
    "id": "uuid",
    "email": "user@example.com",
    "fullName": "User Name",
    "role": "MEMBER",
    "isActive": true,
    "createdAt": "2025-01-01T00:00:00Z"
  }
]
```

### GET /users/:id

Get a specific user.

**Headers:** `Authorization: Bearer <token>`

### POST /users

Create a new user.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN

**Request:**
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "fullName": "New User",
  "role": "MEMBER"
}
```

### PUT /users/:id

Update a user.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN

**Request:**
```json
{
  "fullName": "Updated Name",
  "role": "MANAGER",
  "isActive": true
}
```

### DELETE /users/:id

Delete a user.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN

## Activity Tracking

### POST /activity/sessions/start

Start a new tracking session.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "deviceId": "device-123",
  "platform": "darwin"
}
```

**Response:**
```json
{
  "id": "session-uuid",
  "userId": "user-uuid",
  "deviceId": "device-123",
  "platform": "darwin",
  "startedAt": "2025-01-01T16:50:00Z"
}
```

### POST /activity/sessions/stop

Stop a tracking session.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "sessionId": "session-uuid"
}
```

### POST /activity/batch

Upload activity samples in batch.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "samples": [
    {
      "capturedAt": "2025-01-01T17:00:00Z",
      "mouseDelta": 150,
      "keyCount": 25,
      "deviceSessionId": "session-uuid"
    }
  ]
}
```

**Response:**
```json
{
  "inserted": 10,
  "rejected": 2
}
```

### GET /activity/recent

Get recent activity samples.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `limit` (optional): Number of samples to return (default: 100)

## Reports

### GET /reports/summary

Get summary for a user and date range.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `userId`: User UUID
- `from`: ISO date string
- `to`: ISO date string

**Response:**
```json
{
  "userId": "user-uuid",
  "from": "2025-01-01T00:00:00Z",
  "to": "2025-01-07T23:59:59Z",
  "totalMinutes": 2400,
  "activeMinutes": 2200,
  "idleMinutes": 200,
  "breakMinutes": 0
}
```

### GET /reports/daily

Get daily report for all users.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN, MANAGER

**Query Parameters:**
- `date` (optional): Date in YYYY-MM-DD format (default: today)

**Response:**
```json
{
  "date": "2025-01-01",
  "users": [
    {
      "userId": "user-uuid",
      "userName": "User Name",
      "totalMinutes": 480,
      "activeMinutes": 450,
      "idleMinutes": 30,
      "breakMinutes": 0,
      "entries": []
    }
  ]
}
```

### GET /reports/weekly

Get weekly report.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN, MANAGER

**Query Parameters:**
- `week` (optional): Week in YYYY-Www format (e.g., 2025-W01)

### GET /reports/monthly

Get monthly report.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN, MANAGER

**Query Parameters:**
- `month` (optional): Month in YYYY-MM format

### GET /reports/timesheet

Get detailed timesheet for a user.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `userId`: User UUID
- `from`: ISO date string
- `to`: ISO date string

**Response:**
```json
{
  "userId": "user-uuid",
  "from": "2025-01-01T00:00:00Z",
  "to": "2025-01-07T23:59:59Z",
  "entries": [
    {
      "id": 1,
      "startedAt": "2025-01-01T17:00:00Z",
      "endedAt": "2025-01-01T18:00:00Z",
      "kind": "ACTIVE",
      "source": "AUTO"
    }
  ],
  "adjustments": []
}
```

### GET /reports/export/csv

Export detailed timesheet as CSV.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN, MANAGER

**Query Parameters:**
- `from`: ISO date string
- `to`: ISO date string

**Response:** CSV file download

### GET /reports/export/summary-csv

Export summary report as CSV.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN, MANAGER

**Query Parameters:**
- `from`: ISO date string
- `to`: ISO date string

**Response:** CSV file download

## Organization

### GET /organizations/me

Get current organization details.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "org-uuid",
  "name": "My Organization",
  "timezone": "Asia/Karachi",
  "createdAt": "2025-01-01T00:00:00Z",
  "schedule": {
    "tz": "Asia/Karachi",
    "checkinStart": "16:50",
    "checkinEnd": "02:00",
    "breakStart": "22:00",
    "breakEnd": "23:00",
    "idleThresholdSeconds": 300
  }
}
```

### PUT /organizations/me

Update organization details.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN

**Request:**
```json
{
  "name": "Updated Organization Name",
  "timezone": "Asia/Karachi"
}
```

### GET /organizations/schedule

Get organization schedule settings.

**Headers:** `Authorization: Bearer <token>`

### PUT /organizations/schedule

Update schedule settings.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN

**Request:**
```json
{
  "tz": "Asia/Karachi",
  "checkinStart": "16:50",
  "checkinEnd": "02:00",
  "breakStart": "22:00",
  "breakEnd": "23:00",
  "idleThresholdSeconds": 300
}
```

### POST /organizations/adjustments

Create a manual time adjustment.

**Headers:** `Authorization: Bearer <token>`

**Roles:** OWNER, ADMIN, MANAGER

**Request:**
```json
{
  "userId": "user-uuid",
  "reason": "Missed check-in",
  "deltaMinutes": 60,
  "effectiveDate": "2025-01-01"
}
```

### GET /organizations/adjustments

Get adjustments for a user.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `userId`: User UUID
- `from` (optional): ISO date string
- `to` (optional): ISO date string

## Error Responses

All endpoints may return the following error responses:

**400 Bad Request:**
```json
{
  "statusCode": 400,
  "message": "Validation failed",
  "error": "Bad Request"
}
```

**401 Unauthorized:**
```json
{
  "statusCode": 401,
  "message": "Unauthorized"
}
```

**403 Forbidden:**
```json
{
  "statusCode": 403,
  "message": "Forbidden resource"
}
```

**404 Not Found:**
```json
{
  "statusCode": 404,
  "message": "Resource not found"
}
```

**500 Internal Server Error:**
```json
{
  "statusCode": 500,
  "message": "Internal server error"
}
```
