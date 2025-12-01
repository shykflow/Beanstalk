import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { startOfDay, endOfDay, startOfWeek, endOfWeek, startOfMonth, endOfMonth, differenceInMinutes } from 'date-fns';
import { zonedTimeToUtc } from 'date-fns-tz';

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
    // Parse date as local date (YYYY-MM-DD) to avoid timezone issues
    const dateStr = date.toISOString().split('T')[0];
    const from = new Date(dateStr + 'T00:00:00.000Z');
    const to = new Date(dateStr + 'T23:59:59.999Z');
    
    console.log('📅 Daily Report Query:');
    console.log('  Date String:', dateStr);
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
      include: { organization: true },
    });

    const tz = timezone || user?.organization?.timezone || 'Asia/Karachi';
    
    const fromDate = zonedTimeToUtc(from + ' 00:00:00', tz);
    const toDate = zonedTimeToUtc(to + ' 23:59:59', tz);

    return this.getUserTimesheet(userId, fromDate, toDate);
  }
}
