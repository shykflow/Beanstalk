import { PrismaService } from '../prisma/prisma.service';
export declare class ExportService {
    private prisma;
    constructor(prisma: PrismaService);
    exportToCSV(orgId: string, from: Date, to: Date): Promise<string>;
    exportSummaryToCSV(orgId: string, from: Date, to: Date): Promise<string>;
}
