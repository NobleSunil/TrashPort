/**
 * TrashPort Global Project JavaScript
 *
 * Provides resilient client-side interactivity, progressive enhancement,
 * and polyfills for Bootstrap UI components across citizen and collector portals.
 */

document.addEventListener('DOMContentLoaded', function () {
  /**
   * Safe Dropdown Fallback Handler
   *
   * Ensures navbar and action dropdowns function reliably even if Bootstrap JS
   * fails to load or execute. Automatically handles click-outside dismissal
   * and ARIA accessibility attributes.
   */
  document.addEventListener('click', function (e) {
    const toggle = e.target.closest('[data-bs-toggle="dropdown"]');

    if (toggle) {
      // Defer to native Bootstrap dropdown instance if initialized
      if (window.bootstrap && window.bootstrap.Dropdown) {
        return;
      }

      e.preventDefault();
      const parent = toggle.closest('.dropdown, .btn-group');

      if (parent) {
        const menu = parent.querySelector('.dropdown-menu');
        if (menu) {
          const isShown = menu.classList.contains('show');

          // Close any other open dropdown menus
          document.querySelectorAll('.dropdown-menu.show').forEach(function (m) {
            m.classList.remove('show');
          });

          // Toggle current dropdown menu visibility
          if (!isShown) {
            menu.classList.add('show');
            toggle.setAttribute('aria-expanded', 'true');
          } else {
            toggle.setAttribute('aria-expanded', 'false');
          }
        }
      }
    } else if (!e.target.closest('.dropdown-menu')) {
      // Clicked outside any active dropdown — close all open menus
      document.querySelectorAll('.dropdown-menu.show').forEach(function (m) {
        m.classList.remove('show');
        const p = m.closest('.dropdown, .btn-group');
        if (p) {
          const t = p.querySelector('[data-bs-toggle="dropdown"]');
          if (t) t.setAttribute('aria-expanded', 'false');
        }
      });
    }
  });
});
