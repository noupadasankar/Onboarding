/**
 * Admin Settings application service.
 *
 * Provides a typed key/value store for platform-wide configuration.
 * All mutations require USERS_MANAGE permission (enforced at the route level).
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../../core/di/types';
import { NotFoundError } from '../../../core/errors/app-error';
import type {
  AdminSettingDTO,
  IAdminSettingRepository,
} from '../domain/admin-setting.repository';

export interface IAdminSettingService {
  listAll(): Promise<AdminSettingDTO[]>;
  get(key: string): Promise<AdminSettingDTO>;
  set(key: string, value: unknown, updatedBy: string, description?: string): Promise<AdminSettingDTO>;
  remove(key: string): Promise<void>;
}

@injectable()
export class AdminSettingService implements IAdminSettingService {
  constructor(
    @inject(TYPES.AdminSettingRepository) private readonly repo: IAdminSettingRepository,
  ) {}

  async listAll(): Promise<AdminSettingDTO[]> {
    return this.repo.findAll();
  }

  async get(key: string): Promise<AdminSettingDTO> {
    const setting = await this.repo.findByKey(key);
    if (!setting) throw new NotFoundError(`Setting "${key}" not found`);
    return setting;
  }

  async set(
    key: string,
    value: unknown,
    updatedBy: string,
    description?: string,
  ): Promise<AdminSettingDTO> {
    return this.repo.upsert({ key, value, updatedBy, description });
  }

  async remove(key: string): Promise<void> {
    const existing = await this.repo.findByKey(key);
    if (!existing) throw new NotFoundError(`Setting "${key}" not found`);
    await this.repo.delete(key);
  }
}
