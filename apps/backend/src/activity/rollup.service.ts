import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import {
  isWithinCheckinWindow,
  isWithinBreakWindow,
  hasActivity,
  DEFAULT_RULES,
} from '@time-tracker/shared';
import { startOfMinute, addMinutes, isBefore, isAfter } from 'date-fns';

interface MinuteBucket {
  start: Date;
  end: Date;
  samples: Array<{ mouseDelta: number; keyCount: number }>;
}

@Injectable()
export class RollupService {
  constructor(private prisma: PrismaService) {}

  async rollupUserActivity(userId: string, from: Date, to: Date) {
    // Get user's organization schedule
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      include: {
        organization: {
          include: { schedule: true },
        },
      },
    });

    if (!user) {
      return;
    }

    const schedule = user.organization.schedule || {
      tz: DEFAULT_RULES.timezone,
      checkinStart: DEFAULT_RULES.checkinWindow.start,
      checkinEnd: DEFAULT_RULES.checkinWindow.end,
      breakStart: DEFAULT_RULES.breakWindow.start,
      breakEnd: DEFAULT_RULES.breakWindow.end,
      idleThresholdSeconds: DEFAULT_RULES.idleThresholdSeconds,
    };

    const rules = {
      timezone: schedule.tz,
      checkinWindow: {
        start: schedule.checkinStart,
        end: schedule.checkinEnd,
      },
      breakWindow: {
        start: schedule.breakStart,
        end: schedule.breakEnd,
      },
      idleThresholdSeconds: schedule.idleThresholdSeconds,
    };

    // Fetch samples in the time range
    const samples = await this.prisma.activitySample.findMany({
      where: {
        userId,
        capturedAt: {
          gte: from,
          lte: to,
        },
      },
      orderBy: { capturedAt: 'asc' },
    });

    if (samples.length === 0) {
      return;
    }

    // Group samples by minute
    const minuteBuckets = this.groupByMinute(samples);

    // Process each minute
    const entries: Array<{
      userId: string;
      startedAt: Date;
      endedAt: Date;
      kind: 'ACTIVE' | 'IDLE';
      source: 'AUTO';
    }> = [];

    for (const bucket of minuteBuckets) {
      // Skip if outside check-in window
      if (!isWithinCheckinWindow(bucket.start, rules)) {
        continue;
      }

      // Skip if during break
      if (isWithinBreakWindow(bucket.start, rules)) {
        continue;
      }

      // Check if minute has activity
      const active = bucket.samples.some((s) => hasActivity(s.mouseDelta, s.keyCount));

      if (active) {
        entries.push({
          userId,
          startedAt: bucket.start,
          endedAt: bucket.end,
          kind: 'ACTIVE',
          source: 'AUTO',
        });
      }
    }

    // Merge contiguous active minutes
    const merged = this.mergeContiguous(entries);

    // Delete existing entries in this range and insert new ones
    await this.prisma.$transaction(async (tx) => {
      await tx.timeEntry.deleteMany({
        where: {
          userId,
          startedAt: { gte: from },
          endedAt: { lte: to },
          source: 'AUTO',
        },
      });

      if (merged.length > 0) {
        await tx.timeEntry.createMany({
          data: merged,
        });
      }
    });

    return { processed: merged.length };
  }

  private groupByMinute(
    samples: Array<{
      capturedAt: Date;
      mouseDelta: number;
      keyCount: number;
    }>,
  ): MinuteBucket[] {
    const buckets = new Map<number, MinuteBucket>();

    for (const sample of samples) {
      const minuteStart = startOfMinute(sample.capturedAt);
      const minuteEnd = addMinutes(minuteStart, 1);
      const key = minuteStart.getTime();

      if (!buckets.has(key)) {
        buckets.set(key, {
          start: minuteStart,
          end: minuteEnd,
          samples: [],
        });
      }

      buckets.get(key)!.samples.push({
        mouseDelta: sample.mouseDelta,
        keyCount: sample.keyCount,
      });
    }

    return Array.from(buckets.values()).sort((a, b) => a.start.getTime() - b.start.getTime());
  }

  private mergeContiguous(
    entries: Array<{
      userId: string;
      startedAt: Date;
      endedAt: Date;
      kind: 'ACTIVE' | 'IDLE';
      source: 'AUTO';
    }>,
  ) {
    if (entries.length === 0) return [];

    const merged: typeof entries = [];
    let current = { ...entries[0] };

    for (let i = 1; i < entries.length; i++) {
      const next = entries[i];

      // If next entry starts where current ends, merge them
      if (
        next.startedAt.getTime() === current.endedAt.getTime() &&
        next.kind === current.kind
      ) {
        current.endedAt = next.endedAt;
      } else {
        merged.push(current);
        current = { ...next };
      }
    }

    merged.push(current);
    return merged;
  }
}
