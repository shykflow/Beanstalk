import { PrismaService } from '../prisma/prisma.service';
export declare class ReportsService {
    private prisma;
    constructor(prisma: PrismaService);
    getSummary(userId: string, from: Date, to: Date): Promise<{
        userId: string;
        from: Date;
        to: Date;
        totalMinutes: number;
        activeMinutes: number;
        idleMinutes: number;
        breakMinutes: number;
    }>;
    getDailyReport(orgId: string, date: Date): Promise<{
        date: string;
        users: any[];
    }>;
    getWeeklyReport(orgId: string, date: Date): Promise<{
        period: string;
        from: string;
        to: string;
        users: any[];
    }>;
    getMonthlyReport(orgId: string, date: Date): Promise<{
        period: string;
        from: string;
        to: string;
        users: any[];
    }>;
    private getAggregatedReport;
    getUserTimesheet(userId: string, from: Date, to: Date): Promise<{
        userId: string;
        from: Date;
        to: Date;
        entries: {
            id: string;
            createdAt: Date;
            userId: string;
            endedAt: Date;
            startedAt: Date;
            source: import(".prisma/client").$Enums.TimeEntrySource;
            kind: import(".prisma/client").$Enums.TimeEntryKind;
        }[];
        adjustments: {
            id: string;
            creator: {
                email: string;
                fullName: string | null;
            };
            createdAt: Date;
            userId: string;
            createdBy: string;
            reason: string;
            deltaMinutes: number;
            effectiveDate: Date;
        }[];
    }>;
}
