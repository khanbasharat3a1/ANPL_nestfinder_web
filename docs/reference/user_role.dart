/// Represents the 3-tier user role hierarchy in NestFinder.
enum UserRole {
  user('user', 'User'),
  approver('approver', 'Approver'),
  superAdmin('super_admin', 'Super Admin');

  final String value;
  final String label;

  const UserRole(this.value, this.label);

  static UserRole fromString(String? role) {
    switch (role) {
      case 'super_admin':
        return UserRole.superAdmin;
      case 'approver':
        return UserRole.approver;
      case 'user':
      default:
        return UserRole.user;
    }
  }

  /// Whether this role has authority to review & approve/reject listings
  bool get canReview => this == UserRole.approver || this == UserRole.superAdmin;

  /// Whether this role has full system administration capabilities
  bool get isSuperAdmin => this == UserRole.superAdmin;
}
