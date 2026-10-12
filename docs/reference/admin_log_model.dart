import 'package:cloud_firestore/cloud_firestore.dart';

class AdminLogModel {
  final String id;
  final String actorUid;
  final String action;
  final String targetId;
  final String details;
  final DateTime createdAt;

  const AdminLogModel({
    required this.id,
    required this.actorUid,
    required this.action,
    required this.targetId,
    required this.details,
    required this.createdAt,
  });

  factory AdminLogModel.fromDocument(DocumentSnapshot<Map<String, dynamic>> doc) {
    final data = doc.data() ?? {};
    DateTime parseDate(dynamic v) {
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v) ?? DateTime.now();
      return DateTime.now();
    }

    return AdminLogModel(
      id: doc.id,
      actorUid: data['actorUid'] as String? ?? '',
      action: data['action'] as String? ?? '',
      targetId: data['targetId'] as String? ?? '',
      details: data['details'] as String? ?? '',
      createdAt: parseDate(data['createdAt']),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'actorUid': actorUid,
      'action': action,
      'targetId': targetId,
      'details': details,
      'createdAt': Timestamp.fromDate(createdAt),
    };
  }
}
