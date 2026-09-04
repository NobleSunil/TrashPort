/* Project specific Javascript goes here. */

// Safe dropdown fallback handler
document.addEventListener('DOMContentLoaded', function () {
  document.addEventListener('click', function (e) {
    const toggle = e.target.closest('[data-bs-toggle="dropdown"]');
    if (toggle) {
      if (window.bootstrap && window.bootstrap.Dropdown) {
        return;
      }
      e.preventDefault();
      const parent = toggle.closest('.dropdown, .btn-group');
      if (parent) {
        const menu = parent.querySelector('.dropdown-menu');
        if (menu) {
          const isShown = menu.classList.contains('show');
          document.querySelectorAll('.dropdown-menu.show').forEach(function (m) {
            m.classList.remove('show');
          });
          if (!isShown) {
            menu.classList.add('show');
            toggle.setAttribute('aria-expanded', 'true');
          } else {
            toggle.setAttribute('aria-expanded', 'false');
          }
        }
      }
    } else if (!e.target.closest('.dropdown-menu')) {
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

