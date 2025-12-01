export declare enum UserRole {
    OWNER = "OWNER",
    ADMIN = "ADMIN",
    MANAGER = "MANAGER",
    MEMBER = "MEMBER"
}
export declare enum TimeEntryKind {
    ACTIVE = "ACTIVE",
    IDLE = "IDLE",
    BREAK = "BREAK"
}
export declare enum TimeEntrySource {
    AUTO = "AUTO",
    MANUAL = "MANUAL"
}
export interface Organization {
    id: string;
    name: string;
    timezone: string;
    createdAt: Date;
}
export interface User {
    id: string;
    orgId: string;
    email: string;
    fullName: string | null;
    role: UserRole;
    isActive: boolean;
    createdAt: Date;
}
export interface DeviceSession {
    id: string;
    userId: string;
    deviceId: string;
    platform: string;
    startedAt: Date;
    endedAt: Date | null;
}
export interface ActivitySample {
    id: number;
    userId: string;
    capturedAt: Date;
    mouseDelta: number;
    keyCount: number;
    deviceSessionId: string | null;
}
export interface TimeEntry {
    id: number;
    userId: string;
    startedAt: Date;
    endedAt: Date;
    kind: TimeEntryKind;
    source: TimeEntrySource;
    createdAt: Date;
}
export interface Schedule {
    orgId: string;
    tz: string;
    checkinStart: string;
    checkinEnd: string;
    breakStart: string;
    breakEnd: string;
    idleThresholdSeconds: number;
}
export interface Adjustment {
    id: number;
    userId: string;
    createdBy: string;
    reason: string;
    deltaMinutes: number;
    effectiveDate: Date;
    createdAt: Date;
}
export interface AuthTokens {
    accessToken: string;
    refreshToken: string;
}
export interface JwtPayload {
    sub: string;
    email: string;
    orgId: string;
    role: UserRole;
    iat?: number;
    exp?: number;
}
export interface ActivityBatchItem {
    capturedAt: string;
    mouseDelta: number;
    keyCount: number;
    deviceSessionId?: string;
}
export interface ReportSummary {
    userId: string;
    from: Date;
    to: Date;
    totalMinutes: number;
    activeMinutes: number;
    idleMinutes: number;
    breakMinutes: number;
}
export interface DailyReport {
    date: string;
    users: Array<{
        userId: string;
        userName: string;
        totalMinutes: number;
        activeMinutes: number;
        idleMinutes: number;
        breakMinutes: number;
        entries: TimeEntry[];
    }>;
}
