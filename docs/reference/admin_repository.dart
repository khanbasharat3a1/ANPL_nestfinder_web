import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/enums/listing_enums.dart';
import '../../../core/enums/user_role.dart';
import '../../../core/errors/app_exception.dart';
import '../../auth/models/user_model.dart';
import '../../listings/models/listing_model.dart';
import '../../listings/repositories/listings_repository.dart';
import '../../reports/models/report_model.dart';
import '../models/admin_log_model.dart';
import '../models/app_config_model.dart';

class AdminOverviewCounts {
  final int totalUsers;
  final int approvers;
  final int superAdmins;
  final int pendingListings;
  final int approvedListings;
  final int rejectedListings;
  final int archivedListings;
  final int openReports;

  const AdminOverviewCounts({
    this.totalUsers = 0,
    this.approvers = 0,
    this.superAdmins = 0,
    this.pendingListings = 0,
    this.approvedListings = 0,
    this.rejectedListings = 0,
    this.archivedListings = 0,
    this.openReports = 0,
  });
}

class PaginatedUsersResult {
  final List<UserModel> users;
  final DocumentSnapshot? lastDocument;
  final bool hasMore;

  const PaginatedUsersResult({
    required this.users,
    this.lastDocument,
    required this.hasMore,
  });
}

class AdminRepository {
  final FirebaseFirestore _firestore;

  AdminRepository([FirebaseFirestore? firestore])
      : _firestore = firestore ?? FirebaseFirestore.instance;

  CollectionReference<Map<String, dynamic>> get _usersRef => _firestore.collection('users');
  CollectionReference<Map<String, dynamic>> get _listingsRef => _firestore.collection('listings');
  CollectionReference<Map<String, dynamic>> get _reportsRef => _firestore.collection('reports');
  CollectionReference<Map<String, dynamic>> get _adminLogsRef => _firestore.collection('adminLogs');
  DocumentReference<Map<String, dynamic>> get _configRef => _firestore.collection('config').doc('app');

  // -------------------------------------------------------------
  // Audit Logging
  // -------------------------------------------------------------
  Future<void> logAction({
    required String actorUid,
    required String action,
    required String targetId,
    required String details,
  }) async {
    try {
      await _adminLogsRef.add({
        'actorUid': actorUid,
        'action': action,
        'targetId': targetId,
        'details': details,
        'createdAt': FieldValue.serverTimestamp(),
      });
    } catch (e) {
      debugPrint('[AdminRepository] Error writing admin log: $e');
    }
  }

  Stream<List<AdminLogModel>> watchRecentLogs({int limit = 50}) {
    return _adminLogsRef
        .orderBy('createdAt', descending: true)
        .limit(limit)
        .snapshots()
        .map((snap) => snap.docs.map((d) => AdminLogModel.fromDocument(d)).toList())
        .handleError((e) {
          debugPrint('[AdminRepository] Error streaming admin logs: $e');
          return <AdminLogModel>[];
        });
  }

  // -------------------------------------------------------------
  // Overview Aggregate Counts
  // -------------------------------------------------------------
  Future<AdminOverviewCounts> getOverviewCounts() async {
    try {
      final results = await Future.wait([
        _usersRef.count().get(), // 0: total users
        _usersRef.where('role', isEqualTo: 'approver').count().get(), // 1: approvers
        _usersRef.where('role', isEqualTo: 'super_admin').count().get(), // 2: super_admins
        _listingsRef.where('status', isEqualTo: 'pending').count().get(), // 3: pending
        _listingsRef.where('status', isEqualTo: 'approved').count().get(), // 4: approved
        _listingsRef.where('status', isEqualTo: 'rejected').count().get(), // 5: rejected
        _listingsRef.where('isArchived', isEqualTo: true).count().get(), // 6: archived
        _reportsRef.where('status', isEqualTo: 'open').count().get(), // 7: open reports
      ]);

      return AdminOverviewCounts(
        totalUsers: results[0].count ?? 0,
        approvers: results[1].count ?? 0,
        superAdmins: results[2].count ?? 0,
        pendingListings: results[3].count ?? 0,
        approvedListings: results[4].count ?? 0,
        rejectedListings: results[5].count ?? 0,
        archivedListings: results[6].count ?? 0,
        openReports: results[7].count ?? 0,
      );
    } catch (e) {
      debugPrint('[AdminRepository] Error getting overview counts: $e');
      throw AppException('Failed to load overview counts: $e', originalError: e);
    }
  }

