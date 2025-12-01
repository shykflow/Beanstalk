# Hubstaff-Style Time Tracker — Full Spec (Easy .md)

> **Goal:** Build a cross‑platform desktop time tracker + admin panel with strict working hours for Pakistan (Asia/Karachi), automatic break, idle filtering via mouse/keyboard activity, and rich reporting. Backend on Postgres (self‑hosted on EC2).

---

## 0) TL;DR Build Plan

* **Desktop App:** Electron + React (TypeScript). Background tray app, autostart, low CPU. Activity sampler (mouse/keyboard) every 5s. Idle detection ≥5m.
* **Backend API:** Node.js (NestJS) + Prisma + Postgres. JWT auth (access + refresh) with org‑scoped RBAC.
* **Worker:** BullMQ + Redis for rollups, reports, alerts.
* **Admin Panel:** Next.js (App Router) + Tailwind + shadcn/ui + TanStack Table for timesheets.
* **DB:** PostgreSQL 16 on EC2 (Ubuntu 22.04). PgBouncer in front for pooling.
* **Time Rules (Asia/Karachi):**

  * **Check‑in window:** 16:50 → 02:00 next day.
  * **Break:** 22:00 → 23:00 (no logging; show “Break” banner in desktop app; lock activity).
  * **Idle filter:** If **no mouse OR keyboard** activity for **≥ 5 minutes**, **do not log** those minutes.
* **Reports:** Daily / weekly / monthly timesheets, per‑user detail with idle/break deductions shown.

---

## 1) Functional Requirements

### 1.1 Desktop Tracker (Electron)

* Cross‑platform (Windows/macOS/Linux).
* **Login** → fetch org + schedule.
* **Check‑in** allowed only within **16:50–02:00 Asia/Karachi**.
* **Break enforcement 22:00–23:00:**

  * Client disables tracking and displays **Break mode**.
  * Prevent manual overrides; any attempt to log is rejected client‑side and server validates again.
* **Activity sampling:** every 5s capture current mouse movement delta and keystrokes count (not key content). Store locally then batch upload every 60s.
* **Idle detection:** any continuous span **≥ 300s** with **zero** mouse AND keyboard → treat as **idle** and exclude from log.
* **Clock drift guard:** server authoritative; client posts local timestamps; API returns canonical timestamps.
* **Autostart + Tray:** launches at OS login; tray menu for Start/Stop, Status, Last sync.
* **Network resilience:** queue offline events; backfill on reconnect.
* **Self‑update:** electron‑updater with a private release server or GitHub Releases.

### 1.2 Admin Panel (Web)

* Users CRUD, roles (Owner, Admin, Manager, Member).
* Timesheets by **day/week/month** with filters (user, team, status, date range).
* Detail view: per‑minute bars: Active / Idle / Break / Off‑hours.
* Approvals & manual adjustments (with audit trail).
* CSV export / Excel, and PDF summary.
* Organization settings: schedule windows, break windows, idle threshold, timezone (default **Asia/Karachi**).

### 1.3 Backend/API

* JWT access (15m) + refresh (30d). Org‑scoped RBAC.
* Endpoints to register activity samples, roll up to **time_entries**.
* Validation against windows (check‑in, break) and idle rules.
* Reports endpoints with aggregation.
* Webhooks (optional) for payroll/export.

---

## 2) Time & Rules — Precise Logic

> **Timezone:** Always compute in **Asia/Karachi**. Pakistan currently has **no DST**; keep a feature flag in case DST is reintroduced.

### 2.1 Windows

* **Check‑in allowed:** `16:50 → 02:00 (+1 day)`.
* **Break:** `22:00 → 23:00` (no logging; show enforced break UI; block uploads in this window).

### 2.2 Idle Filtering

* Maintain a sliding window of the last N seconds. If **every 5‑second sample** in a 300‑second span has `mouseDelta == 0 && keyCount == 0`, mark that span **Idle**. Do not persist as time.

### 2.3 Roll‑up Algorithm (pseudo)

```ts
function rollup(samples: Sample[]): TimeEntry[] {
  // Group by minute boundaries in Asia/Karachi
  const minutes = bucketByMinute(samples, tz="Asia/Karachi");
  const entries: TimeEntry[] = [];
  for (const m of minutes) {
    const inCheckWindow = withinCheckWindow(m.start);
    const inBreak = withinBreakWindow(m.start);
    const active = m.any(s => s.mouseDelta>0 || s.keyCount>0);

    if (!inCheckWindow) continue;             // off-hours not counted
    if (inBreak) continue;                     // break not counted
    if (!active) continue;                     // idle minute not counted

    entries.push({ userId, start: m.start, end: m.end, type: 'ACTIVE' });
  }
  return mergeContiguous(entries);            // compress consecutive minutes
}
```

### 2.4 Crossing Midnight

* Represent intervals with explicit dates; e.g., session `2025‑11‑07 23:55 → 2025‑11‑08 00:10`.
* Apply rules minute‑by‑minute; the **02:00** cutoff is next‑day relative to the start calendar day.

### 2.5 Manual Adjustments

