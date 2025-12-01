import { ActivityService } from './activity.service';
import { ActivityBatchItem } from '@time-tracker/shared';
export declare class ActivityController {
    private activityService;
    constructor(activityService: ActivityService);
    startSession(req: any, body: {
        deviceId: string;
        platform: string;
    }): Promise<{
        id: string;
        userId: string;
        deviceId: string;
        endedAt: Date | null;
        platform: string;
        startedAt: Date;
    }>;
    stopSession(body: {
        sessionId: string;
    }): Promise<{
        id: string;
        userId: string;
        deviceId: string;
        endedAt: Date | null;
        platform: string;
        startedAt: Date;
    }>;
    batchUpload(req: any, body: {
        samples: ActivityBatchItem[];
    }): Promise<{
        inserted: number;
        rejected?: undefined;
    } | {
        inserted: number;
        rejected: number;
    }>;
    getRecent(req: any, limit?: string): Promise<{
        id: bigint;
        userId: string;
        capturedAt: Date;
        mouseDelta: number;
        keyCount: number;
        deviceSessionId: string | null;
    }[]>;
}
