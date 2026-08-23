function openChat() {
  const sheet = document.getElementById("chat-sheet");
  const bubble = document.getElementById("chat-bubble");
  const input = document.getElementById("chat-input");

  if (sheet) sheet.classList.add("open");
  if (bubble) bubble.style.display = "none";
  if (input) {
    // Small delay to ensure transition completes and element is focusable
    setTimeout(() => input.focus(), 150);
  }
}

function closeChat() {
  const sheet = document.getElementById("chat-sheet");
  const bubble = document.getElementById("chat-bubble");

  if (sheet) sheet.classList.remove("open");
  if (bubble) bubble.style.display = "flex";
}

document.addEventListener("DOMContentLoaded", () => {
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
