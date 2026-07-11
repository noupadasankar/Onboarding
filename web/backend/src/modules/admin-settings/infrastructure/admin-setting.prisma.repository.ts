/**
 * Prisma implementation of IAdminSettingRepository.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type { PrismaService } from '../../../infrastructure/database/prisma.service';
import type {
  AdminSettingDTO,
  IAdminSettingRepository,
  UpsertSettingInput,
} from '../domain/admin-setting.repository';

function toDTO(row: {
  key: string;
  value: unknown;
  description: string | null;
  updatedBy: string | null;
  updatedAt: Date;
  createdAt: Date;
}): AdminSettingDTO {
  return {
    key: row.key,
    value: row.value,
    description: row.description,
    updatedBy: row.updatedBy,
    updatedAt: row.updatedAt,
    createdAt: row.createdAt,
  };
}

@injectable()
export class AdminSettingPrismaRepository implements IAdminSettingRepository {
  constructor(@inject(TYPES.PrismaService) private readonly prisma: PrismaService) {}

  async findAll(): Promise<AdminSettingDTO[]> {
    const rows = await this.prisma.client.adminSetting.findMany({
      orderBy: { key: 'asc' },
    });
    return rows.map(toDTO);
  }

  async findByKey(key: string): Promise<AdminSettingDTO | null> {
    const row = await this.prisma.client.adminSetting.findUnique({ where: { key } });
    return row ? toDTO(row) : null;
  }

  async upsert(input: UpsertSettingInput): Promise<AdminSettingDTO> {
    const row = await this.prisma.client.adminSetting.upsert({
      where: { key: input.key },
      update: {
        value: input.value as never,
        ...(input.description !== undefined ? { description: input.description } : {}),
        ...(input.updatedBy ? { updatedBy: input.updatedBy } : {}),
      },
      create: {
        key: input.key,
        value: input.value as never,
        description: input.description,
        updatedBy: input.updatedBy,
      },
    });
    return toDTO(row);
  }

  async delete(key: string): Promise<void> {
    await this.prisma.client.adminSetting.delete({ where: { key } });
  }
}
