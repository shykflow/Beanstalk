import { PrismaService } from '../prisma/prisma.service';
export declare class RollupService {
    private prisma;
    constructor(prisma: PrismaService);
    rollupUserActivity(userId: string, from: Date, to: Date): Promise<{
        processed: number;
    } | undefined>;
    private groupByMinute;
    private mergeContiguous;
}