  // -------------------------------------------------------------
  // User Management
  // -------------------------------------------------------------
  Future<PaginatedUsersResult> fetchUsers({
    String? filterRole,
    bool? isBanned,
    DocumentSnapshot? startAfterDoc,
    int limit = 20,
  }) async {
    try {
      Query<Map<String, dynamic>> query = _usersRef.orderBy('createdAt', descending: true);

      if (filterRole != null && filterRole.isNotEmpty) {
        query = query.where('role', isEqualTo: filterRole);
      }
      if (isBanned != null) {
        query = query.where('isBanned', isEqualTo: isBanned);
      }
      if (startAfterDoc != null) {
        query = query.startAfterDocument(startAfterDoc);
      }
      query = query.limit(limit);

      final snap = await query.get();
      final users = snap.docs.map((d) => UserModel.fromDocument(d)).toList();
      return PaginatedUsersResult(
        users: users,
        lastDocument: snap.docs.isNotEmpty ? snap.docs.last : null,
        hasMore: snap.docs.length >= limit,
      );
    } catch (e) {
      debugPrint('[AdminRepository] Error fetching users: $e');
      throw AppException('Failed to load users: $e', originalError: e);
    }
  }

  Future<void> updateUserRole({
    required String targetUid,
    required UserRole newRole,
    required String actorUid,
  }) async {
    if (targetUid == actorUid) {
      throw const AppException('You cannot modify your own role.');
    }

    try {
      final doc = await _usersRef.doc(targetUid).get();
      if (!doc.exists) throw const AppException('User document not found.');
      final currentRole = doc.data()?['role'] as String?;

      if (currentRole == 'super_admin' && newRole != UserRole.superAdmin) {
        final countSnap = await _usersRef.where('role', isEqualTo: 'super_admin').count().get();
        if ((countSnap.count ?? 0) <= 1) {
          throw const AppException('Action blocked: Cannot demote the last remaining Super Admin.');
        }
      }

      await _usersRef.doc(targetUid).update({'role': newRole.value});
      await logAction(
        actorUid: actorUid,
        action: 'role_change',
        targetId: targetUid,
        details: 'Changed role from $currentRole to ${newRole.value}',
      );
    } catch (e) {
      if (e is AppException) rethrow;
      throw AppException('Failed to update role: $e', originalError: e);
    }
  }

  Future<void> toggleUserBan({
    required String targetUid,
    required bool ban,
    required String actorUid,
  }) async {
    if (targetUid == actorUid) {
      throw const AppException('You cannot ban yourself.');
    }

    try {
      final doc = await _usersRef.doc(targetUid).get();
      if (!doc.exists) throw const AppException('User document not found.');
      final currentRole = doc.data()?['role'] as String?;

      if (currentRole == 'super_admin' && ban) {
        final countSnap = await _usersRef.where('role', isEqualTo: 'super_admin').count().get();
        if ((countSnap.count ?? 0) <= 1) {
          throw const AppException('Action blocked: Cannot ban the last remaining Super Admin.');
        }
      }

      await _usersRef.doc(targetUid).update({'isBanned': ban});
      await logAction(
        actorUid: actorUid,
        action: ban ? 'ban_user' : 'unban_user',
        targetId: targetUid,
        details: ban ? 'Banned user' : 'Unbanned user',
      );
    } catch (e) {
      if (e is AppException) rethrow;
      throw AppException('Failed to update ban status: $e', originalError: e);
    }
  }

  Future<int> hideAllUserListings({
    required String targetUid,
    required String actorUid,
  }) async {
    try {
      final snap = await _listingsRef.where('ownerId', isEqualTo: targetUid).get();
      if (snap.docs.isEmpty) return 0;

      final batch = _firestore.batch();
      for (final doc in snap.docs) {
        batch.update(doc.reference, {
          'isArchived': true,
          'status': ListingStatus.archived.value,
          'updatedAt': FieldValue.serverTimestamp(),
        });
      }
      await batch.commit();

      await logAction(
        actorUid: actorUid,
        action: 'hide_user_listings',
        targetId: targetUid,
        details: 'Archived ${snap.docs.length} listings for user',
      );
      return snap.docs.length;
    } catch (e) {
      throw AppException('Failed to hide user listings: $e', originalError: e);
    }
  }

