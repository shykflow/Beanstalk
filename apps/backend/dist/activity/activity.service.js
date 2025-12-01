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
exports.ActivityService = void 0;
const common_1 = require("@nestjs/common");
const bullmq_1 = require("@nestjs/bullmq");
const bullmq_2 = require("bullmq");
const prisma_service_1 = require("../prisma/prisma.service");
const shared_1 = require("@time-tracker/shared");
let ActivityService = class ActivityService {
    constructor(prisma, rollupQueue) {
        this.prisma = prisma;
        this.rollupQueue = rollupQueue;
    }
    async startSession(userId, deviceId, platform) {
        await this.prisma.deviceSession.updateMany({
            where: {
                userId,
                deviceId,
                endedAt: null,
            },
            data: {
                endedAt: new Date(),
            },
        });
        const session = await this.prisma.deviceSession.create({
            data: {
                userId,
                deviceId,
                platform,
                startedAt: new Date(),
            },
        });
        return session;
    }
    async stopSession(sessionId) {
        const session = await this.prisma.deviceSession.update({
            where: { id: sessionId },
            data: { endedAt: new Date() },
        });
        await this.rollupQueue.add('rollup-session', {
            userId: session.userId,
            sessionId: session.id,
        });
        return session;
    }
    async batchUpload(userId, samples) {
        if (samples.length === 0) {
            return { inserted: 0 };
        }
        const user = await this.prisma.user.findUnique({
            where: { id: userId },
            include: {
                organization: {
                    include: { schedule: true },
                },
            },
        });
        if (!user) {
            throw new common_1.BadRequestException('User not found');
        }
        const schedule = user.organization.schedule || {
            tz: shared_1.DEFAULT_RULES.timezone,
            checkinStart: shared_1.DEFAULT_RULES.checkinWindow.start,
            checkinEnd: shared_1.DEFAULT_RULES.checkinWindow.end,
            breakStart: shared_1.DEFAULT_RULES.breakWindow.start,
            breakEnd: shared_1.DEFAULT_RULES.breakWindow.end,
            idleThresholdSeconds: shared_1.DEFAULT_RULES.idleThresholdSeconds,
        };
        const rules = {
            timezone: schedule.tz,
            checkinWindow: {
                start: schedule.checkinStart,
                end: schedule.checkinEnd,
            },
            breakWindow: {
                start: schedule.breakStart,
                end: schedule.breakEnd,
            },
            idleThresholdSeconds: schedule.idleThresholdSeconds,
        };
        const validSamples = samples.filter((sample) => {
            const timestamp = new Date(sample.capturedAt);
            if (!(0, shared_1.isWithinCheckinWindow)(timestamp, rules)) {
                return false;
            }
            if ((0, shared_1.isWithinBreakWindow)(timestamp, rules)) {
                return false;
            }
            return true;
        });
        if (validSamples.length > 0) {
            await this.prisma.activitySample.createMany({
                data: validSamples.map((sample) => ({
                    userId,
                    capturedAt: new Date(sample.capturedAt),
                    mouseDelta: sample.mouseDelta,
                    keyCount: sample.keyCount,
                    deviceSessionId: sample.deviceSessionId || null,
                })),
            });
            await this.rollupQueue.add('rollup-user', {
                userId,
                from: new Date(validSamples[0].capturedAt),
                to: new Date(validSamples[validSamples.length - 1].capturedAt),
            });
        }
        return { inserted: validSamples.length, rejected: samples.length - validSamples.length };
    }
    async getRecentActivity(userId, limit = 100) {
        return this.prisma.activitySample.findMany({
            where: { userId },
            orderBy: { capturedAt: 'desc' },
            take: limit,
        });
    }
};
exports.ActivityService = ActivityService;
exports.ActivityService = ActivityService = __decorate([
    (0, common_1.Injectable)(),
    __param(1, (0, bullmq_1.InjectQueue)('activity-rollup')),
    __metadata("design:paramtypes", [prisma_service_1.PrismaService,
        bullmq_2.Queue])
], ActivityService);
//# sourceMappingURL=activity.service.js.map