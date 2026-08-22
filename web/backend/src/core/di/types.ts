/**
 * Dependency-injection tokens. Using symbols (not string literals) prevents
 * collisions and keeps bindings refactor-safe. Grouped by layer.
 */
export const TYPES = {
  // Config / cross-cutting
  Config: Symbol.for('Config'),
  Logger: Symbol.for('Logger'),

  // Infrastructure
  PrismaService: Symbol.for('PrismaService'),
  RedisService: Symbol.for('RedisService'),

  // Security
  JwtService: Symbol.for('JwtService'),
  PasswordService: Symbol.for('PasswordService'),
  TokenStore: Symbol.for('TokenStore'),

  // AI
  AiGateway: Symbol.for('AiGateway'),

  // Storage
  StorageService: Symbol.for('StorageService'),

  // Queue
  IndexingQueue: Symbol.for('IndexingQueue'),

  // Repositories
  UserRepository: Symbol.for('UserRepository'),
  DepartmentRepository: Symbol.for('DepartmentRepository'),
  DocumentRepository: Symbol.for('DocumentRepository'),
  ConversationRepository: Symbol.for('ConversationRepository'),
  NotificationRepository: Symbol.for('NotificationRepository'),
  AdminSettingRepository: Symbol.for('AdminSettingRepository'),

  // Application services
  AuthService: Symbol.for('AuthService'),
  UserService: Symbol.for('UserService'),
  DepartmentService: Symbol.for('DepartmentService'),
  DocumentService: Symbol.for('DocumentService'),
  ConversationService: Symbol.for('ConversationService'),
  AnalyticsService: Symbol.for('AnalyticsService'),
  NotificationService: Symbol.for('NotificationService'),
  AdminSettingService: Symbol.for('AdminSettingService'),

  // Controllers
  AuthController: Symbol.for('AuthController'),
  UserController: Symbol.for('UserController'),
  RolesController: Symbol.for('RolesController'),
  DepartmentController: Symbol.for('DepartmentController'),
  DocumentController: Symbol.for('DocumentController'),
  ConversationController: Symbol.for('ConversationController'),
  AnalyticsController: Symbol.for('AnalyticsController'),
  NotificationController: Symbol.for('NotificationController'),
  AdminSettingsController: Symbol.for('AdminSettingsController'),

  // Infrastructure services
  AuditLogService: Symbol.for('AuditLogService'),

  // Audit log read module
  AuditLogViewService: Symbol.for('AuditLogViewService'),
  AuditLogViewController: Symbol.for('AuditLogViewController'),

  // Domain services
  RoleCatalogService: Symbol.for('RoleCatalogService'),
  DepartmentAccessService: Symbol.for('DepartmentAccessService'),

  // Dashboard module
  DashboardService: Symbol.for('DashboardService'),
  DashboardController: Symbol.for('DashboardController'),

  // Onboarding module
  OnboardingTaskRepository: Symbol.for('OnboardingTaskRepository'),
  OnboardingTaskService: Symbol.for('OnboardingTaskService'),
  OnboardingTaskController: Symbol.for('OnboardingTaskController'),
  OnboardingRoutesFactory: Symbol.for('OnboardingRoutesFactory'),
} as const;
