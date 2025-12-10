import { zonedTimeToUtc, utcToZonedTime, format } from 'date-fns-tz';
import { addDays, isWithinInterval, parse, startOfDay } from 'date-fns';

export interface TimeWindow {
  start: string; // HH:mm format
  end: string;   // HH:mm format
}

export interface ScheduleRules {
  timezone: string;
  checkinWindow: TimeWindow;
  breakWindow: TimeWindow;
  idleThresholdSeconds: number;
}

/**
 * Check if a timestamp falls within the check-in window
 * Handles midnight crossing (e.g., 16:50 -> 02:00 next day)
 */
export function isWithinCheckinWindow(
  timestamp: Date,
  rules: ScheduleRules
): boolean {
  const tz = rules.timezone;
  const zonedTime = utcToZonedTime(timestamp, tz);
  const timeStr = format(zonedTime, 'HH:mm', { timeZone: tz });
  
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
export function isWithinBreakWindow(
  timestamp: Date,
  rules: ScheduleRules
): boolean {
  const tz = rules.timezone;
  const zonedTime = utcToZonedTime(timestamp, tz);
  const timeStr = format(zonedTime, 'HH:mm', { timeZone: tz });
  
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
export function getCurrentTimeInTz(timezone: string): Date {
  return utcToZonedTime(new Date(), timezone);
}

/**
 * Convert a local time string to UTC
 */
export function localTimeToUtc(
  dateStr: string,
  timeStr: string,
  timezone: string
): Date {
  const localDateTime = parse(
    `${dateStr} ${timeStr}`,
    'yyyy-MM-dd HH:mm',
    new Date()
  );
  return zonedTimeToUtc(localDateTime, timezone);
}

/**
 * Format a date in the organization's timezone
 */
export function formatInTz(
  date: Date,
  formatStr: string,
  timezone: string
): string {
  return format(utcToZonedTime(date, timezone), formatStr, { timeZone: timezone });
}

/**
 * Get the start and end of a day in the organization's timezone
 */
export function getDayBoundariesInTz(
  date: Date,
  timezone: string
): { start: Date; end: Date } {
  const zonedDate = utcToZonedTime(date, timezone);
  const dayStart = startOfDay(zonedDate);
  const dayEnd = addDays(dayStart, 1);
  
  return {
    start: zonedTimeToUtc(dayStart, timezone),
    end: zonedTimeToUtc(dayEnd, timezone),
  };
}

/**
 * Get the working date for a timestamp based on check-in window
 * If time is before checkin end (e.g., 02:00), it belongs to previous day's shift
 * Example: 01:30 AM on Jan 15 → working date is Jan 14
 */
export function getWorkingDate(
  timestamp: Date,
  checkinEnd: string,
  timezone: string
): string {
  const zonedTime = utcToZonedTime(timestamp, timezone);
  const timeStr = format(zonedTime, 'HH:mm', { timeZone: timezone });
  
  // If current time is before checkin end (e.g., before 02:00), subtract one day
  if (timeStr < checkinEnd) {
    const previousDay = addDays(zonedTime, -1);
    return format(previousDay, 'yyyy-MM-dd', { timeZone: timezone });
  }
  
  return format(zonedTime, 'yyyy-MM-dd', { timeZone: timezone });
}

/**
 * Get working day boundaries (from checkin start to checkin end next day)
 * Example: For 2025-01-15, returns 2025-01-15 16:50 to 2025-01-16 02:00
 */
export function getWorkingDayBoundaries(
  workingDate: string,
  checkinStart: string,
  checkinEnd: string,
  timezone: string
): { start: Date; end: Date } {
  // Start: workingDate at checkinStart time
  const startStr = `${workingDate} ${checkinStart}`;
  const start = zonedTimeToUtc(startStr, timezone);
  
  // End: next day at checkinEnd time
  const nextDay = format(addDays(parse(workingDate, 'yyyy-MM-dd', new Date()), 1), 'yyyy-MM-dd');
  const endStr = `${nextDay} ${checkinEnd}`;
  const end = zonedTimeToUtc(endStr, timezone);
  
  return { start, end };
}

/**
 * Check if samples indicate activity (mouse or keyboard)
 */
export function hasActivity(mouseDelta: number, keyCount: number): boolean {
  return mouseDelta > 0 || keyCount > 0;
}

/**
 * Determine if a span of samples represents idle time
 * @param samples - Array of samples with mouseDelta and keyCount
 * @param thresholdSeconds - Idle threshold in seconds
 * @returns true if all samples show no activity
 */
export function isIdleSpan(
  samples: Array<{ mouseDelta: number; keyCount: number }>,
  thresholdSeconds: number = 300
): boolean {
  if (samples.length === 0) return false;
  return samples.every(s => !hasActivity(s.mouseDelta, s.keyCount));
}
