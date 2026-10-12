import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/config/app_config.dart';
import '../../../core/enums/listing_enums.dart';
import '../../../core/errors/app_exception.dart';
import '../models/listing_filter.dart';
import '../models/listing_model.dart';

class PaginatedListingsResult {
  final List<ListingModel> listings;
  final DocumentSnapshot? lastDocument;
  final bool hasMore;
  final bool isFromCache;

  const PaginatedListingsResult({
    required this.listings,
    this.lastDocument,
    required this.hasMore,
    this.isFromCache = false,
  });
}

/// Repository responsible for Firestore operations on accommodation listings
class ListingsRepository {
  final FirebaseFirestore _firestore;

  ListingsRepository([FirebaseFirestore? firestore])
      : _firestore = firestore ?? FirebaseFirestore.instance;

  CollectionReference<Map<String, dynamic>> get _listingsRef =>
      _firestore.collection('listings');

  /// Fetches approved listings for the Explore feed with filtering and pagination
  Future<PaginatedListingsResult> fetchApprovedListings({
    ListingFilter? filter,
    DocumentSnapshot? startAfterDoc,
    int limit = AppConfig.listingPageSize,
  }) async {
    try {
      Query<Map<String, dynamic>> query = _listingsRef
          .where('status', isEqualTo: 'approved')
          .where('isArchived', isEqualTo: false);

      // Apply discrete equality filters
      if (filter?.propertyType != null) {
        query = query.where('type', isEqualTo: filter!.propertyType!.value);
      }
      if (filter?.furnishing != null) {
        query = query.where('furnishing', isEqualTo: filter!.furnishing!.value);
      }
      if (filter?.genderPreference != null) {
        query = query.where('genderPreference', isEqualTo: filter!.genderPreference!.value);
      }
      if (filter?.locality != null && filter!.locality!.trim().isNotEmpty) {
        query = query.where('locality', isEqualTo: filter.locality!.trim());
      }

      // Apply ordering
      switch (filter?.sortBy ?? ListingSortOption.newest) {
        case ListingSortOption.rentLowToHigh:
          query = query.orderBy('rentPerMonth', descending: false);
          break;
        case ListingSortOption.rentHighToLow:
          query = query.orderBy('rentPerMonth', descending: true);
          break;
        case ListingSortOption.newest:
          query = query.orderBy('createdAt', descending: true);
          break;
      }

      // Pagination cursor
      if (startAfterDoc != null) {
        query = query.startAfterDocument(startAfterDoc);
      }

      query = query.limit(limit);

      final snapshot = await query.get();
      var results = snapshot.docs.map((doc) => ListingModel.fromDocument(doc)).toList();

      // Client-side search and rent filtering for seamless UX
      if (filter != null) {
        if (filter.minRent != null) {
          results = results.where((item) => item.rentPerMonth >= filter.minRent!).toList();
        }
        if (filter.maxRent != null) {
          results = results.where((item) => item.rentPerMonth <= filter.maxRent!).toList();
        }
        if (filter.locality != null && filter.locality!.trim().isNotEmpty) {
          final targetLoc = filter.locality!.trim().toLowerCase();
          results = results.where((item) => item.locality.trim().toLowerCase() == targetLoc).toList();
        }
        if (filter.propertyType != null) {
          results = results.where((item) => item.type == filter.propertyType).toList();
        }
        if (filter.furnishing != null) {
          results = results.where((item) => item.furnishing == filter.furnishing).toList();
        }
        if (filter.genderPreference != null) {
          results = results.where((item) => item.genderPreference == filter.genderPreference).toList();
        }
        if (filter.searchQuery != null && filter.searchQuery!.trim().isNotEmpty) {
          final q = filter.searchQuery!.trim().toLowerCase();
          results = results.where((item) {
            final matchTitle = item.title.toLowerCase().contains(q);
            final matchLocality = item.locality.toLowerCase().contains(q);
            final matchAddress = item.fullAddress.toLowerCase().contains(q);
            final matchDesc = item.description.toLowerCase().contains(q);
            return matchTitle || matchLocality || matchAddress || matchDesc;
          }).toList();
        }
      }

      final lastDoc = snapshot.docs.isNotEmpty ? snapshot.docs.last : null;
      final hasMore = snapshot.docs.length >= limit;

      debugPrint('[ListingsRepository] Fetched ${results.length} listings (raw docs: ${snapshot.docs.length})');
      return PaginatedListingsResult(
        listings: results,
        lastDocument: lastDoc,
        hasMore: hasMore,
        isFromCache: snapshot.metadata.isFromCache,
      );
    } catch (e) {
      debugPrint('[ListingsRepository] Error fetching approved listings: $e');
      throw AppException('Failed to load listings: $e', originalError: e);
    }
  }

  /// Real-time stream of a specific listing
  Stream<ListingModel?> watchListing(String id) {
    return _listingsRef.doc(id).snapshots().map((doc) {
      if (!doc.exists || doc.data() == null) return null;
      return ListingModel.fromDocument(doc);
    });
  }

