import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { startOfDay, endOfDay, startOfWeek, endOfWeek, startOfMonth, endOfMonth, differenceInMinutes, addDays, parse } from 'date-fns';
import { zonedTimeToUtc, utcToZonedTime, format } from 'date-fns-tz';

@Injectable()
export class ReportsService {
  constructor(private prisma: PrismaService) {}

  async getSummary(userId: string, from: Date, to: Date) {
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
      const minutes = differenceInMinutes(entry.endedAt, entry.startedAt);
      summary.totalMinutes += minutes;

      if (entry.kind === 'ACTIVE') {
        summary.activeMinutes += minutes;
      } else if (entry.kind === 'IDLE') {
        summary.idleMinutes += minutes;
      } else if (entry.kind === 'BREAK') {
        summary.breakMinutes += minutes;
      }
    }

    return summary;
  }

  async getDailyReport(orgId: string, date: Date) {
    const org = await this.prisma.organization.findUnique({
      where: { id: orgId },
      include: { schedule: true },
    });

    if (!org?.schedule) {
      throw new Error('Organization schedule not configured');
    }

    const schedule = org.schedule;
    const dateStr = date.toISOString().split('T')[0];
    
    // Working day boundaries: dateStr at checkinStart to next day at checkinEnd
    const startStr = `${dateStr} ${schedule.checkinStart}`;
    const from = zonedTimeToUtc(startStr, schedule.tz);
    
    const nextDay = format(addDays(parse(dateStr, 'yyyy-MM-dd', new Date()), 1), 'yyyy-MM-dd');
    const endStr = `${nextDay} ${schedule.checkinEnd}`;
    const to = zonedTimeToUtc(endStr, schedule.tz);
    
    console.log('📅 Daily Report Query (Working Day):');
    console.log('  Working Date:', dateStr);
    console.log('  Schedule:', `${schedule.checkinStart} - ${schedule.checkinEnd}`);
    console.log('  From:', from.toISOString());
    console.log('  To:', to.toISOString());

    const users = await this.prisma.user.findMany({
      where: { orgId, isActive: true },
      select: { id: true, fullName: true, email: true },
    });

    const report = {
      date: date.toISOString().split('T')[0],
      users: [] as any[],
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
      
      if (entries.length > 0) {
        console.log(`  User ${user.fullName}: ${entries.length} entries`);
        console.log(`    First entry: ${entries[0].startedAt.toISOString()}`);
        console.log(`    Last entry: ${entries[entries.length - 1].endedAt.toISOString()}`);
      }

      let totalMinutes = 0;
      let activeMinutes = 0;
      let idleMinutes = 0;
      let breakMinutes = 0;

      for (const entry of entries) {
        const minutes = differenceInMinutes(entry.endedAt, entry.startedAt);
        totalMinutes += minutes;

        if (entry.kind === 'ACTIVE') activeMinutes += minutes;
        else if (entry.kind === 'IDLE') idleMinutes += minutes;
        else if (entry.kind === 'BREAK') breakMinutes += minutes;
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
          id: e.id.toString(), // Convert BigInt to string
        })),
      });
    }

    return report;
  }

  async getWeeklyReport(orgId: string, date: Date) {
    const from = startOfWeek(date, { weekStartsOn: 1 }); // Monday
    const to = endOfWeek(date, { weekStartsOn: 1 });

    return this.getAggregatedReport(orgId, from, to, 'weekly');
  }

  async getMonthlyReport(orgId: string, date: Date) {
    const from = startOfMonth(date);
    const to = endOfMonth(date);

    return this.getAggregatedReport(orgId, from, to, 'monthly');
  }

  private async getAggregatedReport(
    orgId: string,
    from: Date,
    to: Date,
    period: string,
  ) {
    const users = await this.prisma.user.findMany({
      where: { orgId, isActive: true },
      select: { id: true, fullName: true, email: true },
    });

    const report = {
      period,
      from: from.toISOString(),
      to: to.toISOString(),
      users: [] as any[],
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

  async getUserTimesheet(userId: string, from: Date, to: Date) {
    console.log('📊 User Timesheet Query:');
    console.log('  UserId:', userId);
    console.log('  From:', from.toISOString());
    console.log('  To:', to.toISOString());
    
    const entries = await this.prisma.timeEntry.findMany({
      where: {
        userId,
        startedAt: { gte: from },
        endedAt: { lte: to },
      },
      orderBy: { startedAt: 'asc' },
    });
    
    console.log(`  Found ${entries.length} entries`);
    if (entries.length > 0) {
      console.log(`  First: ${entries[0].startedAt.toISOString()}`);
      console.log(`  Last: ${entries[entries.length - 1].endedAt.toISOString()}`);
    }

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

  async getUserTimesheetWithTimezone(userId: string, from: string, to: string, timezone?: string) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      include: { organization: { include: { schedule: true } } },
    });

    if (!user?.organization?.schedule) {
      throw new Error('Organization schedule not configured');
    }

    const schedule = user.organization.schedule;
    const tz = timezone || schedule.tz;
    
    // Working day boundaries for from date
    const fromStartStr = `${from} ${schedule.checkinStart}`;
    const fromDate = zonedTimeToUtc(fromStartStr, tz);
    
    // Working day boundaries for to date (end is next day at checkinEnd)
    const toNextDay = format(addDays(parse(to, 'yyyy-MM-dd', new Date()), 1), 'yyyy-MM-dd');
    const toEndStr = `${toNextDay} ${schedule.checkinEnd}`;
    const toDate = zonedTimeToUtc(toEndStr, tz);

    return this.getUserTimesheet(userId, fromDate, toDate);
  }
}
