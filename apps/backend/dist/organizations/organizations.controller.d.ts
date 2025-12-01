import { OrganizationsService } from './organizations.service';
export declare class OrganizationsController {
    private organizationsService;
    constructor(organizationsService: OrganizationsService);
    getMyOrganization(req: any): Promise<({
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
    updateMyOrganization(req: any, body: {
        name?: string;
        timezone?: string;
    }): Promise<{
        id: string;
        createdAt: Date;
        name: string;
        timezone: string;
    }>;
    getSchedule(req: any): Promise<{
        orgId: string;
        tz: string;
        checkinStart: string;
        checkinEnd: string;
        breakStart: string;
        breakEnd: string;
        idleThresholdSeconds: number;
    }>;
    updateSchedule(req: any, body: {
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
    createAdjustment(req: any, body: {
        userId: string;
        reason: string;
        deltaMinutes: number;
        effectiveDate: string;
    }): Promise<{
        id: bigint;
        createdAt: Date;
        userId: string;
        createdBy: string;
        reason: string;
        deltaMinutes: number;
        effectiveDate: Date;
    }>;
    getAdjustments(userId: string, from?: string, to?: string): Promise<({
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
