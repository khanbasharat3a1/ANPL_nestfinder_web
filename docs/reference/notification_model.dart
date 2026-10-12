import 'package:cloud_firestore/cloud_firestore.dart';

enum NotificationType {
  approved('approved'),
  rejected('rejected');

  final String value;
  const NotificationType(this.value);

  static NotificationType fromString(String val) {
    if (val == 'rejected') return NotificationType.rejected;
    return NotificationType.approved;
  }
}

class NotificationModel {
  final String id;
  final NotificationType type;
  final String listingId;
  final String listingTitle;
  final String message;
  final String? rejectionReason;
  final DateTime createdAt;
  final bool read;

  const NotificationModel({
    required this.id,
    required this.type,
    required this.listingId,
    required this.listingTitle,
    required this.message,
    this.rejectionReason,
    required this.createdAt,
    this.read = false,
  });

  factory NotificationModel.fromDocument(DocumentSnapshot<Map<String, dynamic>> doc) {
    final data = doc.data() ?? {};
    return NotificationModel.fromMap(data, doc.id);
  }

  factory NotificationModel.fromMap(Map<String, dynamic> data, String id) {
    DateTime parsedCreatedAt;
    final rawCreatedAt = data['createdAt'];
    if (rawCreatedAt is Timestamp) {
      parsedCreatedAt = rawCreatedAt.toDate();
    } else if (rawCreatedAt is String) {
      parsedCreatedAt = DateTime.tryParse(rawCreatedAt) ?? DateTime.now();
    } else {
      parsedCreatedAt = DateTime.now();
    }

    return NotificationModel(
      id: id,
      type: NotificationType.fromString(data['type'] as String? ?? 'approved'),
      listingId: data['listingId'] as String? ?? '',
      listingTitle: data['listingTitle'] as String? ?? 'Listing',
      message: data['message'] as String? ?? '',
      rejectionReason: data['rejectionReason'] as String?,
      createdAt: parsedCreatedAt,
      read: data['read'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'type': type.value,
      'listingId': listingId,
      'listingTitle': listingTitle,
      'message': message,
      if (rejectionReason != null) 'rejectionReason': rejectionReason,
      'createdAt': Timestamp.fromDate(createdAt),
      'read': read,
    };
  }

  NotificationModel copyWith({
    String? id,
    NotificationType? type,
    String? listingId,
    String? listingTitle,
    String? message,
    String? rejectionReason,
    DateTime? createdAt,
    bool? read,
  }) {
    return NotificationModel(
      id: id ?? this.id,
      type: type ?? this.type,
      listingId: listingId ?? this.listingId,
      listingTitle: listingTitle ?? this.listingTitle,
      message: message ?? this.message,
      rejectionReason: rejectionReason ?? this.rejectionReason,
      createdAt: createdAt ?? this.createdAt,
      read: read ?? this.read,
    );
  }
}
