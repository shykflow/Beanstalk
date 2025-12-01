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
exports.ReportsController = void 0;
const common_1 = require("@nestjs/common");
const reports_service_1 = require("./reports.service");
const export_service_1 = require("./export.service");
const jwt_auth_guard_1 = require("../auth/guards/jwt-auth.guard");
const roles_guard_1 = require("../auth/guards/roles.guard");
const roles_decorator_1 = require("../auth/decorators/roles.decorator");
const shared_1 = require("@time-tracker/shared");
const date_fns_1 = require("date-fns");
let ReportsController = class ReportsController {
    constructor(reportsService, exportService) {
        this.reportsService = reportsService;
        this.exportService = exportService;
    }
    async getSummary(userId, from, to) {
        return this.reportsService.getSummary(userId, new Date(from), new Date(to));
    }
    async getDailyReport(req, date) {
        try {
            const reportDate = date ? new Date(date) : new Date();
            console.log('Getting daily report for orgId:', req.user.orgId, 'date:', reportDate);
            const result = await this.reportsService.getDailyReport(req.user.orgId, reportDate);
            console.log('Daily report result:', JSON.stringify(result, null, 2));
            return result;
        }
        catch (error) {
            console.error('Error in getDailyReport:', error);
            throw error;
        }
    }
    async getWeeklyReport(req, week) {
        const date = week
            ? (0, date_fns_1.parse)(week, "'W'II-yyyy", new Date())
            : new Date();
        return this.reportsService.getWeeklyReport(req.user.orgId, date);
    }
    async getMonthlyReport(req, month) {
        const date = month ? (0, date_fns_1.parse)(month, 'yyyy-MM', new Date()) : new Date();
        return this.reportsService.getMonthlyReport(req.user.orgId, date);
    }
    async getTimesheet(userId, from, to) {
        return this.reportsService.getUserTimesheet(userId, new Date(from), new Date(to));
    }
    async exportCSV(req, from, to, res) {
        const csv = await this.exportService.exportToCSV(req.user.orgId, new Date(from), new Date(to));
        res.setHeader('Content-Type', 'text/csv');
        res.setHeader('Content-Disposition', `attachment; filename=timesheet-${from}-${to}.csv`);
        res.send(csv);
    }
    async exportSummaryCSV(req, from, to, res) {
        const csv = await this.exportService.exportSummaryToCSV(req.user.orgId, new Date(from), new Date(to));
        res.setHeader('Content-Type', 'text/csv');
        res.setHeader('Content-Disposition', `attachment; filename=summary-${from}-${to}.csv`);
        res.send(csv);
    }
};
exports.ReportsController = ReportsController;
__decorate([
    (0, common_1.Get)('summary'),
    __param(0, (0, common_1.Query)('userId', common_1.ParseUUIDPipe)),
    __param(1, (0, common_1.Query)('from')),
    __param(2, (0, common_1.Query)('to')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, String, String]),
    __metadata("design:returntype", Promise)
], ReportsController.prototype, "getSummary", null);
__decorate([
    (0, common_1.Get)('daily'),
    (0, roles_decorator_1.Roles)(shared_1.UserRole.OWNER, shared_1.UserRole.ADMIN, shared_1.UserRole.MANAGER),
    __param(0, (0, common_1.Request)()),
    __param(1, (0, common_1.Query)('date')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, String]),
    __metadata("design:returntype", Promise)
], ReportsController.prototype, "getDailyReport", null);
__decorate([
    (0, common_1.Get)('weekly'),
    (0, roles_decorator_1.Roles)(shared_1.UserRole.OWNER, shared_1.UserRole.ADMIN, shared_1.UserRole.MANAGER),
    __param(0, (0, common_1.Request)()),
    __param(1, (0, common_1.Query)('week')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, String]),
    __metadata("design:returntype", Promise)
], ReportsController.prototype, "getWeeklyReport", null);
__decorate([
    (0, common_1.Get)('monthly'),
    (0, roles_decorator_1.Roles)(shared_1.UserRole.OWNER, shared_1.UserRole.ADMIN, shared_1.UserRole.MANAGER),
    __param(0, (0, common_1.Request)()),
    __param(1, (0, common_1.Query)('month')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, String]),
    __metadata("design:returntype", Promise)
], ReportsController.prototype, "getMonthlyReport", null);
__decorate([
    (0, common_1.Get)('timesheet'),
    __param(0, (0, common_1.Query)('userId', common_1.ParseUUIDPipe)),
    __param(1, (0, common_1.Query)('from')),
    __param(2, (0, common_1.Query)('to')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, String, String]),
    __metadata("design:returntype", Promise)
], ReportsController.prototype, "getTimesheet", null);
__decorate([
    (0, common_1.Get)('export/csv'),
    (0, roles_decorator_1.Roles)(shared_1.UserRole.OWNER, shared_1.UserRole.ADMIN, shared_1.UserRole.MANAGER),
    __param(0, (0, common_1.Request)()),
    __param(1, (0, common_1.Query)('from')),
    __param(2, (0, common_1.Query)('to')),
    __param(3, (0, common_1.Res)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, String, String, Object]),
    __metadata("design:returntype", Promise)
], ReportsController.prototype, "exportCSV", null);
__decorate([
    (0, common_1.Get)('export/summary-csv'),
    (0, roles_decorator_1.Roles)(shared_1.UserRole.OWNER, shared_1.UserRole.ADMIN, shared_1.UserRole.MANAGER),
    __param(0, (0, common_1.Request)()),
    __param(1, (0, common_1.Query)('from')),
    __param(2, (0, common_1.Query)('to')),
    __param(3, (0, common_1.Res)()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, String, String, Object]),
    __metadata("design:returntype", Promise)
], ReportsController.prototype, "exportSummaryCSV", null);
exports.ReportsController = ReportsController = __decorate([
    (0, common_1.Controller)('reports'),
    (0, common_1.UseGuards)(jwt_auth_guard_1.JwtAuthGuard, roles_guard_1.RolesGuard),
    __metadata("design:paramtypes", [reports_service_1.ReportsService,
        export_service_1.ExportService])
], ReportsController);
//# sourceMappingURL=reports.controller.js.map