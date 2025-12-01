import { PrismaService } from '../prisma/prisma.service';
import { UserRole } from '@time-tracker/shared';
export declare class UsersService {
    private prisma;
    constructor(prisma: PrismaService);
    findAll(orgId: string): Promise<{
        id: string;
        email: string;
        fullName: string | null;
        role: import(".prisma/client").$Enums.UserRole;
        isActive: boolean;
        createdAt: Date;
    }[]>;
    findOne(id: string): Promise<{
        id: string;
        email: string;
        orgId: string;
        fullName: string | null;
        role: import(".prisma/client").$Enums.UserRole;
        isActive: boolean;
        createdAt: Date;
    }>;
    create(data: {
        email: string;
        password: string;
        fullName: string;
        role: UserRole;
        orgId: string;
    }): Promise<{
        id: string;
        email: string;
        fullName: string | null;
        role: import(".prisma/client").$Enums.UserRole;
        isActive: boolean;
        createdAt: Date;
    }>;
    update(id: string, data: {
        fullName?: string;
        role?: UserRole;
        isActive?: boolean;
    }): Promise<{
        id: string;
        email: string;
        fullName: string | null;
        role: import(".prisma/client").$Enums.UserRole;
        isActive: boolean;
        createdAt: Date;
    }>;
    delete(id: string): Promise<void>;
}
