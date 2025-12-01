import { Queue } from 'bullmq';
import { PrismaService } from '../prisma/prisma.service';
import { ActivityBatchItem } from '@time-tracker/shared';
export declare class ActivityService {
    private prisma;
    private rollupQueue;
    constructor(prisma: PrismaService, rollupQueue: Queue);
    startSession(userId: string, deviceId: string, platform: string): Promise<{
        id: string;
        userId: string;
        deviceId: string;
        endedAt: Date | null;
        platform: string;
        startedAt: Date;
    }>;
    stopSession(sessionId: string): Promise<{
        id: string;
        userId: string;
        deviceId: string;
        endedAt: Date | null;
        platform: string;
        startedAt: Date;
    }>;
    batchUpload(userId: string, samples: ActivityBatchItem[]): Promise<{
        inserted: number;
        rejected?: undefined;
    } | {
        inserted: number;
        rejected: number;
    }>;
    getRecentActivity(userId: string, limit?: number): Promise<{
        id: bigint;
        userId: string;
        capturedAt: Date;
        mouseDelta: number;
        keyCount: number;
        deviceSessionId: string | null;
    }[]>;
}
