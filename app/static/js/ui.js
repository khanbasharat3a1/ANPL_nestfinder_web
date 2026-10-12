/**
 * NestFinder Web UI Controller
 * Theme management, Toast dismissals, and CSRF token handling.
 */

(function () {
  'use strict';

  // 1. Theme Manager
  const THEME_KEY = 'nestfinder_theme';

  function initTheme() {
    const savedTheme = localStorage.getItem(THEME_KEY);
    if (savedTheme) {
      document.documentElement.setAttribute('data-theme', savedTheme);
    }
  }

  function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    let newTheme;

    if (currentTheme) {
      newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    } else {
      newTheme = prefersDark ? 'light' : 'dark';
    }

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem(THEME_KEY, newTheme);
  }

  // 2. CSRF Token Helper
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  // 3. Global Toast / Alert Helper
  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `flash-message flash-${type}`;
    toast.innerHTML = `
      <span>${message}</span>
      <button type="button" style="background:none;border:none;cursor:pointer;font-size:1.2rem;line-height:1;color:inherit;" aria-label="Close">&times;</button>
    `;

    toast.querySelector('button').addEventListener('click', () => toast.remove());
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 5000);
  }

  // Attach global helpers to window
  window.NestFinder = window.NestFinder || {};
  window.NestFinder.toggleTheme = toggleTheme;
  window.NestFinder.getCsrfToken = getCsrfToken;
  window.NestFinder.showToast = showToast;

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener('click', toggleTheme);
    }
  });
})();
