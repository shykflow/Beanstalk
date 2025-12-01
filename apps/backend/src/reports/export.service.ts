import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { differenceInMinutes } from 'date-fns';

@Injectable()
export class ExportService {
  constructor(private prisma: PrismaService) {}

  async exportToCSV(orgId: string, from: Date, to: Date): Promise<string> {
    const users = await this.prisma.user.findMany({
      where: { orgId, isActive: true },
      select: { id: true, fullName: true, email: true },
    });

    const rows: string[] = [
      'User,Email,Date,Start Time,End Time,Duration (minutes),Type,Source',
    ];

    for (const user of users) {
      const entries = await this.prisma.timeEntry.findMany({
        where: {
          userId: user.id,
          startedAt: { gte: from },
          endedAt: { lte: to },
        },
        orderBy: { startedAt: 'asc' },
      });

      for (const entry of entries) {
        const duration = differenceInMinutes(entry.endedAt, entry.startedAt);
        const date = entry.startedAt.toISOString().split('T')[0];
        const startTime = entry.startedAt.toISOString();
        const endTime = entry.endedAt.toISOString();

        rows.push(
          `"${user.fullName || user.email}","${user.email}","${date}","${startTime}","${endTime}",${duration},"${entry.kind}","${entry.source}"`,
        );
      }
    }

    return rows.join('\n');
  }

  async exportSummaryToCSV(orgId: string, from: Date, to: Date): Promise<string> {
    const users = await this.prisma.user.findMany({
      where: { orgId, isActive: true },
      select: { id: true, fullName: true, email: true },
    });

    const rows: string[] = [
      'User,Email,Total Minutes,Active Minutes,Idle Minutes,Break Minutes,Total Hours',
    ];

    for (const user of users) {
      const entries = await this.prisma.timeEntry.findMany({
        where: {
          userId: user.id,
          startedAt: { gte: from },
          endedAt: { lte: to },
        },
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

      const totalHours = (totalMinutes / 60).toFixed(2);

      rows.push(
        `"${user.fullName || user.email}","${user.email}",${totalMinutes},${activeMinutes},${idleMinutes},${breakMinutes},${totalHours}`,
      );
    }

    return rows.join('\n');
  }
}
