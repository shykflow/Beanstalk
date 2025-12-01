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
