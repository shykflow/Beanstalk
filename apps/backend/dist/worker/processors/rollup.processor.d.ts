import { WorkerHost } from '@nestjs/bullmq';
import { Job } from 'bullmq';
import { RollupService } from '../../activity/rollup.service';
export declare class RollupProcessor extends WorkerHost {
    private rollupService;
    constructor(rollupService: RollupService);
    process(job: Job<any, any, string>): Promise<any>;
    private handleRollupUser;
    private handleRollupSession;
}
