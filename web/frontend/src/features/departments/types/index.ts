export interface DepartmentDTO {
  id: string;
  name: string;
  displayName: string;
  description: string | null;
  isActive: boolean;
  createdAt: string;
}

export interface CreateDepartmentRequest {
  name: string;
  displayName: string;
  description?: string;
}

export interface UpdateDepartmentRequest extends Partial<CreateDepartmentRequest> {
  isActive?: boolean;
}
