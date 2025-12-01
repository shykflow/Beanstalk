import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class OrganizationsService {
  constructor(private prisma: PrismaService) {}

  async getOrganization(orgId: string) {
    return this.prisma.organization.findUnique({
      where: { id: orgId },
      include: { schedule: true },
    });
  }

  async updateOrganization(orgId: string, data: { name?: string; timezone?: string }) {
    return this.prisma.organization.update({
      where: { id: orgId },
      data,
    });
  }

  async getSchedule(orgId: string) {
    const schedule = await this.prisma.schedule.findUnique({
      where: { orgId },
    });

    if (!schedule) {
      // Create default schedule if it doesn't exist
      return this.prisma.schedule.create({
        data: { orgId },
      });
    }

    return schedule;
  }

  async updateSchedule(
    orgId: string,
    data: {
      tz?: string;
      checkinStart?: string;
      checkinEnd?: string;
      breakStart?: string;
      breakEnd?: string;
      idleThresholdSeconds?: number;
    },
  ) {
    return this.prisma.schedule.upsert({
      where: { orgId },
      update: data,
      create: {
        orgId,
        ...data,
      },
    });
  }

  async createAdjustment(data: {
    userId: string;
    createdBy: string;
    reason: string;
    deltaMinutes: number;
    effectiveDate: Date;
  }) {
    return this.prisma.adjustment.create({
      data,
    });
  }

  async getAdjustments(userId: string, from?: Date, to?: Date) {
    return this.prisma.adjustment.findMany({
      where: {
        userId,
        ...(from && to
          ? {
              effectiveDate: {
                gte: from,
                lte: to,
              },
            }
          : {}),
      },
      include: {
        creator: {
          select: {
            fullName: true,
            email: true,
          },
        },
      },
      orderBy: { createdAt: 'desc' },
    });
  }
}