  /// Get single listing by document ID
  Future<ListingModel?> getListingById(String id) async {
    try {
      final doc = await _listingsRef.doc(id).get();
      if (!doc.exists || doc.data() == null) return null;
      return ListingModel.fromDocument(doc);
    } catch (e) {
      debugPrint('[ListingsRepository] Error getting listing $id: $e');
      throw AppException('Failed to load listing: $e', originalError: e);
    }
  }

  /// Real-time stream of all listings owned by the user
  Stream<List<ListingModel>> watchMyListings(String userId) {
    return _listingsRef
        .where('ownerId', isEqualTo: userId)
        .snapshots()
        .map((snapshot) {
          final list = snapshot.docs.map((doc) => ListingModel.fromDocument(doc)).toList();
          list.sort((a, b) => b.createdAt.compareTo(a.createdAt));
          debugPrint('[ListingsRepository] watchMyListings ($userId) emitted ${list.length} listings');
          return list;
        });
  }

  /// Fetches listings owned by the user filtered by status
  Future<List<ListingModel>> fetchMyListings({
    required String userId,
    required ListingStatus status,
  }) async {
    try {
      final snapshot = await _listingsRef
          .where('ownerId', isEqualTo: userId)
          .get();

      var list = snapshot.docs.map((doc) => ListingModel.fromDocument(doc)).toList();
      list = list.where((item) => item.status == status && !item.isArchived).toList();
      list.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      return list;
    } catch (e) {
      debugPrint('[ListingsRepository] Error fetching my listings ($status): $e');
      throw AppException('Failed to load your listings: $e', originalError: e);
    }
  }

  /// Generates a unique document ID for a listing session
  String generateListingDocId() => _listingsRef.doc().id;

  /// Creates a new accommodation listing with an explicit document ID using set(),
  /// ensuring retries or multiple submit taps never create duplicate listings.
  /// If isSuperAdmin == true, listing is directly approved without review.
  Future<String> createListing(
    ListingModel listing, {
    bool isAutoApproved = false,
    String? reviewerName,
    String? reviewerRole,
  }) async {
    try {
      final docId = listing.id.isNotEmpty ? listing.id : generateListingDocId();
      final now = DateTime.now();
      final targetStatus = isAutoApproved ? ListingStatus.approved : ListingStatus.pending;
      final enforcedListing = listing.copyWith(
        id: docId,
        status: targetStatus,
        reviewedBy: isAutoApproved ? listing.ownerId : null,
        reviewedByName: isAutoApproved ? (reviewerName ?? listing.ownerName) : null,
        reviewedByRole: isAutoApproved ? (reviewerRole ?? 'Approver') : null,
        reviewedAt: isAutoApproved ? now : null,
        isArchived: false,
        createdAt: now,
        updatedAt: now,
      );

      await _listingsRef.doc(docId).set(enforcedListing.toMap());
      debugPrint('[ListingsRepository] Set listing $docId with status: ${targetStatus.value} (isArchived: false, isAutoApproved: $isAutoApproved)');
      return docId;
    } catch (e) {
      debugPrint('[ListingsRepository] Error creating/setting listing: $e');
      throw AppException('Failed to create listing: $e', originalError: e);
    }
  }

  /// Updates an existing listing. If the listing was previously approved,
  /// security rules dictate it resets to 'pending'.
  Future<void> updateListing(ListingModel listing) async {
    try {
      final wasApproved = listing.status == ListingStatus.approved;
      final targetStatus = wasApproved ? ListingStatus.pending : listing.status;

      final updates = listing.copyWith(
        status: targetStatus,
        clearRejectionReason: true,
        isArchived: false,
        updatedAt: DateTime.now(),
      );

      await _listingsRef.doc(listing.id).update(updates.toMap());
      debugPrint('[ListingsRepository] Updated listing ${listing.id} (status: ${targetStatus.value})');
    } catch (e) {
      debugPrint('[ListingsRepository] Error updating listing: $e');
      throw AppException('Failed to update listing: $e', originalError: e);
    }
  }

  /// Archives a listing (soft delete by owner)
  Future<void> archiveListing(String listingId) async {
    try {
      await _listingsRef.doc(listingId).update({
        'status': ListingStatus.archived.value,
        'isArchived': true,
        'updatedAt': Timestamp.now(),
      });
      debugPrint('[ListingsRepository] Archived listing $listingId (isArchived: true)');
    } catch (e) {
      debugPrint('[ListingsRepository] Error archiving listing: $e');
      throw AppException('Failed to archive listing: $e', originalError: e);
    }
  }

  /// Resubmits a rejected listing for approval
  Future<void> resubmitListing(ListingModel listing) async {
    try {
      final updates = listing.copyWith(
        status: ListingStatus.pending,
        clearRejectionReason: true,
        updatedAt: DateTime.now(),
      );

      await _listingsRef.doc(listing.id).update(updates.toMap());
      debugPrint('[ListingsRepository] Resubmitted listing ${listing.id} for approval');
    } catch (e) {
      debugPrint('[ListingsRepository] Error resubmitting listing: $e');
      throw AppException('Failed to resubmit listing: $e', originalError: e);
    }
  }

