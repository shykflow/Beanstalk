import {
  Controller,
  Post,
  Get,
  Body,
  UseGuards,
  Request,
  Query,
} from '@nestjs/common';
import { ActivityService } from './activity.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { ActivityBatchItem } from '@time-tracker/shared';

@Controller('activity')
@UseGuards(JwtAuthGuard)
export class ActivityController {
  constructor(private activityService: ActivityService) {}

  @Post('sessions/start')
  async startSession(
    @Request() req,
    @Body() body: { deviceId: string; platform: string },
  ) {
    return this.activityService.startSession(req.user.id, body.deviceId, body.platform);
  }

  @Post('sessions/stop')
  async stopSession(@Body() body: { sessionId: string }) {
    return this.activityService.stopSession(body.sessionId);
  }

  @Post('batch')
  async batchUpload(@Request() req, @Body() body: { samples: ActivityBatchItem[] }) {
    return this.activityService.batchUpload(req.user.id, body.samples);
  }

  @Get('recent')
  async getRecent(@Request() req, @Query('limit') limit?: string) {
    return this.activityService.getRecentActivity(
      req.user.id,
      limit ? parseInt(limit) : 100,
    );
  }
}
