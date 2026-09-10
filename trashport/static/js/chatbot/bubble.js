/**
 * ==============================================================================
 * Chatbot Floating Bubble & Sheet Toggle Controller
 * ==============================================================================
 * Handles the opening, closing, keyboard navigation (Escape), and outside-click
 * dismissal for the floating AI assistant widget.
 */

/**
 * Expands the chat interface sheet and hides the floating launcher bubble.
 * Restores input focus with a transition delay.
 * @param {Event} [event] Optional triggering event
 */
function openChat(event) {
  if (event && typeof event.stopPropagation === "function") {
    event.stopPropagation();
  }
  const sheet = document.getElementById("chat-sheet");
  const bubble = document.getElementById("chat-bubble");
  const input = document.getElementById("chat-input");

  if (sheet) sheet.classList.add("open");
  if (bubble) bubble.style.display = "none";
  sessionStorage.setItem("trashport_chat_open", "true");
  if (input) {
    // Small delay to ensure transition completes and element is focusable
    setTimeout(() => input.focus(), 150);
  }
}

/**
 * Collapses the chat interface sheet and restores the launcher bubble.
 * @param {Event} [event] Optional triggering event
 */
function closeChat(event) {
  if (event && typeof event.stopPropagation === "function") {
    event.stopPropagation();
  }
  const sheet = document.getElementById("chat-sheet");
  const bubble = document.getElementById("chat-bubble");

  if (sheet) sheet.classList.remove("open");
  if (bubble) bubble.style.display = "flex";
  sessionStorage.removeItem("trashport_chat_open");
}


document.addEventListener("DOMContentLoaded", () => {
  // Restore open state if previously opened
  if (sessionStorage.getItem("trashport_chat_open") === "true") {
    openChat();
  }
  const sheet = document.getElementById("chat-sheet");
  if (sheet) {
    sheet.addEventListener("click", (e) => {
      e.stopPropagation();
    });
  }

  // Click outside chat sheet while open -> closeChat()
  document.addEventListener("click", (event) => {
    const sheet = document.getElementById("chat-sheet");
    const bubble = document.getElementById("chat-bubble");

    if (sheet && sheet.classList.contains("open")) {
      // Only close if click is outside both the chat sheet and the launcher bubble
      if (!sheet.contains(event.target) && !bubble.contains(event.target)) {
        closeChat();
      }
    }
  });

  // Escape key -> closeChat()
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" || event.keyCode === 27) {
      closeChat();
    }
  });
});
