/**
 * Department domain repository interface.
 * Keeps the application service decoupled from Prisma.
 */
export interface DepartmentDTO {
  id: string;
  name: string;
  displayName: string;
  description: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDepartmentInput {
  name: string;
  displayName: string;
  description?: string;
}

export interface IDepartmentRepository {
  findAll(includeInactive?: boolean): Promise<DepartmentDTO[]>;
  findById(id: string): Promise<DepartmentDTO | null>;
  findByName(name: string): Promise<DepartmentDTO | null>;
  create(input: CreateDepartmentInput): Promise<DepartmentDTO>;
  update(id: string, input: Partial<CreateDepartmentInput & { isActive: boolean }>): Promise<DepartmentDTO | null>;
}
