import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../prisma/prisma.service';
import { AuthTokens } from '@time-tracker/shared';
export declare class AuthService {
    private prisma;
    private jwtService;
    private config;
    constructor(prisma: PrismaService, jwtService: JwtService, config: ConfigService);
    validateUser(email: string, password: string): Promise<any>;
    login(user: any): Promise<AuthTokens>;
    register(data: {
        email: string;
        password: string;
        fullName: string;
        orgName: string;
    }): Promise<AuthTokens>;
    refreshTokens(refreshToken: string): Promise<AuthTokens>;
    private generateRefreshToken;
    logout(userId: string): Promise<void>;
}
