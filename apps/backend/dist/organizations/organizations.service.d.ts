import { PrismaService } from '../prisma/prisma.service';
export declare class OrganizationsService {
    private prisma;
    constructor(prisma: PrismaService);
    getOrganization(orgId: string): Promise<({
        schedule: {
            orgId: string;
            tz: string;
            checkinStart: string;
            checkinEnd: string;
            breakStart: string;
            breakEnd: string;
            idleThresholdSeconds: number;
        } | null;
    } & {
        id: string;
        createdAt: Date;
        name: string;
        timezone: string;
    }) | null>;
    updateOrganization(orgId: string, data: {
        name?: string;
        timezone?: string;
    }): Promise<{
        id: string;
        createdAt: Date;
        name: string;
        timezone: string;
    }>;
    getSchedule(orgId: string): Promise<{
        orgId: string;
        tz: string;
        checkinStart: string;
        checkinEnd: string;
        breakStart: string;
        breakEnd: string;
        idleThresholdSeconds: number;
    }>;
    updateSchedule(orgId: string, data: {
        tz?: string;
        checkinStart?: string;
        checkinEnd?: string;
        breakStart?: string;
        breakEnd?: string;
        idleThresholdSeconds?: number;
    }): Promise<{
        orgId: string;
        tz: string;
        checkinStart: string;
        checkinEnd: string;
        breakStart: string;
        breakEnd: string;
        idleThresholdSeconds: number;
    }>;
    createAdjustment(data: {
        userId: string;
        createdBy: string;
        reason: string;
        deltaMinutes: number;
        effectiveDate: Date;
    }): Promise<{
        id: bigint;
        createdAt: Date;
        userId: string;
        createdBy: string;
        reason: string;
        deltaMinutes: number;
        effectiveDate: Date;
    }>;
    getAdjustments(userId: string, from?: Date, to?: Date): Promise<({
        creator: {
            email: string;
            fullName: string | null;
        };
    } & {
        id: bigint;
        createdAt: Date;
        userId: string;
        createdBy: string;
        reason: string;
        deltaMinutes: number;
        effectiveDate: Date;
    })[]>;
}
