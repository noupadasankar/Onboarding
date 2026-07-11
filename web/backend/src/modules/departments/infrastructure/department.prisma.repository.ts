/**
 * Prisma implementation of IDepartmentRepository.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import type { PrismaService } from '../../../infrastructure/database/prisma.service';
import type {
  CreateDepartmentInput,
  DepartmentDTO,
  IDepartmentRepository,
} from '../domain/department.repository';

@injectable()
export class DepartmentPrismaRepository implements IDepartmentRepository {
  constructor(
    @inject(TYPES.PrismaService) private readonly prisma: PrismaService,
  ) {}

  private map(d: {
    id: string; name: string; displayName: string; description: string | null;
    isActive: boolean; createdAt: Date; updatedAt: Date;
  }): DepartmentDTO {
    return {
      id: d.id,
      name: d.name,
      displayName: d.displayName,
      description: d.description,
      isActive: d.isActive,
      createdAt: d.createdAt.toISOString(),
      updatedAt: d.updatedAt.toISOString(),
    };
  }

  async findAll(includeInactive = false): Promise<DepartmentDTO[]> {
    const rows = await this.prisma.client.department.findMany({
      where: includeInactive ? undefined : { isActive: true },
      orderBy: { name: 'asc' },
    });
    return rows.map(this.map);
  }

  async findById(id: string): Promise<DepartmentDTO | null> {
    const row = await this.prisma.client.department.findUnique({ where: { id } });
    return row ? this.map(row) : null;
  }

  async findByName(name: string): Promise<DepartmentDTO | null> {
    const row = await this.prisma.client.department.findUnique({ where: { name } });
    return row ? this.map(row) : null;
  }

  async create(input: CreateDepartmentInput): Promise<DepartmentDTO> {
    const row = await this.prisma.client.department.create({ data: input });
    return this.map(row);
  }

  async update(
    id: string,
    input: Partial<CreateDepartmentInput & { isActive: boolean }>,
  ): Promise<DepartmentDTO | null> {
    try {
      const row = await this.prisma.client.department.update({ where: { id }, data: input });
      return this.map(row);
    } catch {
      return null;
    }
  }
}
