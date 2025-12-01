"use strict";
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var __param = (this && this.__param) || function (paramIndex, decorator) {
    return function (target, key) { decorator(target, key, paramIndex); }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.OrganizationsController = void 0;
const common_1 = require("@nestjs/common");
const organizations_service_1 = require("./organizations.service");
const jwt_auth_guard_1 = require("../auth/guards/jwt-auth.guard");
const roles_guard_1 = require("../auth/guards/roles.guard");
const roles_decorator_1 = require("../auth/decorators/roles.decorator");
const shared_1 = require("@time-tracker/shared");
let OrganizationsController = class OrganizationsController {
    constructor(organizationsService) {
        this.organizationsService = organizationsService;
    }
    async getMyOrganization(req) {
        return this.organizationsService.getOrganization(req.user.orgId);
    }
    async updateMyOrganization(req, body) {
        return this.organizationsService.updateOrganization(req.user.orgId, body);
    }
    async getSchedule(req) {
        return this.organizationsService.getSchedule(req.user.orgId);
    }
    async updateSchedule(req, body) {
        return this.organizationsService.updateSchedule(req.user.orgId, body);
    }
    async createAdjustment(req, body) {
        return this.organizationsService.createAdjustment({
            userId: body.userId,
            createdBy: req.user.id,
            reason: body.reason,
            deltaMinutes: body.deltaMinutes,
            effectiveDate: new Date(body.effectiveDate),
        });
    }
    async getAdjustments(userId, from, to) {
        return this.organizationsService.getAdjustments(userId, from ? new Date(from) : undefined, to ? new Date(to) : undefined);
    }
};
exports.OrganizationsController = OrganizationsController;
__decorate([
    (0, common_1.Get)('me'),
    __param(0, (0, common_1.Request)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], OrganizationsController.prototype, "getMyOrganization", null);
__decorate([
    (0, common_1.Put)('me'),
    (0, roles_decorator_1.Roles)(shared_1.UserRole.OWNER, shared_1.UserRole.ADMIN),
    __param(0, (0, common_1.Request)()),
    __param(1, (0, common_1.Body)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], OrganizationsController.prototype, "updateMyOrganization", null);
__decorate([
    (0, common_1.Get)('schedule'),
    __param(0, (0, common_1.Request)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object]),
    __metadata("design:returntype", Promise)
], OrganizationsController.prototype, "getSchedule", null);
__decorate([
    (0, common_1.Put)('schedule'),
    (0, roles_decorator_1.Roles)(shared_1.UserRole.OWNER, shared_1.UserRole.ADMIN),
    __param(0, (0, common_1.Request)()),
    __param(1, (0, common_1.Body)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], OrganizationsController.prototype, "updateSchedule", null);
__decorate([
    (0, common_1.Post)('adjustments'),
    (0, roles_decorator_1.Roles)(shared_1.UserRole.OWNER, shared_1.UserRole.ADMIN, shared_1.UserRole.MANAGER),
    __param(0, (0, common_1.Request)()),
    __param(1, (0, common_1.Body)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], OrganizationsController.prototype, "createAdjustment", null);
__decorate([
    (0, common_1.Get)('adjustments'),
    __param(0, (0, common_1.Query)('userId', common_1.ParseUUIDPipe)),
    __param(1, (0, common_1.Query)('from')),
    __param(2, (0, common_1.Query)('to')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, String, String]),
    __metadata("design:returntype", Promise)
], OrganizationsController.prototype, "getAdjustments", null);
exports.OrganizationsController = OrganizationsController = __decorate([
    (0, common_1.Controller)('organizations'),
    (0, common_1.UseGuards)(jwt_auth_guard_1.JwtAuthGuard, roles_guard_1.RolesGuard),
    __metadata("design:paramtypes", [organizations_service_1.OrganizationsService])
], OrganizationsController);
//# sourceMappingURL=organizations.controller.js.map