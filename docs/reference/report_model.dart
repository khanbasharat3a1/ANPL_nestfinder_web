import 'package:cloud_firestore/cloud_firestore.dart';

class ReportModel {
  final String id;
  final String listingId;
  final String listingTitle;
  final String reportedBy;
  final String reportedByName;
  final String reason;
  final DateTime createdAt;
  final bool resolved;

  const ReportModel({
    required this.id,
    required this.listingId,
    required this.listingTitle,
    required this.reportedBy,
    required this.reportedByName,
    required this.reason,
    required this.createdAt,
    this.resolved = false,
  });

  Map<String, dynamic> toMap() {
    return {
      'listingId': listingId,
      'listingTitle': listingTitle,
      'reportedBy': reportedBy,
      'reportedByName': reportedByName,
      'reason': reason,
      'createdAt': Timestamp.fromDate(createdAt),
      'resolved': resolved,
    };
  }

  factory ReportModel.fromDocument(DocumentSnapshot doc) {
    final data = doc.data() as Map<String, dynamic>? ?? {};
    final ts = data['createdAt'];
    final created = ts is Timestamp ? ts.toDate() : DateTime.now();

    return ReportModel(
      id: doc.id,
      listingId: data['listingId'] ?? '',
      listingTitle: data['listingTitle'] ?? '',
      reportedBy: data['reportedBy'] ?? '',
      reportedByName: data['reportedByName'] ?? 'User',
      reason: data['reason'] ?? '',
      createdAt: created,
      resolved: data['resolved'] ?? false,
    );
  }
}
