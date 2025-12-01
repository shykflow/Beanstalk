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
exports.RollupProcessor = void 0;
const bullmq_1 = require("@nestjs/bullmq");
const rollup_service_1 = require("../../activity/rollup.service");
let RollupProcessor = class RollupProcessor extends bullmq_1.WorkerHost {
    constructor(rollupService) {
        super();
        this.rollupService = rollupService;
    }
    async process(job) {
        switch (job.name) {
            case 'rollup-user':
                return this.handleRollupUser(job);
            case 'rollup-session':
                return this.handleRollupSession(job);
            default:
                throw new Error(`Unknown job type: ${job.name}`);
        }
    }
    async handleRollupUser(job) {
        const { userId, from, to } = job.data;
        return this.rollupService.rollupUserActivity(userId, new Date(from), new Date(to));
    }
    async handleRollupSession(job) {
        const { userId } = job.data;
        const to = new Date();
        const from = new Date(to.getTime() - 60 * 60 * 1000);
        return this.rollupService.rollupUserActivity(userId, from, to);
    }
};
exports.RollupProcessor = RollupProcessor;
exports.RollupProcessor = RollupProcessor = __decorate([
    (0, bullmq_1.Processor)('activity-rollup'),
    __metadata("design:paramtypes", [rollup_service_1.RollupService])
], RollupProcessor);
//# sourceMappingURL=rollup.processor.js.map