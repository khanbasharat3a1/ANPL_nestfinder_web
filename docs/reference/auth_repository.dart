import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:rxdart/rxdart.dart';
import '../../../core/enums/user_role.dart';
import '../../../core/errors/app_exception.dart';
import '../models/user_model.dart';

/// Repository handling authentication flows and Firestore user profile synchronization.
class AuthRepository {
  final FirebaseAuth _firebaseAuth;
  final FirebaseFirestore _firestore;
  final GoogleSignIn _googleSignIn;

  AuthRepository({
    FirebaseAuth? firebaseAuth,
    FirebaseFirestore? firestore,
    GoogleSignIn? googleSignIn,
  })  : _firebaseAuth = firebaseAuth ?? FirebaseAuth.instance,
        _firestore = firestore ?? FirebaseFirestore.instance,
        _googleSignIn = googleSignIn ?? GoogleSignIn();

  /// Stream of Firebase Auth user state
  Stream<User?> get authStateChanges => _firebaseAuth.authStateChanges();

  /// Current authenticated Firebase user
  User? get currentFirebaseUser => _firebaseAuth.currentUser;

  /// Real-time stream of the current user's profile from Firestore `users/{uid}`.
  /// Uses RxDart switchMap so the Firestore listener is cancelled the moment
  /// auth state changes or becomes null.
  Stream<UserModel?> watchCurrentUser() {
    return _firebaseAuth.authStateChanges().switchMap<UserModel?>((firebaseUser) {
      debugPrint('[Auth] Auth state changed: uid=${firebaseUser?.uid}');
      if (firebaseUser == null) {
        return Stream<UserModel?>.value(null);
      }

      // Safe Firestore listener with auto-resubscription and error handling
      return Rx.retryWhen<DocumentSnapshot<Map<String, dynamic>>>(
        () => _firestore.collection('users').doc(firebaseUser.uid).snapshots(),
        (error, stackTrace) {
          debugPrint('[Auth] Firestore user listener error: $error. Resubscribing in 2s...');
          return Rx.timer(null, const Duration(seconds: 2));
        },
      )
      .where((snapshot) {
        debugPrint('[Auth] User doc snapshot: uid=${firebaseUser.uid}, exists=${snapshot.exists}');
        // While the doc does not exist yet, the stream must stay in loading, not emit an error or a null user.
        if (!snapshot.exists || snapshot.data() == null) {
          _syncOrCreateUserDocument(firebaseUser);
          return false;
        }
        return true;
      })
      .map<UserModel?>((snapshot) {
        return UserModel.fromDocument(snapshot);
      })
      .handleError((error, stackTrace) {
        debugPrint('[Auth] Firestore stream handled error safely: $error');
      });
    });
  }

