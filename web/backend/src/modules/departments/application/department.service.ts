/**
 * Department application service.
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import { ConflictError, NotFoundError } from '../../../core/errors/app-error';
import type {
  CreateDepartmentInput,
  DepartmentDTO,
  IDepartmentRepository,
} from '../domain/department.repository';

export interface IDepartmentService {
  list(includeInactive?: boolean): Promise<DepartmentDTO[]>;
  getById(id: string): Promise<DepartmentDTO>;
  create(input: CreateDepartmentInput): Promise<DepartmentDTO>;
  update(id: string, input: Partial<CreateDepartmentInput & { isActive: boolean }>): Promise<DepartmentDTO>;
}

@injectable()
export class DepartmentService implements IDepartmentService {
  constructor(
    @inject(TYPES.DepartmentRepository) private readonly repo: IDepartmentRepository,
  ) {}

  async list(includeInactive = false): Promise<DepartmentDTO[]> {
    return this.repo.findAll(includeInactive);
  }

  async getById(id: string): Promise<DepartmentDTO> {
    const dept = await this.repo.findById(id);
    if (!dept) throw new NotFoundError('Department not found');
    return dept;
  }

  async create(input: CreateDepartmentInput): Promise<DepartmentDTO> {
    const existing = await this.repo.findByName(input.name);
    if (existing) throw new ConflictError(`Department "${input.name}" already exists`);
    return this.repo.create(input);
  }

  async update(
    id: string,
    input: Partial<CreateDepartmentInput & { isActive: boolean }>,
  ): Promise<DepartmentDTO> {
    const result = await this.repo.update(id, input);
    if (!result) throw new NotFoundError('Department not found');
    return result;
  }
}
