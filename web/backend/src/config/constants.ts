/** Cross-cutting constants that are not environment-dependent. */

export const API_PREFIX = '/api/v1';

/** Header used to forward the end user's identity to the Python AI service. */
export const HEADER_USER_ID = 'x-user-id';
export const HEADER_USER_ROLE = 'x-user-role';
export const HEADER_INTERNAL_TOKEN = 'x-internal-token';
export const HEADER_REQUEST_ID = 'x-request-id';

export const BCRYPT_ROUNDS = 12;
