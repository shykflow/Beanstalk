import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Body,
  Param,
  UseGuards,
  Request,
} from '@nestjs/common';
import { UsersService } from './users.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { RolesGuard } from '../auth/guards/roles.guard';
import { Roles } from '../auth/decorators/roles.decorator';
import { UserRole } from '@time-tracker/shared';

@Controller('users')
@UseGuards(JwtAuthGuard, RolesGuard)
export class UsersController {
  constructor(private usersService: UsersService) {}

  @Get()
  @Roles(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER)
  async findAll(@Request() req) {
    return this.usersService.findAll(req.user.orgId);
  }

  @Get(':id')
  async findOne(@Param('id') id: string) {
    return this.usersService.findOne(id);
  }

  @Post()
  @Roles(UserRole.OWNER, UserRole.ADMIN)
  async create(
    @Request() req,
    @Body()
    body: {
      email: string;
      password: string;
      fullName: string;
      role: UserRole;
    },
  ) {
    return this.usersService.create({
      ...body,
      orgId: req.user.orgId,
    });
  }

  @Put(':id')
  @Roles(UserRole.OWNER, UserRole.ADMIN)
  async update(
    @Param('id') id: string,
    @Body() body: { fullName?: string; role?: UserRole; isActive?: boolean },
  ) {
    return this.usersService.update(id, body);
  }

  @Delete(':id')
  @Roles(UserRole.OWNER, UserRole.ADMIN)
  async delete(@Param('id') id: string) {
    await this.usersService.delete(id);
    return { message: 'User deleted successfully' };
  }
}
