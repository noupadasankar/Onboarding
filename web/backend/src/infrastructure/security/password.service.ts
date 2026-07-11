/**
 * Password hashing/verification. Behind an interface so the algorithm can be
 * swapped (e.g. argon2) and so services can mock it in unit tests.
 */
import { injectable } from 'inversify';
import bcrypt from 'bcryptjs';
import { BCRYPT_ROUNDS } from '../../config/constants';

export interface IPasswordService {
  hash(plain: string): Promise<string>;
  verify(plain: string, hash: string): Promise<boolean>;
}

@injectable()
export class BcryptPasswordService implements IPasswordService {
  hash(plain: string): Promise<string> {
    return bcrypt.hash(plain, BCRYPT_ROUNDS);
  }

  verify(plain: string, hash: string): Promise<boolean> {
    return bcrypt.compare(plain, hash);
  }
}
