import { UsersService } from './users.service';
import { UserRole } from '@time-tracker/shared';
export declare class UsersController {
    private usersService;
    constructor(usersService: UsersService);
    findAll(req: any): Promise<{
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
    create(req: any, body: {
        email: string;
        password: string;
        fullName: string;
        role: UserRole;
    }): Promise<{
        id: string;
        email: string;
        fullName: string | null;
        role: import(".prisma/client").$Enums.UserRole;
        isActive: boolean;
        createdAt: Date;
    }>;
    update(id: string, body: {
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
    delete(id: string): Promise<{
        message: string;
    }>;
}
