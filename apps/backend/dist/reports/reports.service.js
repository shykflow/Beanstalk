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
Object.defineProperty(exports, "__esModule", { value: true });
exports.ReportsService = void 0;
const common_1 = require("@nestjs/common");
const prisma_service_1 = require("../prisma/prisma.service");
const date_fns_1 = require("date-fns");
let ReportsService = class ReportsService {
    constructor(prisma) {
        this.prisma = prisma;
    }
    async getSummary(userId, from, to) {
        const entries = await this.prisma.timeEntry.findMany({
            where: {
                userId,
                startedAt: { gte: from },
                endedAt: { lte: to },
            },
        });
        const summary = {
            userId,
            from,
            to,
            totalMinutes: 0,
            activeMinutes: 0,
            idleMinutes: 0,
            breakMinutes: 0,
        };
        for (const entry of entries) {
            const minutes = (0, date_fns_1.differenceInMinutes)(entry.endedAt, entry.startedAt);
            summary.totalMinutes += minutes;
            if (entry.kind === 'ACTIVE') {
                summary.activeMinutes += minutes;
            }
            else if (entry.kind === 'IDLE') {
                summary.idleMinutes += minutes;
            }
            else if (entry.kind === 'BREAK') {
                summary.breakMinutes += minutes;
            }
        }
        return summary;
    }
    async getDailyReport(orgId, date) {
        const from = (0, date_fns_1.startOfDay)(date);
        const to = (0, date_fns_1.endOfDay)(date);
        const users = await this.prisma.user.findMany({
            where: { orgId, isActive: true },
            select: { id: true, fullName: true, email: true },
        });
        const report = {
            date: date.toISOString().split('T')[0],
            users: [],
        };
        for (const user of users) {
            const entries = await this.prisma.timeEntry.findMany({
                where: {
                    userId: user.id,
                    startedAt: { gte: from },
                    endedAt: { lte: to },
                },
                orderBy: { startedAt: 'asc' },
            });
            let totalMinutes = 0;
            let activeMinutes = 0;
            let idleMinutes = 0;
            let breakMinutes = 0;
            for (const entry of entries) {
                const minutes = (0, date_fns_1.differenceInMinutes)(entry.endedAt, entry.startedAt);
                totalMinutes += minutes;
                if (entry.kind === 'ACTIVE')
                    activeMinutes += minutes;
                else if (entry.kind === 'IDLE')
                    idleMinutes += minutes;
                else if (entry.kind === 'BREAK')
                    breakMinutes += minutes;
            }
            report.users.push({
                userId: user.id,
                userName: user.fullName || user.email,
                totalMinutes,
                activeMinutes,
                idleMinutes,
                breakMinutes,
                entries: entries.map(e => ({
                    ...e,
                    id: e.id.toString(),
                })),
            });
        }
        return report;
    }
    async getWeeklyReport(orgId, date) {
        const from = (0, date_fns_1.startOfWeek)(date, { weekStartsOn: 1 });
        const to = (0, date_fns_1.endOfWeek)(date, { weekStartsOn: 1 });
        return this.getAggregatedReport(orgId, from, to, 'weekly');
    }
    async getMonthlyReport(orgId, date) {
        const from = (0, date_fns_1.startOfMonth)(date);
        const to = (0, date_fns_1.endOfMonth)(date);
        return this.getAggregatedReport(orgId, from, to, 'monthly');
    }
    async getAggregatedReport(orgId, from, to, period) {
        const users = await this.prisma.user.findMany({
            where: { orgId, isActive: true },
            select: { id: true, fullName: true, email: true },
        });
        const report = {
            period,
            from: from.toISOString(),
            to: to.toISOString(),
            users: [],
        };
        for (const user of users) {
            const summary = await this.getSummary(user.id, from, to);
            report.users.push({
                userName: user.fullName || user.email,
                ...summary,
            });
        }
        return report;
    }
    async getUserTimesheet(userId, from, to) {
        const entries = await this.prisma.timeEntry.findMany({
            where: {
                userId,
                startedAt: { gte: from },
                endedAt: { lte: to },
            },
            orderBy: { startedAt: 'asc' },
        });
        const adjustments = await this.prisma.adjustment.findMany({
            where: {
                userId,
                effectiveDate: {
                    gte: from,
                    lte: to,
                },
            },
            include: {
                creator: {
                    select: {
                        fullName: true,
                        email: true,
                    },
                },
            },
        });
        return {
            userId,
            from,
            to,
            entries: entries.map(e => ({
                ...e,
                id: e.id.toString(),
            })),
            adjustments: adjustments.map(a => ({
                ...a,
                id: a.id.toString(),
            })),
        };
    }
};
exports.ReportsService = ReportsService;
exports.ReportsService = ReportsService = __decorate([
    (0, common_1.Injectable)(),
    __metadata("design:paramtypes", [prisma_service_1.PrismaService])
], ReportsService);
//# sourceMappingURL=reports.service.js.map