  /// Sign in with Email and Password
  Future<UserModel> signInWithEmailAndPassword({
    required String email,
    required String password,
  }) async {
    try {
      final credential = await _firebaseAuth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      final user = credential.user;
      if (user == null) throw const AppException('Sign in failed. Please try again.');

      return await _syncOrCreateUserDocument(user);
    } on FirebaseAuthException catch (e) {
      debugPrint('[AuthRepository] FirebaseAuthException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } on PlatformException catch (e) {
      debugPrint('[AuthRepository] PlatformException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } catch (e) {
      debugPrint('[AuthRepository] Unexpected sign-in error: $e');
      if (e is AppException) rethrow;
      throw AppException(e.toString(), originalError: e);
    }
  }

  /// Register a new account with Email and Password
  Future<UserModel> signUpWithEmailAndPassword({
    required String email,
    required String password,
    required String name,
    String? phone,
  }) async {
    try {
      final credential = await _firebaseAuth.createUserWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      final user = credential.user;
      if (user == null) throw const AppException('Registration failed. Please try again.');

      await user.updateDisplayName(name.trim());

      final userModel = UserModel(
        uid: user.uid,
        name: name.trim(),
        email: user.email ?? email.trim(),
        phone: phone?.trim(),
        photoUrl: user.photoURL,
        role: UserRole.user,
        isBanned: false,
        createdAt: DateTime.now(),
      );

      debugPrint('[Auth] Creating user doc on sign up for uid=${user.uid}');
      await _firestore.collection('users').doc(user.uid).set(userModel.toMap(), SetOptions(merge: true));
      debugPrint('[Auth] Successfully created user doc on sign up for uid=${user.uid}');
      return userModel;
    } on FirebaseAuthException catch (e) {
      debugPrint('[AuthRepository] FirebaseAuthException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } on PlatformException catch (e) {
      debugPrint('[AuthRepository] PlatformException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } catch (e) {
      debugPrint('[AuthRepository] Unexpected sign-up error: $e');
      if (e is AppException) rethrow;
      throw AppException(e.toString(), originalError: e);
    }
  }

  /// Sign in with Google (OAuth)
  Future<UserModel> signInWithGoogle() async {
    try {
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) {
        throw const AppException('Google sign-in was cancelled.', code: 'sign_in_canceled');
      }

      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
      final OAuthCredential credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final userCredential = await _firebaseAuth.signInWithCredential(credential);
      final user = userCredential.user;
      if (user == null) {
        throw const AppException('Failed to sign in with Google credential.', code: 'sign_in_failed');
      }

      return await _syncOrCreateUserDocument(
        user,
        fallbackName: googleUser.displayName,
        fallbackPhotoUrl: googleUser.photoUrl,
      );
    } on FirebaseAuthException catch (e) {
      debugPrint('[AuthRepository] FirebaseAuthException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } on PlatformException catch (e) {
      debugPrint('[AuthRepository] PlatformException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } catch (e) {
      debugPrint('[AuthRepository] Unexpected Google sign-in error: $e');
      if (e is AppException) rethrow;
      throw AppException(e.toString(), originalError: e);
    }
  }

  /// Send password reset link to user's email
  Future<void> sendPasswordResetEmail(String email) async {
    try {
      await _firebaseAuth.sendPasswordResetEmail(email: email.trim());
    } on FirebaseAuthException catch (e) {
      debugPrint('[AuthRepository] FirebaseAuthException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } on PlatformException catch (e) {
      debugPrint('[AuthRepository] PlatformException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } catch (e) {
      debugPrint('[AuthRepository] Unexpected password reset error: $e');
      if (e is AppException) rethrow;
      throw AppException(e.toString(), originalError: e);
    }
  }

  /// Update user profile details (name, phone, photoUrl)
  Future<void> updateProfile({
    required String uid,
    String? name,
    String? phone,
    String? photoUrl,
  }) async {
    try {
      final updates = <String, dynamic>{};
      if (name != null) {
        updates['name'] = name.trim();
        updates['nameLower'] = name.trim().toLowerCase();
      }
      if (phone != null) updates['phone'] = phone.trim();
      if (photoUrl != null) updates['photoUrl'] = photoUrl;

      if (updates.isNotEmpty) {
        await _firestore.collection('users').doc(uid).update(updates);
      }
    } on FirebaseAuthException catch (e) {
      debugPrint('[AuthRepository] FirebaseAuthException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } on PlatformException catch (e) {
      debugPrint('[AuthRepository] PlatformException [${e.code}]: ${e.message}');
      throw AppException(
        AppException.formatErrorMessage(e.code, e.message),
        code: e.code,
        originalError: e,
      );
    } catch (e) {
      if (e is AppException) rethrow;
      throw AppException(e.toString(), originalError: e);
    }
  }

  /// Sign out from Firebase and Google Sign-In
  Future<void> signOut() async {
    try {
      await Future.wait([
        _firebaseAuth.signOut(),
        _googleSignIn.signOut(),
      ]);
    } catch (e) {
      throw AppException('Error signing out: $e');
    }
  }

  /// Ensures a Firestore document exists in `users/{uid}`.
  Future<UserModel> _syncOrCreateUserDocument(
    User user, {
    String? fallbackName,
    String? fallbackPhotoUrl,
  }) async {
    final docRef = _firestore.collection('users').doc(user.uid);
    try {
      final snapshot = await docRef.get();

      if (snapshot.exists && snapshot.data() != null) {
        debugPrint('[Auth] Found existing user doc in Firestore for uid=${user.uid}');
        return UserModel.fromDocument(snapshot);
      }

      debugPrint('[Auth] Creating new user doc in Firestore for uid=${user.uid}');
      // First time sign-in: create user profile
      final newUser = UserModel(
        uid: user.uid,
        name: user.displayName ?? fallbackName ?? 'Employee',
        email: user.email ?? '',
        phone: user.phoneNumber,
        photoUrl: user.photoURL ?? fallbackPhotoUrl,
        role: UserRole.user,
        isBanned: false,
        createdAt: DateTime.now(),
      );

      await docRef.set(newUser.toMap(), SetOptions(merge: true));
      debugPrint('[Auth] Successfully created user doc in Firestore for uid=${user.uid}');
      return newUser;
    } catch (e) {
      debugPrint('[Auth] Error syncing or creating user doc for uid=${user.uid}: $e');
      rethrow;
    }
  }
}
