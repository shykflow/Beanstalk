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
exports.RollupService = void 0;
const common_1 = require("@nestjs/common");
const prisma_service_1 = require("../prisma/prisma.service");
const shared_1 = require("@time-tracker/shared");
const date_fns_1 = require("date-fns");
let RollupService = class RollupService {
    constructor(prisma) {
        this.prisma = prisma;
    }
    async rollupUserActivity(userId, from, to) {
        const user = await this.prisma.user.findUnique({
            where: { id: userId },
            include: {
                organization: {
                    include: { schedule: true },
                },
            },
        });
        if (!user) {
            return;
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
        const samples = await this.prisma.activitySample.findMany({
            where: {
                userId,
                capturedAt: {
                    gte: from,
                    lte: to,
                },
            },
            orderBy: { capturedAt: 'asc' },
        });
        if (samples.length === 0) {
            return;
        }
        const minuteBuckets = this.groupByMinute(samples);
        const entries = [];
        for (const bucket of minuteBuckets) {
            if (!(0, shared_1.isWithinCheckinWindow)(bucket.start, rules)) {
                continue;
            }
            if ((0, shared_1.isWithinBreakWindow)(bucket.start, rules)) {
                continue;
            }
            const active = bucket.samples.some((s) => (0, shared_1.hasActivity)(s.mouseDelta, s.keyCount));
            if (active) {
                entries.push({
                    userId,
                    startedAt: bucket.start,
                    endedAt: bucket.end,
                    kind: 'ACTIVE',
                    source: 'AUTO',
                });
            }
        }
        const merged = this.mergeContiguous(entries);
        await this.prisma.$transaction(async (tx) => {
            await tx.timeEntry.deleteMany({
                where: {
                    userId,
                    startedAt: { gte: from },
                    endedAt: { lte: to },
                    source: 'AUTO',
                },
            });
            if (merged.length > 0) {
                await tx.timeEntry.createMany({
                    data: merged,
                });
            }
        });
        return { processed: merged.length };
    }
    groupByMinute(samples) {
        const buckets = new Map();
        for (const sample of samples) {
            const minuteStart = (0, date_fns_1.startOfMinute)(sample.capturedAt);
            const minuteEnd = (0, date_fns_1.addMinutes)(minuteStart, 1);
            const key = minuteStart.getTime();
            if (!buckets.has(key)) {
                buckets.set(key, {
                    start: minuteStart,
                    end: minuteEnd,
                    samples: [],
                });
            }
            buckets.get(key).samples.push({
                mouseDelta: sample.mouseDelta,
                keyCount: sample.keyCount,
            });
        }
        return Array.from(buckets.values()).sort((a, b) => a.start.getTime() - b.start.getTime());
    }
    mergeContiguous(entries) {
        if (entries.length === 0)
            return [];
        const merged = [];
        let current = { ...entries[0] };
        for (let i = 1; i < entries.length; i++) {
            const next = entries[i];
            if (next.startedAt.getTime() === current.endedAt.getTime() &&
                next.kind === current.kind) {
                current.endedAt = next.endedAt;
            }
            else {
                merged.push(current);
                current = { ...next };
            }
        }
        merged.push(current);
        return merged;
    }
};
exports.RollupService = RollupService;
exports.RollupService = RollupService = __decorate([
    (0, common_1.Injectable)(),
    __metadata("design:paramtypes", [prisma_service_1.PrismaService])
], RollupService);
//# sourceMappingURL=rollup.service.js.map