* Admins may add/subtract minutes with a **reason**. All adjustments recorded in `adjustments` with `created_by` and before/after spans.

---

## 3) Data Model (PostgreSQL)

```sql
-- organizations & users
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'Asia/Karachi',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  email CITEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT,
  role TEXT NOT NULL CHECK (role IN ('OWNER','ADMIN','MANAGER','MEMBER')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_org ON users(org_id);

-- sessions for desktop app
CREATE TABLE device_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  device_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  UNIQUE(user_id, device_id, started_at)
);

-- raw activity samples (batched uploads)
CREATE TABLE activity_samples (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  captured_at TIMESTAMPTZ NOT NULL,
  mouse_delta INT NOT NULL,
  key_count INT NOT NULL,
  device_session_id UUID REFERENCES device_sessions(id) ON DELETE SET NULL
);
CREATE INDEX idx_samples_user_time ON activity_samples(user_id, captured_at);

-- rolled-up minutes
CREATE TABLE time_entries (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('ACTIVE','IDLE','BREAK')),
  source TEXT NOT NULL DEFAULT 'AUTO',  -- AUTO or MANUAL
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_entries_user_time ON time_entries(user_id, started_at);

-- schedule & rules per org (defaults shown)
CREATE TABLE schedules (
  org_id UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
  tz TEXT NOT NULL DEFAULT 'Asia/Karachi',
  checkin_start TIME NOT NULL DEFAULT '16:50',
  checkin_end TIME NOT NULL DEFAULT '02:00',
  break_start TIME NOT NULL DEFAULT '22:00',
  break_end TIME NOT NULL DEFAULT '23:00',
  idle_threshold_seconds INT NOT NULL DEFAULT 300
);

-- manual adjustments
CREATE TABLE adjustments (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_by UUID NOT NULL REFERENCES users(id),
  reason TEXT NOT NULL,
  delta_minutes INT NOT NULL,
  effective_date DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Indexes:**

* `idx_samples_user_time` for ingestion windows.
* `idx_entries_user_time` for reports.

**Retention:**

* Raw samples optional retention (e.g., 90 days). Time entries retained long‑term.

---

## 4) API Design (NestJS)

### Auth

* `POST /auth/login` → {access, refresh}
* `POST /auth/refresh`

### Activity

* `POST /activity/batch` — body: array of `{capturedAt, mouseDelta, keyCount, deviceSessionId}`
* `POST /sessions/start` / `POST /sessions/stop`

### Reports

* `GET /reports/summary?userId&from&to` → totals with ACTIVE/IDLE/BREAK minutes
* `GET /reports/daily?date`
* `GET /reports/weekly?week=YYYY-Www`
* `GET /reports/monthly?month=YYYY-MM`

### Admin

* `GET /users` `POST /users` `PATCH /users/:id` `DELETE /users/:id`
* `GET /entries?userId&from&to` — minute bars
* `POST /adjustments`
* `GET /settings/schedule` `PATCH /settings/schedule`

**Guards:** org‑scoped, role‑based (Owner/Admin/Manager/Member).

---

## 5) Desktop App (Electron + React)

### Core Modules

* **Sampler:** `iohook` (or `@nut-tree/nut-js` for cursor pos) for mouse delta & key counts. Don’t capture key **content**.
* **Uploader:** batches every 60s; retries exponential backoff.
* **Enforcer:** disables Start during off‑hours; auto‑Stop at 02:00; auto‑Break lock 22:00–23:00.
* **UI:** Start/Stop, Today summary, Last sync, Status badges.

### Permissions

* macOS: Accessibility permission (AX). Windows: low‑level hooks via node module. Linux: X11/Wayland hooks.

### Packaging

* Windows: NSIS, auto‑update via electron‑builder. macOS: notarized dmg. Linux: AppImage.

---

## 6) Admin Panel (Next.js)

* **Tables:** Users, Timesheets, Entries detail.
* **Charts:** Hours by day/week.
* **Filters:** user/team/date.
* **Exports:** CSV, XLSX, PDF.
* **Forms:** Schedule settings (times, idle threshold, timezone).

---

## 7) Background Worker (BullMQ)

* **Jobs:** rollup new samples → entries; recompute on schedule change; generate reports; email/export.
* **Schedules:** every minute process latest; nightly consolidation at 03:00 Asia/Karachi.

---

## 8) Deploy PostgreSQL on EC2 (Ubuntu 22.04)

1. **Provision EC2:** t3.medium (or better), gp3 volume. Security Group: allow 22 (SSH), **5432 from app subnets/IPs only**. Prefer private subnet + VPN/Bastion.
2. **System deps**

   ```bash
   sudo apt update && sudo apt -y upgrade
   sudo apt -y install postgresql-16 postgresql-client-16 ufw
   ```
3. **Config**

   * `/etc/postgresql/16/main/postgresql.conf`:

     * `listen_addresses = '*'`
     * `shared_buffers = 25% of RAM`
     * `effective_cache_size = 50% of RAM`
     * `work_mem = 4-16MB`
   * `/etc/postgresql/16/main/pg_hba.conf`:

     * `hostssl all all <YOUR_APP_CIDR> md5`
4. **TLS** (simple way with self‑signed for internal):

   ```bash
   sudo -u postgres mkdir -p /var/lib/postgresql/16/main/certs
   openssl req -new -x509 -days 3650 -nodes -out server.crt -keyout server.key -subj \
     "/C=PK/ST=Sindh/L=Karachi/O=YourOrg/OU=Eng/CN=postgres.ec2.internal"
   chmod 600 server.key && chown postgres:postgres server.*
   ```

   Set in `postgresql.conf`: `ssl=on`, `ssl_cert_file='server.crt'`, `ssl_key_file='server.key'`.
5. **Users & DB**

   ```bash
   sudo -u postgres psql -c "CREATE ROLE app WITH LOGIN PASSWORD '...';"
   sudo -u postgres createdb -O app time_tracker
   ```
6. **Firewall**

   ```bash
   sudo ufw allow OpenSSH
   sudo ufw allow from <YOUR_APP_CIDR> to any port 5432 proto tcp
   sudo ufw enable
   ```
7. **Pooling (PgBouncer)** (optional but recommended) in same instance or sidecar.
8. **Backups**

   * Nightly `pg_dump` to S3 + weekly base backup with `pg_basebackup`.
9. **Monitoring**

   * `pg_stat_statements`, CloudWatch agent or Prometheus node exporter + postgres exporter.

> **Alternative:** Use **Amazon RDS for PostgreSQL/Aurora** to offload ops.

---

## 9) Security & Privacy

* **Consent:** inform users that only **activity counts** (not key content) are captured.
* **Transport:** HTTPS for API; TLS for Postgres.
* **At Rest:** enable disk encryption on EC2; consider pgcrypto for sensitive fields.
* **Least privilege:** separate DB users for app, read‑only reporting, admin.
* **Audit log:** adjustments, admin actions.

---

## 10) Environment & DevOps

* Monorepo with **pnpm workspaces**: `apps/desktop`, `apps/admin`, `apps/api`, `apps/worker`, `packages/ui`, `packages/config`, `packages/types`.
* CI: Build, typecheck, test; sign Electron builds on release branch.
* Infra as Code: Terraform for EC2, SGs, S3 backups.

---

## 11) Prompt for Cursor (drop‑in)

> Paste this into Cursor as your **Project Instruction** (or first message) so it scaffolds and keeps constraints.

```
You are an expert full‑stack engineer. Build a Hubstaff‑style time tracker with:

