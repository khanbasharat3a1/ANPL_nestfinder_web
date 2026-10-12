import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/errors/app_exception.dart';

/// Repository for submitting and tracking accommodation reports
class ReportsRepository {
  final FirebaseFirestore _firestore;

  ReportsRepository([FirebaseFirestore? firestore])
      : _firestore = firestore ?? FirebaseFirestore.instance;

  Future<void> submitReport({
    required String listingId,
    required String listingTitle,
    required String reportedBy,
    required String reportedByName,
    required String reason,
  }) async {
    try {
      final reportId = '${listingId}_$reportedBy';

      await _firestore.collection('reports').doc(reportId).set({
        'listingId': listingId,
        'listingTitle': listingTitle,
        'reportedBy': reportedBy,
        'reporterName': reportedByName,
        'reason': reason.trim(),
        'status': 'open',
        'createdAt': FieldValue.serverTimestamp(),
      });
      debugPrint('[ReportsRepository] Report submitted with deterministic ID $reportId');
    } catch (e) {
      debugPrint('[ReportsRepository] Error submitting report: $e');
      throw AppException('Failed to submit report: $e', originalError: e);
    }
  }
}

final reportsRepositoryProvider = Provider<ReportsRepository>((ref) {
  return ReportsRepository();
});
