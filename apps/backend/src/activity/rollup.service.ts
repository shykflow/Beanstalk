import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import {
  isWithinCheckinWindow,
  isWithinBreakWindow,
  hasActivity,
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
    try {
      console.log(`🔄 Starting rollup for user ${userId} from ${from.toISOString()} to ${to.toISOString()}`);
      
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
      console.error('❌ User not found:', userId);
      return;
    }

    if (!user.organization.schedule) {
      console.error('❌ Organization schedule not configured for user:', userId);
      return;
    }

    const schedule = user.organization.schedule;

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

    console.log(`📊 Found ${samples.length} samples to process`);

    if (samples.length === 0) {
      console.log('⚠️ No samples to process');
      return;
    }

    // Group samples by minute
    const minuteBuckets = this.groupByMinute(samples);

    // Process each minute and determine ACTIVE/IDLE
    const minuteEntries: Array<{
      userId: string;
      startedAt: Date;
      endedAt: Date;
      hasActivity: boolean;
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

      minuteEntries.push({
        userId,
        startedAt: bucket.start,
        endedAt: bucket.end,
        hasActivity: active,
      });
    }

    // Apply idle threshold logic
    console.log(`🎯 Applying idle threshold: ${rules.idleThresholdSeconds}s (${Math.floor(rules.idleThresholdSeconds / 60)} minutes)`);
    const entries = this.applyIdleThreshold(minuteEntries, rules.idleThresholdSeconds);

    // Merge contiguous same-type minutes
    const merged = this.mergeContiguous(entries);

    // Smart merge: only extend same kind, replace different kind
    await this.prisma.$transaction(async (tx) => {
      if (merged.length === 0) return;

      for (const newEntry of merged) {
        // Find adjacent entry of SAME kind
        const adjacent = await tx.timeEntry.findFirst({
          where: {
            userId,
            source: 'AUTO',
            kind: newEntry.kind,
            OR: [
              { endedAt: newEntry.startedAt },
              { startedAt: newEntry.endedAt },
            ],
          },
        });

        // Find overlapping entries of ANY kind (but exclude adjacent entry)
        const overlapping = await tx.timeEntry.findMany({
          where: {
            userId,
            source: 'AUTO',
            id: adjacent ? { not: adjacent.id } : undefined,
            OR: [
              { startedAt: { gte: newEntry.startedAt, lt: newEntry.endedAt } },
              { endedAt: { gt: newEntry.startedAt, lte: newEntry.endedAt } },
              { startedAt: { lt: newEntry.startedAt }, endedAt: { gt: newEntry.endedAt } },
            ],
          },
        });

        // Delete ONLY truly overlapping entries (not adjacent)
        if (overlapping.length > 0) {
          await tx.timeEntry.deleteMany({
            where: { id: { in: overlapping.map(e => e.id) } },
          });
          console.log(`🗑️  Deleted ${overlapping.length} overlapping entries`);
        }

        // Extend adjacent entry of same kind
        if (adjacent) {
          const newStart = adjacent.startedAt < newEntry.startedAt ? adjacent.startedAt : newEntry.startedAt;
          const newEnd = adjacent.endedAt > newEntry.endedAt ? adjacent.endedAt : newEntry.endedAt;
          
          await tx.timeEntry.update({
            where: { id: adjacent.id },
            data: { startedAt: newStart, endedAt: newEnd },
          });
          console.log(`🔄 Extended ${newEntry.kind}: ${newStart.toISOString()} to ${newEnd.toISOString()}`);
        } else {
          // Create new entry
          await tx.timeEntry.create({ data: newEntry });
          console.log(`➕ Created ${newEntry.kind}: ${newEntry.startedAt.toISOString()} to ${newEntry.endedAt.toISOString()}`);
        }
      }
    }, { timeout: 15000 });

    console.log(`✅ Rollup complete: Processed ${merged.length} entries`);
    
    return { processed: merged.length };
    } catch (error) {
      console.error('❌ Rollup failed:', error);
      throw error;
    }
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

  private applyIdleThreshold(
    minuteEntries: Array<{
      userId: string;
      startedAt: Date;
      endedAt: Date;
      hasActivity: boolean;
    }>,
    idleThresholdSeconds: number,
  ): Array<{
    userId: string;
    startedAt: Date;
    endedAt: Date;
    kind: 'ACTIVE' | 'IDLE';
    source: 'AUTO';
  }> {
    const entries: Array<{
      userId: string;
      startedAt: Date;
      endedAt: Date;
      kind: 'ACTIVE' | 'IDLE';
      source: 'AUTO';
    }> = [];

    const idleThresholdMinutes = Math.floor(idleThresholdSeconds / 60);
    let consecutiveIdleCount = 0;
    let pendingIdleEntries: Array<typeof entries[0]> = [];

    console.log(`📋 Processing ${minuteEntries.length} minute entries with threshold ${idleThresholdMinutes} minutes`);

    for (let i = 0; i < minuteEntries.length; i++) {
      const entry = minuteEntries[i];

      if (entry.hasActivity) {
        // Active minute - reset idle counter and flush pending as ACTIVE
        console.log(`  ✅ Minute ${i + 1}: ACTIVE (has activity) - reset idle counter`);
        
        // Flush pending idle entries as ACTIVE (below threshold)
        if (pendingIdleEntries.length > 0) {
          console.log(`    → Flushing ${pendingIdleEntries.length} pending minutes as ACTIVE`);
          entries.push(...pendingIdleEntries);
          pendingIdleEntries = [];
        }
        consecutiveIdleCount = 0;
        
        entries.push({
          userId: entry.userId,
          startedAt: entry.startedAt,
          endedAt: entry.endedAt,
          kind: 'ACTIVE',
          source: 'AUTO',
        });
      } else {
        // Idle minute - increment counter
        consecutiveIdleCount++;
        console.log(`  ⏸️  Minute ${i + 1}: No activity - consecutive idle: ${consecutiveIdleCount}/${idleThresholdMinutes}`);

        // If already past threshold, directly add as IDLE
        if (consecutiveIdleCount > idleThresholdMinutes) {
          console.log(`    → Already past threshold, adding as IDLE`);
          entries.push({
            userId: entry.userId,
            startedAt: entry.startedAt,
            endedAt: entry.endedAt,
            kind: 'IDLE',
            source: 'AUTO',
          });
        } else {
          // Add to pending
          const pendingEntry = {
            userId: entry.userId,
            startedAt: entry.startedAt,
            endedAt: entry.endedAt,
            kind: 'ACTIVE' as const,
            source: 'AUTO' as const,
          };
          pendingIdleEntries.push(pendingEntry);

          // If threshold just reached, convert all pending to IDLE
          if (consecutiveIdleCount === idleThresholdMinutes) {
            console.log(`    → Threshold reached! Converting ${pendingIdleEntries.length} minutes to IDLE`);
            
            // Convert all pending entries to IDLE and add to entries
            const idleEntries = pendingIdleEntries.map(e => ({ ...e, kind: 'IDLE' as const }));
            entries.push(...idleEntries);
            pendingIdleEntries = [];
          }
        }
      }
    }

    // Flush remaining pending entries as ACTIVE (didn't reach threshold)
    if (pendingIdleEntries.length > 0) {
      console.log(`  → Flushing ${pendingIdleEntries.length} pending minutes as ACTIVE (threshold not reached)`);
      entries.push(...pendingIdleEntries);
    }

    const activeCount = entries.filter(e => e.kind === 'ACTIVE').length;
    const idleCount = entries.filter(e => e.kind === 'IDLE').length;
    console.log(`📊 Result: ${activeCount} ACTIVE, ${idleCount} IDLE entries`);

    return entries;
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
