import 'package:cloud_firestore/cloud_firestore.dart';
import '../../../core/enums/user_role.dart';

/// User profile data model corresponding to Firestore `users/{uid}`.
class UserModel {
  final String uid;
  final String name;
  final String email;
  final String? nameLower;
  final String? emailLower;
  final String? phone;
  final String? photoUrl;
  final UserRole role;
  final bool isBanned;
  final String? fcmToken;
  final DateTime createdAt;

  const UserModel({
    required this.uid,
    required this.name,
    required this.email,
    this.nameLower,
    this.emailLower,
    this.phone,
    this.photoUrl,
    this.role = UserRole.user,
    this.isBanned = false,
    this.fcmToken,
    required this.createdAt,
  });

  /// Factory constructor parsing from Firestore DocumentSnapshot or Map
  factory UserModel.fromMap(Map<String, dynamic> map, String uid) {
    DateTime parseDate(dynamic value) {
      if (value is Timestamp) {
        return value.toDate();
      } else if (value is String) {
        return DateTime.tryParse(value) ?? DateTime.now();
      }
      return DateTime.now();
    }

    final rawName = map['name'] as String? ?? 'Employee';
    final rawEmail = map['email'] as String? ?? '';

    return UserModel(
      uid: uid,
      name: rawName,
      email: rawEmail,
      nameLower: map['nameLower'] as String? ?? rawName.toLowerCase(),
      emailLower: map['emailLower'] as String? ?? rawEmail.toLowerCase(),
      phone: map['phone'] as String?,
      photoUrl: map['photoUrl'] as String?,
      role: UserRole.fromString(map['role'] as String?),
      isBanned: map['isBanned'] as bool? ?? false,
      fcmToken: map['fcmToken'] as String?,
      createdAt: parseDate(map['createdAt']),
    );
  }

  factory UserModel.fromDocument(DocumentSnapshot doc) {
    final data = doc.data() as Map<String, dynamic>? ?? {};
    return UserModel.fromMap(data, doc.id);
  }

  Map<String, dynamic> toMap() {
    return {
      'name': name,
      'nameLower': nameLower ?? name.toLowerCase(),
      'email': email,
      'emailLower': emailLower ?? email.toLowerCase(),
      'phone': phone,
      'photoUrl': photoUrl,
      'role': role.value,
      'isBanned': isBanned,
      'fcmToken': fcmToken,
      'createdAt': Timestamp.fromDate(createdAt),
    };
  }

  UserModel copyWith({
    String? name,
    String? email,
    String? nameLower,
    String? emailLower,
    String? phone,
    String? photoUrl,
    UserRole? role,
    bool? isBanned,
    String? fcmToken,
    DateTime? createdAt,
  }) {
    return UserModel(
      uid: uid,
      name: name ?? this.name,
      email: email ?? this.email,
      nameLower: nameLower ?? (name != null ? name.toLowerCase() : this.nameLower),
      emailLower: emailLower ?? (email != null ? email.toLowerCase() : this.emailLower),
      phone: phone ?? this.phone,
      photoUrl: photoUrl ?? this.photoUrl,
      role: role ?? this.role,
      isBanned: isBanned ?? this.isBanned,
      fcmToken: fcmToken ?? this.fcmToken,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}
