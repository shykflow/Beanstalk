import {
  Controller,
  Get,
  Query,
  UseGuards,
  Request,
  ParseUUIDPipe,
  Res,
} from '@nestjs/common';
import { Response } from 'express';
import { ReportsService } from './reports.service';
import { ExportService } from './export.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { RolesGuard } from '../auth/guards/roles.guard';
import { Roles } from '../auth/decorators/roles.decorator';
import { UserRole } from '@time-tracker/shared';
import { parse } from 'date-fns';

@Controller('reports')
@UseGuards(JwtAuthGuard, RolesGuard)
export class ReportsController {
  constructor(
    private reportsService: ReportsService,
    private exportService: ExportService,
  ) {}

  @Get('summary')
  async getSummary(
    @Query('userId', ParseUUIDPipe) userId: string,
    @Query('from') from: string,
    @Query('to') to: string,
  ) {
    return this.reportsService.getSummary(
      userId,
      new Date(from),
      new Date(to),
    );
  }

  @Get('daily')
  @Roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)
  async getDailyReport(@Request() req, @Query('date') date: string) {
    try {
      const reportDate = date ? new Date(date) : new Date();
      console.log('Getting daily report for orgId:', req.user.orgId, 'date:', reportDate);
      const result = await this.reportsService.getDailyReport(req.user.orgId, reportDate);
      console.log('Daily report result:', JSON.stringify(result, null, 2));
      return result;
    } catch (error) {
      console.error('Error in getDailyReport:', error);
      throw error;
    }
  }

  @Get('weekly')
  @Roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)
  async getWeeklyReport(@Request() req, @Query('week') week: string) {
    // week format: YYYY-Www (e.g., 2025-W45)
    const date = week
      ? parse(week, "'W'II-yyyy", new Date())
      : new Date();
    return this.reportsService.getWeeklyReport(req.user.orgId, date);
  }

  @Get('monthly')
  @Roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)
  async getMonthlyReport(@Request() req, @Query('month') month: string) {
    // month format: YYYY-MM
    const date = month ? parse(month, 'yyyy-MM', new Date()) : new Date();
    return this.reportsService.getMonthlyReport(req.user.orgId, date);
  }

  @Get('timesheet')
  async getTimesheet(
    @Query('userId', ParseUUIDPipe) userId: string,
    @Query('from') from: string,
    @Query('to') to: string,
    @Query('timezone') timezone?: string,
  ) {
    return this.reportsService.getUserTimesheetWithTimezone(
      userId,
      from,
      to,
      timezone,
    );
  }

  @Get('my-today')
  @Roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER, UserRole.MEMBER)
  async getMyToday(@Request() req) {
    const today = new Date().toISOString().split('T')[0];
    const from = new Date(today + 'T00:00:00.000Z');
    const to = new Date(today + 'T23:59:59.999Z');
    
    const entries = await this.reportsService.getUserTimesheet(
      req.user.id,
      from,
      to,
    );
    
    let activeMinutes = 0;
    let idleMinutes = 0;
    
    for (const entry of entries.entries) {
      const minutes = Math.floor(
        (new Date(entry.endedAt).getTime() - new Date(entry.startedAt).getTime()) / 60000
      );
      if (entry.kind === 'ACTIVE') activeMinutes += minutes;
      else if (entry.kind === 'IDLE') idleMinutes += minutes;
    }
    
    return { activeMinutes, idleMinutes };
  }

  @Get('export/csv')
  @Roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)
  async exportCSV(
    @Request() req,
    @Query('from') from: string,
    @Query('to') to: string,
    @Res() res: Response,
  ) {
    const csv = await this.exportService.exportToCSV(
      req.user.orgId,
      new Date(from),
      new Date(to),
    );

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader(
      'Content-Disposition',
      `attachment; filename=timesheet-${from}-${to}.csv`,
    );
    res.send(csv);
  }

  @Get('export/summary-csv')
  @Roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)
  async exportSummaryCSV(
    @Request() req,
    @Query('from') from: string,
    @Query('to') to: string,
    @Res() res: Response,
  ) {
    const csv = await this.exportService.exportSummaryToCSV(
      req.user.orgId,
      new Date(from),
      new Date(to),
    );

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader(
      'Content-Disposition',
      `attachment; filename=summary-${from}-${to}.csv`,
    );
    res.send(csv);
  }
}
