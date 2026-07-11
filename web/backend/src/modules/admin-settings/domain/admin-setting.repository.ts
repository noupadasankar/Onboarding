/**
 * Admin settings domain types and repository interface.
 */

export interface AdminSettingDTO {
  key: string;
  value: unknown;
  description: string | null;
  updatedBy: string | null;
  updatedAt: Date;
  createdAt: Date;
}

export interface UpsertSettingInput {
  key: string;
  value: unknown;
  description?: string;
  updatedBy?: string;
}

export interface IAdminSettingRepository {
  findAll(): Promise<AdminSettingDTO[]>;
  findByKey(key: string): Promise<AdminSettingDTO | null>;
  upsert(input: UpsertSettingInput): Promise<AdminSettingDTO>;
  delete(key: string): Promise<void>;
}
