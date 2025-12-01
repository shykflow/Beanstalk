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
exports.ExportService = void 0;
const common_1 = require("@nestjs/common");
const prisma_service_1 = require("../prisma/prisma.service");
const date_fns_1 = require("date-fns");
let ExportService = class ExportService {
    constructor(prisma) {
        this.prisma = prisma;
    }
    async exportToCSV(orgId, from, to) {
        const users = await this.prisma.user.findMany({
            where: { orgId, isActive: true },
            select: { id: true, fullName: true, email: true },
        });
        const rows = [
            'User,Email,Date,Start Time,End Time,Duration (minutes),Type,Source',
        ];
        for (const user of users) {
            const entries = await this.prisma.timeEntry.findMany({
                where: {
                    userId: user.id,
                    startedAt: { gte: from },
                    endedAt: { lte: to },
                },
                orderBy: { startedAt: 'asc' },
            });
            for (const entry of entries) {
                const duration = (0, date_fns_1.differenceInMinutes)(entry.endedAt, entry.startedAt);
                const date = entry.startedAt.toISOString().split('T')[0];
                const startTime = entry.startedAt.toISOString();
                const endTime = entry.endedAt.toISOString();
                rows.push(`"${user.fullName || user.email}","${user.email}","${date}","${startTime}","${endTime}",${duration},"${entry.kind}","${entry.source}"`);
            }
        }
        return rows.join('\n');
    }
    async exportSummaryToCSV(orgId, from, to) {
        const users = await this.prisma.user.findMany({
            where: { orgId, isActive: true },
            select: { id: true, fullName: true, email: true },
        });
        const rows = [
            'User,Email,Total Minutes,Active Minutes,Idle Minutes,Break Minutes,Total Hours',
        ];
        for (const user of users) {
            const entries = await this.prisma.timeEntry.findMany({
                where: {
                    userId: user.id,
                    startedAt: { gte: from },
                    endedAt: { lte: to },
                },
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
            const totalHours = (totalMinutes / 60).toFixed(2);
            rows.push(`"${user.fullName || user.email}","${user.email}",${totalMinutes},${activeMinutes},${idleMinutes},${breakMinutes},${totalHours}`);
        }
        return rows.join('\n');
    }
};
exports.ExportService = ExportService;
exports.ExportService = ExportService = __decorate([
    (0, common_1.Injectable)(),
    __metadata("design:paramtypes", [prisma_service_1.PrismaService])
], ExportService);
//# sourceMappingURL=export.service.js.map