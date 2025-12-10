import { Injectable, BadRequestException } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import { PrismaService } from '../prisma/prisma.service';
import { RollupService } from './rollup.service';
import { ActivityBatchItem } from '@time-tracker/shared';
import {
  isWithinCheckinWindow,
  isWithinBreakWindow,
} from '@time-tracker/shared';

@Injectable()
export class ActivityService {
  constructor(
    private prisma: PrismaService,
    @InjectQueue('activity-rollup') private rollupQueue: Queue,
    private rollupService: RollupService,
  ) {}

  async startSession(userId: string, deviceId: string, platform: string) {
    // Find and properly close any existing active sessions for this device
    const existingSessions = await this.prisma.deviceSession.findMany({
      where: {
        userId,
        deviceId,
        endedAt: null,
      },
    });

    // Process each existing session
    for (const oldSession of existingSessions) {
      console.log(`⚠️ Found unclosed session ${oldSession.id}, closing and processing...`);
      
      // Close the session
      await this.prisma.deviceSession.update({
        where: { id: oldSession.id },
        data: { endedAt: new Date() },
      });

      // Trigger rollup for the old session to process any remaining samples
      const from = oldSession.startedAt;
      const to = new Date();
      
      try {
        await this.rollupQueue.add('rollup-user', {
          userId: oldSession.userId,
          from,
          to,
        });
        console.log(`🔄 Queued rollup for unclosed session ${oldSession.id}`);
      } catch (error) {
        console.log(`⚠️ Redis unavailable, running rollup directly for unclosed session`);
        await this.rollupService.rollupUserActivity(oldSession.userId, from, to);
      }
    }

    // Create new session
    const session = await this.prisma.deviceSession.create({
      data: {
        userId,
        deviceId,
        platform,
        startedAt: new Date(),
      },
    });

    console.log(`✅ Created new session ${session.id}`);
    return session;
  }

  async stopSession(sessionId: string) {
    const session = await this.prisma.deviceSession.findUnique({
      where: { id: sessionId },
    });

    if (!session) {
      throw new BadRequestException('Session not found');
    }

    const updatedSession = await this.prisma.deviceSession.update({
      where: { id: sessionId },
      data: { endedAt: new Date() },
    });

    // Trigger final rollup for session time range to process any remaining samples
    const from = session.startedAt;
    const to = new Date();

    try {
      await this.rollupQueue.add('rollup-user', {
        userId: session.userId,
        from,
        to,
      });
      console.log(`🔄 Queued final rollup for session ${sessionId}`);
    } catch (error) {
      console.log(`⚠️ Redis unavailable, running final rollup directly`);
      await this.rollupService.rollupUserActivity(session.userId, from, to);
    }

    return updatedSession;
  }

  async batchUpload(userId: string, samples: ActivityBatchItem[]) {
    console.log(`📥 Received batch upload: ${samples.length} samples from user ${userId}`);
    
    if (samples.length === 0) {
      return { inserted: 0 };
    }

    // Get organization schedule
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      include: {
        organization: {
          include: { schedule: true },
        },
      },
    });

    if (!user) {
      throw new BadRequestException('User not found');
    }

    if (!user.organization.schedule) {
      throw new BadRequestException('Organization schedule not configured');
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

    console.log(`⏰ Schedule: Check-in ${schedule.checkinStart}-${schedule.checkinEnd}, Break ${schedule.breakStart}-${schedule.breakEnd}, TZ: ${schedule.tz}`);
    
    // Filter and validate samples
    // Only reject samples outside working hours or during break
    // IDLE samples are accepted and will be marked as IDLE during rollup
    const validSamples = samples.filter((sample, index) => {
      const timestamp = new Date(sample.capturedAt);
      const isInCheckin = isWithinCheckinWindow(timestamp, rules);
      const isInBreak = isWithinBreakWindow(timestamp, rules);
      
      if (index === 0) {
        console.log(`🔍 Sample check: Time=${timestamp.toISOString()}, InCheckin=${isInCheckin}, InBreak=${isInBreak}`);
      }

      // Reject if outside check-in window
      if (!isInCheckin) {
        if (index === 0) console.log(`❌ Rejected: Outside check-in window`);
        return false;
      }

      // Reject if during break
      if (isInBreak) {
        if (index === 0) console.log(`❌ Rejected: During break time`);
        return false;
      }

      // Accept all samples within working hours (both ACTIVE and IDLE)
      return true;
    });

    // Batch insert
    if (validSamples.length > 0) {
      await this.prisma.activitySample.createMany({
        data: validSamples.map((sample) => ({
          userId,
          capturedAt: new Date(sample.capturedAt),
          mouseDelta: sample.mouseDelta,
          keyCount: sample.keyCount,
          deviceSessionId: sample.deviceSessionId || null,
        })),
      });

      console.log(`✅ Inserted ${validSamples.length} samples into database`);

      // Expand time range to include previous entries for merging
      const firstSampleTime = new Date(validSamples[0].capturedAt);
      const lastSampleTime = new Date(validSamples[validSamples.length - 1].capturedAt);
      
      // Process from 5 minutes before first sample to allow merging with previous entries
      const from = new Date(firstSampleTime.getTime() - 5 * 60 * 1000);
      const to = lastSampleTime;

      // Try queue, fallback to direct call if Redis fails
      try {
        await this.rollupQueue.add('rollup-user', { userId, from, to });
        console.log(`🔄 Queued rollup job for user ${userId}`);
      } catch (error) {
        console.log(`⚠️ Redis unavailable, running rollup directly`);
        await this.rollupService.rollupUserActivity(userId, from, to);
      }
    }

    const result = { inserted: validSamples.length, rejected: samples.length - validSamples.length };
    console.log(`📊 Result: Inserted ${result.inserted}, Rejected ${result.rejected}`);
    
    return result;
  }

  async getRecentActivity(userId: string, limit: number = 100) {
    return this.prisma.activitySample.findMany({
      where: { userId },
      orderBy: { capturedAt: 'desc' },
      take: limit,
    });
  }

  async triggerRollup(userId: string) {
    const now = new Date();
    
    // Find active session to get start time
    const activeSession = await this.prisma.deviceSession.findFirst({
      where: {
        userId,
        endedAt: null,
      },
      orderBy: { startedAt: 'desc' },
    });
    
    // Process from session start (or last 10 minutes if no active session)
    const from = activeSession 
      ? activeSession.startedAt 
      : new Date(now.getTime() - 10 * 60 * 1000);
    
    try {
      await this.rollupQueue.add('rollup-user', {
        userId,
        from,
        to: now,
      });
      console.log(`🔄 Rollup queued for user ${userId} from ${from.toISOString()}`);
      return { success: true, message: 'Rollup triggered' };
    } catch (error) {
      console.log(`⚠️ Redis unavailable, running rollup directly`);
      await this.rollupService.rollupUserActivity(userId, from, now);
      return { success: true, message: 'Rollup completed directly' };
    }
  }
}
