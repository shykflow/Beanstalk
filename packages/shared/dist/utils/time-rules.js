"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_RULES = exports.DEFAULT_TIMEZONE = void 0;
exports.isWithinCheckinWindow = isWithinCheckinWindow;
exports.isWithinBreakWindow = isWithinBreakWindow;
exports.getCurrentTimeInTz = getCurrentTimeInTz;
exports.localTimeToUtc = localTimeToUtc;
exports.formatInTz = formatInTz;
exports.getDayBoundariesInTz = getDayBoundariesInTz;
exports.hasActivity = hasActivity;
exports.isIdleSpan = isIdleSpan;
const date_fns_tz_1 = require("date-fns-tz");
const date_fns_1 = require("date-fns");
exports.DEFAULT_TIMEZONE = 'Asia/Karachi';
exports.DEFAULT_RULES = {
    timezone: exports.DEFAULT_TIMEZONE,
    checkinWindow: { start: '16:50', end: '02:00' },
    breakWindow: { start: '22:00', end: '23:00' },
    idleThresholdSeconds: 300,
};
/**
 * Check if a timestamp falls within the check-in window
 * Handles midnight crossing (e.g., 16:50 -> 02:00 next day)
 */
function isWithinCheckinWindow(timestamp, rules = exports.DEFAULT_RULES) {
    const tz = rules.timezone;
    const zonedTime = (0, date_fns_tz_1.utcToZonedTime)(timestamp, tz);
    const timeStr = (0, date_fns_tz_1.format)(zonedTime, 'HH:mm', { timeZone: tz });
    const { start, end } = rules.checkinWindow;
    // If end < start, window crosses midnight
    if (end < start) {
        return timeStr >= start || timeStr < end;
    }
    return timeStr >= start && timeStr < end;
}
/**
 * Check if a timestamp falls within the break window
 */
function isWithinBreakWindow(timestamp, rules = exports.DEFAULT_RULES) {
    const tz = rules.timezone;
    const zonedTime = (0, date_fns_tz_1.utcToZonedTime)(timestamp, tz);
    const timeStr = (0, date_fns_tz_1.format)(zonedTime, 'HH:mm', { timeZone: tz });
    const { start, end } = rules.breakWindow;
    // Break window typically doesn't cross midnight, but handle it anyway
    if (end < start) {
        return timeStr >= start || timeStr < end;
    }
    return timeStr >= start && timeStr < end;
}
/**
 * Get the current time in the organization's timezone
 */
function getCurrentTimeInTz(timezone = exports.DEFAULT_TIMEZONE) {
    return (0, date_fns_tz_1.utcToZonedTime)(new Date(), timezone);
}
/**
 * Convert a local time string to UTC
 */
function localTimeToUtc(dateStr, timeStr, timezone = exports.DEFAULT_TIMEZONE) {
    const localDateTime = (0, date_fns_1.parse)(`${dateStr} ${timeStr}`, 'yyyy-MM-dd HH:mm', new Date());
    return (0, date_fns_tz_1.zonedTimeToUtc)(localDateTime, timezone);
}
/**
 * Format a date in the organization's timezone
 */
function formatInTz(date, formatStr, timezone = exports.DEFAULT_TIMEZONE) {
    return (0, date_fns_tz_1.format)((0, date_fns_tz_1.utcToZonedTime)(date, timezone), formatStr, { timeZone: timezone });
}
/**
 * Get the start and end of a day in the organization's timezone
 */
function getDayBoundariesInTz(date, timezone = exports.DEFAULT_TIMEZONE) {
    const zonedDate = (0, date_fns_tz_1.utcToZonedTime)(date, timezone);
    const dayStart = (0, date_fns_1.startOfDay)(zonedDate);
    const dayEnd = (0, date_fns_1.addDays)(dayStart, 1);
    return {
        start: (0, date_fns_tz_1.zonedTimeToUtc)(dayStart, timezone),
        end: (0, date_fns_tz_1.zonedTimeToUtc)(dayEnd, timezone),
    };
}
/**
 * Check if samples indicate activity (mouse or keyboard)
 */
function hasActivity(mouseDelta, keyCount) {
    return mouseDelta > 0 || keyCount > 0;
}
/**
 * Determine if a span of samples represents idle time
 * @param samples - Array of samples with mouseDelta and keyCount
 * @param thresholdSeconds - Idle threshold in seconds
 * @returns true if all samples show no activity
 */
function isIdleSpan(samples, thresholdSeconds = 300) {
    if (samples.length === 0)
        return false;
    return samples.every(s => !hasActivity(s.mouseDelta, s.keyCount));
}