  /// Fetches pending listings for the review queue, oldest first (15 per page)
  Future<PaginatedListingsResult> fetchReviewQueue({
    DocumentSnapshot? startAfterDoc,
    int limit = 15,
  }) async {
    try {
      Query<Map<String, dynamic>> query = _listingsRef
          .where('status', isEqualTo: 'pending')
          .orderBy('createdAt', descending: false);

      if (startAfterDoc != null) {
        query = query.startAfterDocument(startAfterDoc);
      }
      query = query.limit(limit);

      final snapshot = await query.get();
      final results = snapshot.docs.map((doc) => ListingModel.fromDocument(doc)).toList();
      final lastDoc = snapshot.docs.isNotEmpty ? snapshot.docs.last : null;
      final hasMore = snapshot.docs.length >= limit;

      debugPrint('[ListingsRepository] Fetched ${results.length} review queue listings');
      return PaginatedListingsResult(
        listings: results,
        lastDocument: lastDoc,
        hasMore: hasMore,
      );
    } catch (e) {
      debugPrint('[ListingsRepository] Error fetching review queue: $e');
      throw AppException('Failed to load review queue: $e', originalError: e);
    }
  }

  /// Cheap aggregate count of pending listings
  Future<int> getPendingReviewCount() async {
    try {
      final snapshot = await _listingsRef
          .where('status', isEqualTo: 'pending')
          .count()
          .get();
      return snapshot.count ?? 0;
    } catch (e) {
      debugPrint('[ListingsRepository] Error getting pending review count: $e');
      return 0;
    }
  }

  /// Approves a listing and writes a notification document to users/{ownerId}/notifications in a single batch
  Future<void> approveListingWithBatch({
    required String listingId,
    required String ownerId,
    required String reviewerId,
    required String reviewerName,
    required String reviewerRole,
    required String title,
    Map<String, dynamic>? minorEdits,
  }) async {
    try {
      final batch = _firestore.batch();
      final listingDoc = _listingsRef.doc(listingId);
      final notificationDoc = _firestore
          .collection('users')
          .doc(ownerId)
          .collection('notifications')
          .doc();

      final now = FieldValue.serverTimestamp();
      final finalTitle = minorEdits?['title'] as String? ?? title;

      final listingUpdates = <String, dynamic>{
        'status': ListingStatus.approved.value,
        'reviewedBy': reviewerId,
        'reviewedByName': reviewerName,
        'reviewedByRole': reviewerRole,
        'reviewedAt': now,
        'rejectionReason': FieldValue.delete(),
        'updatedAt': now,
      };

      if (minorEdits != null) {
        minorEdits.forEach((k, v) {
          if (k != 'status' && k != 'reviewedBy' && k != 'reviewedByName' && k != 'reviewedByRole' && k != 'reviewedAt' && k != 'rejectionReason') {
            listingUpdates[k] = v;
          }
        });
      }

      batch.update(listingDoc, listingUpdates);

      batch.set(notificationDoc, {
        'type': 'approved',
        'listingId': listingId,
        'listingTitle': finalTitle,
        'message': 'Your listing "$finalTitle" has been approved and is now live on Explore.',
        'createdAt': now,
        'read': false,
      });

      await batch.commit();
      debugPrint('[ListingsRepository] Successfully approved listing $listingId and created notification in batch');
    } catch (e) {
      debugPrint('[ListingsRepository] Error approving listing with batch: $e');
      throw AppException('Failed to approve listing: $e', originalError: e);
    }
  }

  /// Rejects a listing and writes a notification document to users/{ownerId}/notifications in a single batch
  Future<void> rejectListingWithBatch({
    required String listingId,
    required String ownerId,
    required String reviewerId,
    required String reviewerName,
    required String reviewerRole,
    required String title,
    required String rejectionReason,
  }) async {
    try {
      final batch = _firestore.batch();
      final listingDoc = _listingsRef.doc(listingId);
      final notificationDoc = _firestore
          .collection('users')
          .doc(ownerId)
          .collection('notifications')
          .doc();

      final now = FieldValue.serverTimestamp();

      batch.update(listingDoc, {
        'status': ListingStatus.rejected.value,
        'rejectionReason': rejectionReason,
        'reviewedBy': reviewerId,
        'reviewedByName': reviewerName,
        'reviewedByRole': reviewerRole,
        'reviewedAt': now,
        'updatedAt': now,
      });

      batch.set(notificationDoc, {
        'type': 'rejected',
        'listingId': listingId,
        'listingTitle': title,
        'message': 'Your listing "$title" was not approved: $rejectionReason',
        'rejectionReason': rejectionReason,
        'createdAt': now,
        'read': false,
      });

      await batch.commit();
      debugPrint('[ListingsRepository] Successfully rejected listing $listingId and created notification in batch');
    } catch (e) {
      debugPrint('[ListingsRepository] Error rejecting listing with batch: $e');
      throw AppException('Failed to reject listing: $e', originalError: e);
    }
  }
}

final listingsRepositoryProvider = Provider<ListingsRepository>((ref) {
  return ListingsRepository();
});
