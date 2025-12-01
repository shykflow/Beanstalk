import { Response } from 'express';
import { ReportsService } from './reports.service';
import { ExportService } from './export.service';
export declare class ReportsController {
    private reportsService;
    private exportService;
    constructor(reportsService: ReportsService, exportService: ExportService);
    getSummary(userId: string, from: string, to: string): Promise<{
        userId: string;
        from: Date;
        to: Date;
        totalMinutes: number;
        activeMinutes: number;
        idleMinutes: number;
        breakMinutes: number;
    }>;
    getDailyReport(req: any, date: string): Promise<{
        date: string;
        users: any[];
    }>;
    getWeeklyReport(req: any, week: string): Promise<{
        period: string;
        from: string;
        to: string;
        users: any[];
    }>;
    getMonthlyReport(req: any, month: string): Promise<{
        period: string;
        from: string;
        to: string;
        users: any[];
    }>;
    getTimesheet(userId: string, from: string, to: string): Promise<{
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
    exportCSV(req: any, from: string, to: string, res: Response): Promise<void>;
    exportSummaryCSV(req: any, from: string, to: string, res: Response): Promise<void>;
}
