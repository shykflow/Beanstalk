import {
  Controller,
  Get,
  Put,
  Post,
  Body,
  UseGuards,
  Request,
  Query,
  ParseUUIDPipe,
} from '@nestjs/common';
import { OrganizationsService } from './organizations.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { RolesGuard } from '../auth/guards/roles.guard';
import { Roles } from '../auth/decorators/roles.decorator';
import { UserRole } from '@time-tracker/shared';

@Controller('organizations')
@UseGuards(JwtAuthGuard, RolesGuard)
export class OrganizationsController {
  constructor(private organizationsService: OrganizationsService) {}

  @Get('me')
  async getMyOrganization(@Request() req) {
    return this.organizationsService.getOrganization(req.user.orgId);
  }

  @Put('me')
  @Roles(UserRole.OWNER, UserRole.ADMIN)
  async updateMyOrganization(
    @Request() req,
    @Body() body: { name?: string; timezone?: string },
  ) {
    return this.organizationsService.updateOrganization(req.user.orgId, body);
  }

  @Get('schedule')
  async getSchedule(@Request() req) {
    return this.organizationsService.getSchedule(req.user.orgId);
  }

  @Put('schedule')
  @Roles(UserRole.OWNER, UserRole.ADMIN)
  async updateSchedule(
    @Request() req,
    @Body()
    body: {
      tz?: string;
      checkinStart?: string;
      checkinEnd?: string;
      breakStart?: string;
      breakEnd?: string;
      idleThresholdSeconds?: number;
    },
  ) {
    return this.organizationsService.updateSchedule(req.user.orgId, body);
  }

  @Post('adjustments')
  @Roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)
  async createAdjustment(
    @Request() req,
    @Body()
    body: {
      userId: string;
      reason: string;
      deltaMinutes: number;
      effectiveDate: string;
    },
  ) {
    return this.organizationsService.createAdjustment({
      userId: body.userId,
      createdBy: req.user.id,
      reason: body.reason,
      deltaMinutes: body.deltaMinutes,
      effectiveDate: new Date(body.effectiveDate),
    });
  }

  @Get('adjustments')
  async getAdjustments(
    @Query('userId', ParseUUIDPipe) userId: string,
    @Query('from') from?: string,
    @Query('to') to?: string,
  ) {
    return this.organizationsService.getAdjustments(
      userId,
      from ? new Date(from) : undefined,
      to ? new Date(to) : undefined,
    );
  }
}
