/**
 * NestFinder Firebase Client Authentication
 * Uses modular Firebase Auth v10 SDK via Google Static CDN.
 * Handles Google Popup, Email/Password sign-in, Registration, and Password Reset.
 */

import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  sendPasswordResetEmail,
  signOut as firebaseSignOut
} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';

// Initialize Firebase Client with server-injected config
const firebaseConfig = window.FIREBASE_CONFIG || {};
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

/**
 * Exchanges Firebase ID token with Flask /auth/session endpoint.
 */
async function postSessionToken(idToken, extraData = {}) {
  const csrfToken = window.NestFinder?.getCsrfToken() || '';
  const payload = { idToken, ...extraData };

  const response = await fetch('/auth/session', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || result.details || 'Session creation failed');
  }

  // Redirect to target or explore feed
  window.location.href = result.redirect || '/explore';
}

/**
 * Google Sign-In with Popup.
 * Invoked synchronously within the click event handler so iOS Safari does not block popup.
 */
export async function loginWithGoogle(nextUrl = '') {
  try {
    const userCredential = await signInWithPopup(auth, googleProvider);
    const user = userCredential.user;
    const idToken = await user.getIdToken();

    await postSessionToken(idToken, {
      name: user.displayName,
      next: nextUrl,
    });
  } catch (error) {
    console.error('Google Sign-In failed:', error);
    if (error.code === 'auth/popup-closed-by-user') {
      window.NestFinder?.showToast('Sign-in popup was closed.', 'info');
    } else {
      window.NestFinder?.showToast(error.message || 'Google sign-in failed.', 'error');
    }
  }
}

/**
 * Sign in with Email and Password.
 */
export async function loginWithEmail(email, password, nextUrl = '') {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email.trim(), password);
    const user = userCredential.user;
    const idToken = await user.getIdToken();

    await postSessionToken(idToken, {
      name: user.displayName,
      next: nextUrl,
    });
  } catch (error) {
    console.error('Email sign-in failed:', error);
    let msg = 'Failed to sign in. Please verify your email and password.';
    if (error.code === 'auth/user-not-found' || error.code === 'auth/wrong-password' || error.code === 'auth/invalid-credential') {
      msg = 'Invalid email or password.';
    } else if (error.code === 'auth/too-many-requests') {
      msg = 'Too many attempts. Please try again later.';
    }
    window.NestFinder?.showToast(msg, 'error');
  }
}

/**
 * Register a new user with Email and Password.
 */
export async function registerWithEmail(name, email, password, phone = '') {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email.trim(), password);
    const user = userCredential.user;

    // Update display name in Firebase Auth
    if (name) {
      await updateProfile(user, { displayName: name.trim() });
    }

    const idToken = await user.getIdToken();

    await postSessionToken(idToken, {
      name: name.trim(),
      phone: phone.trim(),
      next: '/explore',
    });
  } catch (error) {
    console.error('Registration failed:', error);
    let msg = 'Registration failed. Please check your information.';
    if (error.code === 'auth/email-already-in-use') {
      msg = 'An account with this email already exists.';
    } else if (error.code === 'auth/weak-password') {
      msg = 'Password should be at least 6 characters.';
    }
    window.NestFinder?.showToast(msg, 'error');
  }
}

/**
 * Send password reset email.
 */
export async function requestPasswordReset(email) {
  try {
    await sendPasswordResetEmail(auth, email.trim());
    window.NestFinder?.showToast('Password reset link sent to your email.', 'success');
  } catch (error) {
    console.error('Password reset failed:', error);
    window.NestFinder?.showToast(error.message || 'Failed to send reset link.', 'error');
  }
}

// Expose on global window object for inline form bindings
window.NestFinderAuth = {
  loginWithGoogle,
  loginWithEmail,
  registerWithEmail,
  requestPasswordReset,
};
