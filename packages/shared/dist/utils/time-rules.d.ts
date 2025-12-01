export declare const DEFAULT_TIMEZONE = "Asia/Karachi";
export interface TimeWindow {
    start: string;
    end: string;
}
export interface ScheduleRules {
    timezone: string;
    checkinWindow: TimeWindow;
    breakWindow: TimeWindow;
    idleThresholdSeconds: number;
}
export declare const DEFAULT_RULES: ScheduleRules;
/**
 * Check if a timestamp falls within the check-in window
 * Handles midnight crossing (e.g., 16:50 -> 02:00 next day)
 */
export declare function isWithinCheckinWindow(timestamp: Date, rules?: ScheduleRules): boolean;
/**
 * Check if a timestamp falls within the break window
 */
export declare function isWithinBreakWindow(timestamp: Date, rules?: ScheduleRules): boolean;
/**
 * Get the current time in the organization's timezone
 */
export declare function getCurrentTimeInTz(timezone?: string): Date;
/**
 * Convert a local time string to UTC
 */
export declare function localTimeToUtc(dateStr: string, timeStr: string, timezone?: string): Date;
/**
 * Format a date in the organization's timezone
 */
export declare function formatInTz(date: Date, formatStr: string, timezone?: string): string;
/**
 * Get the start and end of a day in the organization's timezone
 */
export declare function getDayBoundariesInTz(date: Date, timezone?: string): {
    start: Date;
    end: Date;
};
/**
 * Check if samples indicate activity (mouse or keyboard)
 */
export declare function hasActivity(mouseDelta: number, keyCount: number): boolean;
/**
 * Determine if a span of samples represents idle time
 * @param samples - Array of samples with mouseDelta and keyCount
 * @param thresholdSeconds - Idle threshold in seconds
 * @returns true if all samples show no activity
 */
export declare function isIdleSpan(samples: Array<{
    mouseDelta: number;
    keyCount: number;
}>, thresholdSeconds?: number): boolean;
