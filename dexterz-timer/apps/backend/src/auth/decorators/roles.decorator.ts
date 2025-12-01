import { SetMetadata } from '@nestjs/common';
import { UserRole } from '@time-tracker/shared';

export const Roles = (...roles: UserRole[]) => SetMetadata('roles', roles);
