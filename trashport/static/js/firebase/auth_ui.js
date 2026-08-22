/**
 * Firebase Auth UI Helpers
 */
TrashPortFirebase.showAuthError = function(elementId, message) {
  const el = document.getElementById(elementId);
  if (el) {
    el.textContent = message;
    el.classList.remove("hidden");
  }
};

TrashPortFirebase.hideAuthError = function(elementId) {
  const el = document.getElementById(elementId);
  if (el) {
    el.classList.add("hidden");
  }
};