  Future<int> backfillUserSearchFields({required String actorUid}) async {
    try {
      final snap = await _usersRef.get();
      if (snap.docs.isEmpty) return 0;

      final batch = _firestore.batch();
      var updated = 0;

      for (final doc in snap.docs) {
        final data = doc.data();
        final name = data['name'] as String? ?? '';
        final email = data['email'] as String? ?? '';
        final nameLower = data['nameLower'] as String?;
        final emailLower = data['emailLower'] as String?;

        if (nameLower == null || emailLower == null) {
          batch.update(doc.reference, {
            'nameLower': name.toLowerCase(),
            'emailLower': email.toLowerCase(),
          });
          updated++;
        }
      }

      if (updated > 0) {
        await batch.commit();
        await logAction(
          actorUid: actorUid,
          action: 'backfill_search_fields',
          targetId: 'users',
          details: 'Backfilled lowercase search fields on $updated user docs',
        );
      }
      return updated;
    } catch (e) {
      throw AppException('Failed to backfill user search fields: $e', originalError: e);
    }
  }

  // -------------------------------------------------------------
  // Listing Management (Admin)
  // -------------------------------------------------------------
  Future<PaginatedListingsResult> fetchAllListingsAdmin({
    String? status,
    bool? isArchived,
    DocumentSnapshot? startAfterDoc,
    int limit = 20,
  }) async {
    try {
      Query<Map<String, dynamic>> query = _listingsRef.orderBy('createdAt', descending: true);

      if (status != null && status.isNotEmpty) {
        query = query.where('status', isEqualTo: status);
      }
      if (isArchived != null) {
        query = query.where('isArchived', isEqualTo: isArchived);
      }
      if (startAfterDoc != null) {
        query = query.startAfterDocument(startAfterDoc);
      }
      query = query.limit(limit);

      final snap = await query.get();
      final listings = snap.docs.map((d) => ListingModel.fromDocument(d)).toList();
      return PaginatedListingsResult(
        listings: listings,
        lastDocument: snap.docs.isNotEmpty ? snap.docs.last : null,
        hasMore: snap.docs.length >= limit,
      );
    } catch (e) {
      throw AppException('Failed to load listings: $e', originalError: e);
    }
  }

  Future<void> forceApproveListing({
    required String listingId,
    required String ownerId,
    required String title,
    required String actorUid,
  }) async {
    try {
      final batch = _firestore.batch();
      final now = FieldValue.serverTimestamp();

      batch.update(_listingsRef.doc(listingId), {
        'status': ListingStatus.approved.value,
        'reviewedBy': actorUid,
        'reviewedAt': now,
        'isArchived': false,
        'rejectionReason': FieldValue.delete(),
        'updatedAt': now,
      });

      final notifDoc = _usersRef.doc(ownerId).collection('notifications').doc();
      batch.set(notifDoc, {
        'type': 'approved',
        'listingId': listingId,
        'listingTitle': title,
        'message': 'Your listing "$title" has been approved by admin and is live on Explore.',
        'createdAt': now,
        'read': false,
      });

      await batch.commit();
      await logAction(
        actorUid: actorUid,
        action: 'force_approve',
        targetId: listingId,
        details: 'Force approved listing "$title"',
      );
    } catch (e) {
      throw AppException('Failed to force approve listing: $e', originalError: e);
    }
  }

  Future<void> forceRejectListing({
    required String listingId,
    required String ownerId,
    required String title,
    required String reason,
    required String actorUid,
  }) async {
    try {
      final batch = _firestore.batch();
      final now = FieldValue.serverTimestamp();

      batch.update(_listingsRef.doc(listingId), {
        'status': ListingStatus.rejected.value,
        'rejectionReason': reason,
        'reviewedBy': actorUid,
        'reviewedAt': now,
        'updatedAt': now,
      });

      final notifDoc = _usersRef.doc(ownerId).collection('notifications').doc();
      batch.set(notifDoc, {
        'type': 'rejected',
        'listingId': listingId,
        'listingTitle': title,
        'message': 'Your listing "$title" was rejected by admin: $reason',
        'rejectionReason': reason,
        'createdAt': now,
        'read': false,
      });

      await batch.commit();
      await logAction(
        actorUid: actorUid,
        action: 'force_reject',
        targetId: listingId,
        details: 'Force rejected listing "$title": $reason',
      );
    } catch (e) {
      throw AppException('Failed to force reject listing: $e', originalError: e);
    }
  }

