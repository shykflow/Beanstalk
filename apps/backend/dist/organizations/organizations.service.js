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
exports.OrganizationsService = void 0;
const common_1 = require("@nestjs/common");
const prisma_service_1 = require("../prisma/prisma.service");
let OrganizationsService = class OrganizationsService {
    constructor(prisma) {
        this.prisma = prisma;
    }
    async getOrganization(orgId) {
        return this.prisma.organization.findUnique({
            where: { id: orgId },
            include: { schedule: true },
        });
    }
    async updateOrganization(orgId, data) {
        return this.prisma.organization.update({
            where: { id: orgId },
            data,
        });
    }
    async getSchedule(orgId) {
        const schedule = await this.prisma.schedule.findUnique({
            where: { orgId },
        });
        if (!schedule) {
            return this.prisma.schedule.create({
                data: { orgId },
            });
        }
        return schedule;
    }
    async updateSchedule(orgId, data) {
        return this.prisma.schedule.upsert({
            where: { orgId },
            update: data,
            create: {
                orgId,
                ...data,
            },
        });
    }
    async createAdjustment(data) {
        return this.prisma.adjustment.create({
            data,
        });
    }
    async getAdjustments(userId, from, to) {
        return this.prisma.adjustment.findMany({
            where: {
                userId,
                ...(from && to
                    ? {
                        effectiveDate: {
                            gte: from,
                            lte: to,
                        },
                    }
                    : {}),
            },
            include: {
                creator: {
                    select: {
                        fullName: true,
                        email: true,
                    },
                },
            },
            orderBy: { createdAt: 'desc' },
        });
    }
};
exports.OrganizationsService = OrganizationsService;
exports.OrganizationsService = OrganizationsService = __decorate([
    (0, common_1.Injectable)(),
    __metadata("design:paramtypes", [prisma_service_1.PrismaService])
], OrganizationsService);
//# sourceMappingURL=organizations.service.js.map