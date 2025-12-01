import { AuthService } from './auth.service';
export declare class AuthController {
    private authService;
    constructor(authService: AuthService);
    register(body: {
        email: string;
        password: string;
        fullName: string;
        orgName: string;
    }): Promise<import("@time-tracker/shared").AuthTokens>;
    login(req: any): Promise<import("@time-tracker/shared").AuthTokens>;
    refresh(body: {
        refreshToken: string;
    }): Promise<import("@time-tracker/shared").AuthTokens>;
    logout(req: any): Promise<void>;
}
