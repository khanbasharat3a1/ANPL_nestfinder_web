import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/errors/app_exception.dart';
import '../models/notification_model.dart';

class NotificationsRepository {
  final FirebaseFirestore _firestore;

  NotificationsRepository([FirebaseFirestore? firestore])
      : _firestore = firestore ?? FirebaseFirestore.instance;

  CollectionReference<Map<String, dynamic>> _notificationsRef(String userId) =>
      _firestore.collection('users').doc(userId).collection('notifications');

  /// Real-time stream of all notifications for a user, newest first
  Stream<List<NotificationModel>> watchNotifications(String userId) {
    if (userId.isEmpty) return Stream.value([]);
    return _notificationsRef(userId)
        .orderBy('createdAt', descending: true)
        .snapshots()
        .map((snapshot) {
          return snapshot.docs.map((doc) => NotificationModel.fromDocument(doc)).toList();
        })
        .handleError((error) {
          debugPrint('[NotificationsRepository] Error watching notifications: $error');
          return <NotificationModel>[];
        });
  }

  /// Real-time stream of unread notification count
  Stream<int> watchUnreadCount(String userId) {
    if (userId.isEmpty) return Stream.value(0);
    return _notificationsRef(userId)
        .where('read', isEqualTo: false)
        .snapshots()
        .map((snapshot) => snapshot.docs.length)
        .handleError((error) {
          debugPrint('[NotificationsRepository] Error watching unread count: $error');
          return 0;
        });
  }

  /// Mark a single notification as read
  Future<void> markAsRead({required String userId, required String notificationId}) async {
    try {
      await _notificationsRef(userId).doc(notificationId).update({'read': true});
    } catch (e) {
      debugPrint('[NotificationsRepository] Error marking notification as read: $e');
      throw AppException('Failed to update notification', originalError: e);
    }
  }

  /// Mark all notifications as read using a batch
  Future<void> markAllAsRead(String userId) async {
    try {
      final unreadDocs = await _notificationsRef(userId)
          .where('read', isEqualTo: false)
          .get();

      if (unreadDocs.docs.isEmpty) return;

      final batch = _firestore.batch();
      for (final doc in unreadDocs.docs) {
        batch.update(doc.reference, {'read': true});
      }
      await batch.commit();
    } catch (e) {
      debugPrint('[NotificationsRepository] Error marking all notifications as read: $e');
      throw AppException('Failed to mark all as read', originalError: e);
    }
  }
}

final notificationsRepositoryProvider = Provider<NotificationsRepository>((ref) {
  return NotificationsRepository();
});