  Future<void> toggleListingArchive({
    required String listingId,
    required bool archive,
    required String actorUid,
  }) async {
    try {
      await _listingsRef.doc(listingId).update({
        'isArchived': archive,
        if (archive) 'status': ListingStatus.archived.value,
        'updatedAt': FieldValue.serverTimestamp(),
      });
      await logAction(
        actorUid: actorUid,
        action: archive ? 'archive_listing' : 'unarchive_listing',
        targetId: listingId,
        details: archive ? 'Archived listing' : 'Unarchived listing',
      );
    } catch (e) {
      throw AppException('Failed to update archive status: $e', originalError: e);
    }
  }

  Future<void> deleteListing({
    required String listingId,
    required String title,
    required String actorUid,
  }) async {
    try {
      await _listingsRef.doc(listingId).delete();
      await logAction(
        actorUid: actorUid,
        action: 'delete_listing',
        targetId: listingId,
        details: 'Deleted listing "$title" (Cloudinary images stay behind)',
      );
    } catch (e) {
      throw AppException('Failed to delete listing: $e', originalError: e);
    }
  }

  // Bulk operations (up to 50 items)
  Future<void> bulkApproveListings(List<ListingModel> listings, String actorUid) async {
    if (listings.isEmpty) return;
    try {
      final batch = _firestore.batch();
      final now = FieldValue.serverTimestamp();

      for (final l in listings) {
        batch.update(_listingsRef.doc(l.id), {
          'status': ListingStatus.approved.value,
          'reviewedBy': actorUid,
          'reviewedAt': now,
          'isArchived': false,
          'rejectionReason': FieldValue.delete(),
          'updatedAt': now,
        });

        final notif = _usersRef.doc(l.ownerId).collection('notifications').doc();
        batch.set(notif, {
          'type': 'approved',
          'listingId': l.id,
          'listingTitle': l.title,
          'message': 'Your listing "${l.title}" has been approved by admin.',
          'createdAt': now,
          'read': false,
        });
      }

      await batch.commit();
      await logAction(
        actorUid: actorUid,
        action: 'bulk_approve',
        targetId: 'multiple',
        details: 'Bulk approved ${listings.length} listings',
      );
    } catch (e) {
      throw AppException('Failed to bulk approve listings: $e', originalError: e);
    }
  }

  Future<void> bulkRejectListings(List<ListingModel> listings, String reason, String actorUid) async {
    if (listings.isEmpty) return;
    try {
      final batch = _firestore.batch();
      final now = FieldValue.serverTimestamp();

      for (final l in listings) {
        batch.update(_listingsRef.doc(l.id), {
          'status': ListingStatus.rejected.value,
          'rejectionReason': reason,
          'reviewedBy': actorUid,
          'reviewedAt': now,
          'updatedAt': now,
        });

        final notif = _usersRef.doc(l.ownerId).collection('notifications').doc();
        batch.set(notif, {
          'type': 'rejected',
          'listingId': l.id,
          'listingTitle': l.title,
          'message': 'Your listing "${l.title}" was not approved: $reason',
          'rejectionReason': reason,
          'createdAt': now,
          'read': false,
        });
      }

      await batch.commit();
      await logAction(
        actorUid: actorUid,
        action: 'bulk_reject',
        targetId: 'multiple',
        details: 'Bulk rejected ${listings.length} listings: $reason',
      );
    } catch (e) {
      throw AppException('Failed to bulk reject listings: $e', originalError: e);
    }
  }

  Future<void> bulkArchiveListings(List<ListingModel> listings, String actorUid) async {
    if (listings.isEmpty) return;
    try {
      final batch = _firestore.batch();
      final now = FieldValue.serverTimestamp();

      for (final l in listings) {
        batch.update(_listingsRef.doc(l.id), {
          'isArchived': true,
          'status': ListingStatus.archived.value,
          'updatedAt': now,
        });
      }

      await batch.commit();
      await logAction(
        actorUid: actorUid,
        action: 'bulk_archive',
        targetId: 'multiple',
        details: 'Bulk archived ${listings.length} listings',
      );
    } catch (e) {
      throw AppException('Failed to bulk archive listings: $e', originalError: e);
    }
  }