STACK
- Desktop: Electron + React + TypeScript.
- API: NestJS + Prisma + Postgres.
- Admin: Next.js (App Router) + Tailwind + shadcn/ui.
- Worker: BullMQ + Redis.
- Monorepo: pnpm workspaces.

REQUIREMENTS (HARD)
- Timezone: Asia/Karachi.
- Check‑in allowed only 16:50 → 02:00 next day.
- Enforced Break 22:00 → 23:00 (no logging; UI shows Break).
- Idle rule: if no mouse AND no keyboard activity for ≥ 5 minutes, do not log those minutes.
- Minute‑level rollups with ACTIVE/IDLE/BREAK.
- Desktop samples activity every 5 seconds; batch upload every 60 seconds.
- Offline queue + backfill; server authoritative timestamps.
- Admin panel with Users CRUD; timesheets (day/week/month); per‑minute bars; exports.
- RBAC: OWNER/ADMIN/MANAGER/MEMBER.

DELIVERABLES
- Prisma schema for tables: organizations, users, device_sessions, activity_samples, time_entries, schedules, adjustments.
- NestJS modules: Auth, Activity, Entries, Reports, Admin.
- Electron app with Tray, Autostart, Sampler, Enforcer, Uploader.
- Next.js admin pages: Dashboard, Users, Timesheets, Entry detail, Settings (schedule & idle).
- Worker jobs for rollup + nightly consolidation.

QUALITY
- Type‑safe DTOs; Zod validation on client.
- E2E tests for time windows (cross‑midnight), break exclusion, idle exclusion, and rollup merging.
- Linting (eslint, prettier), commit hooks.

Non‑goals: keylogging content, screenshots.
```

---

## 12) Testing Scenarios (acceptance)

* User checks in at **16:49** → blocked; at **16:50** → allowed.
* Session from **21:55–23:05** → only 21:55–22:00 counts; 22:00–23:00 break removed; 23:00–23:05 counts (if active).
* Idle stretch **5m10s** with zero activity → excluded.
* Crossing midnight: **01:55–02:05** → only 01:55–02:00 counts.
* Offline 30m then reconnect → backlog processed, timestamps canonical from server.

---

## 13) Nice‑to‑Haves (Later)

* Screenshot blurring/redaction (with consent).
* Geofenced check‑ins (office IPs).
* Desktop “nudge” after 5m idle.
* Payroll integrations (CSV template first).


## 14) Quick Commands

* Seed org + admin: `pnpm api prisma db push && pnpm api prisma db seed`
* Run all: `pnpm -r dev` (API 3000, Admin 3001, Worker 3002, Desktop dev hot‑reload)

