import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { startOfDay, endOfDay, startOfWeek, endOfWeek, startOfMonth, endOfMonth, differenceInMinutes } from 'date-fns';

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
    const from = startOfDay(date);
    const to = endOfDay(date);

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
    const entries = await this.prisma.timeEntry.findMany({
      where: {
        userId,
        startedAt: { gte: from },
        endedAt: { lte: to },
      },
      orderBy: { startedAt: 'asc' },
    });

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
}