  Future<void> bulkDeleteListings(List<ListingModel> listings, String actorUid) async {
    if (listings.isEmpty) return;
    try {
      final batch = _firestore.batch();

      for (final l in listings) {
        batch.delete(_listingsRef.doc(l.id));
      }

      await batch.commit();
      await logAction(
        actorUid: actorUid,
        action: 'bulk_delete',
        targetId: 'multiple',
        details: 'Bulk deleted ${listings.length} listings',
      );
    } catch (e) {
      throw AppException('Failed to bulk delete listings: $e', originalError: e);
    }
  }

  // -------------------------------------------------------------
  // Reports Management
  // -------------------------------------------------------------
  Future<List<ReportModel>> fetchReports({String? status, int limit = 50}) async {
    try {
      Query<Map<String, dynamic>> query = _reportsRef.orderBy('createdAt', descending: true);
      if (status != null && status.isNotEmpty) {
        query = query.where('status', isEqualTo: status);
      }
      query = query.limit(limit);

      final snap = await query.get();
      return snap.docs.map((d) => ReportModel.fromDocument(d)).toList();
    } catch (e) {
      throw AppException('Failed to load reports: $e', originalError: e);
    }
  }

  Future<void> submitReport({
    required String listingId,
    required String listingTitle,
    required String reportedBy,
    required String reporterName,
    required String reason,
  }) async {
    final reportId = '${listingId}_$reportedBy';
    try {
      await _reportsRef.doc(reportId).set({
        'listingId': listingId,
        'listingTitle': listingTitle,
        'reportedBy': reportedBy,
        'reporterName': reporterName,
        'reason': reason,
        'status': 'open',
        'createdAt': FieldValue.serverTimestamp(),
      });
    } catch (e) {
      throw AppException('Failed to submit report: $e', originalError: e);
    }
  }

  Future<void> dismissReport({
    required String reportId,
    required String actorUid,
  }) async {
    try {
      await _reportsRef.doc(reportId).update({
        'status': 'resolved',
        'resolvedAt': FieldValue.serverTimestamp(),
        'resolvedBy': actorUid,
      });
      await logAction(
        actorUid: actorUid,
        action: 'dismiss_report',
        targetId: reportId,
        details: 'Dismissed community report',
      );
    } catch (e) {
      throw AppException('Failed to dismiss report: $e', originalError: e);
    }
  }

  Future<void> takedownReport({
    required String reportId,
    required String listingId,
    required String ownerId,
    required String listingTitle,
    required String actorUid,
  }) async {
    try {
      final batch = _firestore.batch();
      final now = FieldValue.serverTimestamp();

      batch.update(_listingsRef.doc(listingId), {
        'isArchived': true,
        'status': ListingStatus.archived.value,
        'updatedAt': now,
      });

      batch.update(_reportsRef.doc(reportId), {
        'status': 'resolved',
        'resolvedAt': now,
        'resolvedBy': actorUid,
      });

      final notif = _usersRef.doc(ownerId).collection('notifications').doc();
      batch.set(notif, {
        'type': 'rejected',
        'listingId': listingId,
        'listingTitle': listingTitle,
        'message': 'Your listing "$listingTitle" was taken down following a verified community report.',
        'createdAt': now,
        'read': false,
      });

      await batch.commit();
      await logAction(
        actorUid: actorUid,
        action: 'takedown_report',
        targetId: reportId,
        details: 'Took down listing "$listingTitle" and resolved report $reportId',
      );
    } catch (e) {
      throw AppException('Failed to process report take down: $e', originalError: e);
    }
  }

  // -------------------------------------------------------------
  // App Configuration
  // -------------------------------------------------------------
  Future<AppConfigModel> fetchAppConfig() async {
    try {
      final doc = await _configRef.get();
      return AppConfigModel.fromDocument(doc);
    } catch (e) {
      debugPrint('[AdminRepository] Error fetching app config: $e');
      return AppConfigModel.defaults();
    }
  }

  Stream<AppConfigModel> watchAppConfig() {
    return _configRef.snapshots().map((doc) => AppConfigModel.fromDocument(doc));
  }

  Future<void> updateAppConfig(AppConfigModel config, String actorUid) async {
    try {
      await _configRef.set(config.toMap(), SetOptions(merge: true));
      await logAction(
        actorUid: actorUid,
        action: 'update_app_config',
        targetId: 'config/app',
        details: 'Updated app settings (localities, amenities, office coordinates)',
      );
    } catch (e) {
      throw AppException('Failed to update app config: $e', originalError: e);
    }
  }
}

final adminRepositoryProvider = Provider<AdminRepository>((ref) {
  return AdminRepository();
});
