import { Injectable, BadRequestException } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import { PrismaService } from '../prisma/prisma.service';
import { ActivityBatchItem } from '@time-tracker/shared';
import {
  isWithinCheckinWindow,
  isWithinBreakWindow,
  DEFAULT_RULES,
} from '@time-tracker/shared';

@Injectable()
export class ActivityService {
  constructor(
    private prisma: PrismaService,
    @InjectQueue('activity-rollup') private rollupQueue: Queue,
  ) {}

  async startSession(userId: string, deviceId: string, platform: string) {
    // End any existing active sessions for this device
    await this.prisma.deviceSession.updateMany({
      where: {
        userId,
        deviceId,
        endedAt: null,
      },
      data: {
        endedAt: new Date(),
      },
    });

    // Create new session
    const session = await this.prisma.deviceSession.create({
      data: {
        userId,
        deviceId,
        platform,
        startedAt: new Date(),
      },
    });

    return session;
  }

  async stopSession(sessionId: string) {
    const session = await this.prisma.deviceSession.update({
      where: { id: sessionId },
      data: { endedAt: new Date() },
    });

    // Trigger rollup for this session
    await this.rollupQueue.add('rollup-session', {
      userId: session.userId,
      sessionId: session.id,
    });

    return session;
  }

  async batchUpload(userId: string, samples: ActivityBatchItem[]) {
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

    // Filter and validate samples
    const validSamples = samples.filter((sample) => {
      const timestamp = new Date(sample.capturedAt);

      // Reject if outside check-in window
      if (!isWithinCheckinWindow(timestamp, rules)) {
        return false;
      }

      // Reject if during break
      if (isWithinBreakWindow(timestamp, rules)) {
        return false;
      }

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

      // Queue rollup job
      await this.rollupQueue.add('rollup-user', {
        userId,
        from: new Date(validSamples[0].capturedAt),
        to: new Date(validSamples[validSamples.length - 1].capturedAt),
      });
    }

    return { inserted: validSamples.length, rejected: samples.length - validSamples.length };
  }

  async getRecentActivity(userId: string, limit: number = 100) {
    return this.prisma.activitySample.findMany({
      where: { userId },
      orderBy: { capturedAt: 'desc' },
      take: limit,
    });
  }
}
