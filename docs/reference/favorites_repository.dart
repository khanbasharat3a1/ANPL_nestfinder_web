import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/enums/listing_enums.dart';
import '../../../core/errors/app_exception.dart';
import '../models/listing_model.dart';

/// Repository managing user favorites subcollection at `users/{userId}/favorites/{listingId}`
class FavoritesRepository {
  final FirebaseFirestore _firestore;

  FavoritesRepository([FirebaseFirestore? firestore])
      : _firestore = firestore ?? FirebaseFirestore.instance;

  CollectionReference<Map<String, dynamic>> _userFavorites(String userId) =>
      _firestore.collection('users').doc(userId).collection('favorites');

  /// Real-time stream of favorited listing IDs for the given user
  Stream<Set<String>> watchFavoriteIds(String userId) {
    if (userId.isEmpty) return Stream.value({});
    return _userFavorites(userId).snapshots().map((snapshot) {
      return snapshot.docs.map((doc) => doc.id).toSet();
    });
  }

  /// Toggles favorite status for a listing
  Future<void> toggleFavorite({
    required String userId,
    required String listingId,
    required bool isFavorite,
  }) async {
    try {
      final docRef = _userFavorites(userId).doc(listingId);
      if (isFavorite) {
        await docRef.set({
          'listingId': listingId,
          'savedAt': Timestamp.now(),
        });
        debugPrint('[FavoritesRepository] Added $listingId to favorites');
      } else {
        await docRef.delete();
        debugPrint('[FavoritesRepository] Removed $listingId from favorites');
      }
    } catch (e) {
      debugPrint('[FavoritesRepository] Error toggling favorite: $e');
      throw AppException('Failed to update favorite: $e', originalError: e);
    }
  }

  /// Fetches full ListingModel objects for all favorited listings of a user
  Future<List<ListingModel>> fetchFavoriteListings(String userId) async {
    try {
      final snapshot = await _userFavorites(userId).get();
      if (snapshot.docs.isEmpty) return [];

      final listingIds = snapshot.docs.map((d) => d.id).toList();
      final results = <ListingModel>[];

      // Fetch documents in chunks (max 30 per whereIn)
      for (var i = 0; i < listingIds.length; i += 30) {
        final chunk = listingIds.sublist(
          i,
          i + 30 > listingIds.length ? listingIds.length : i + 30,
        );

        final listingsSnapshot = await _firestore
            .collection('listings')
            .where(FieldPath.documentId, whereIn: chunk)
            .get();

        for (final doc in listingsSnapshot.docs) {
          final listing = ListingModel.fromDocument(doc);
          // Only show approved listings in favorites
          if (listing.status == ListingStatus.approved) {
            results.add(listing);
          }
        }
      }

      debugPrint('[FavoritesRepository] Fetched ${results.length} favorite listings');
      return results;
    } catch (e) {
      debugPrint('[FavoritesRepository] Error fetching favorite listings: $e');
      throw AppException('Failed to load favorites: $e', originalError: e);
    }
  }
}

final favoritesRepositoryProvider = Provider<FavoritesRepository>((ref) {
  return FavoritesRepository();
});
