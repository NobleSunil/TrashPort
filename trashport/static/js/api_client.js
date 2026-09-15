/**
 * TrashPort Unified API Client
 *
 * Lightweight fetch wrapper that handles:
 * - Same-origin credential forwarding (session cookies)
 * - Automatic Django CSRF token extraction from cookies
 * - JSON request/response serialization and error handling
 */
const APIClient = {
  /**
   * Perform an authenticated GET request.
   *
   * @param {string} url - Target API URL or path
   * @returns {Promise<Object>} Parsed JSON response
   * @throws {Error} If HTTP response status is not ok (2xx)
   */
  async get(url) {
    const res = await fetch(url, { credentials: "same-origin" });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  },

  /**
   * Perform an authenticated POST request with CSRF token header.
   *
   * @param {string} url - Target API URL or path
   * @param {Object} [body={}] - Request payload to be JSON-stringified
   * @returns {Promise<Object>} Parsed JSON response
   * @throws {Error} If HTTP response status is not ok (2xx)
   */
  async post(url, body = {}) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": APIClient.getCookie("csrftoken") || "",
      },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.message || errData.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  /**
   * Extract a named cookie value from document.cookie.
   * Primarily used for retrieving Django's `csrftoken`.
   *
   * @param {string} name - Name of the cookie to retrieve
   * @returns {string|null} Decoded cookie value or null if not found
   */
  getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  },
};
