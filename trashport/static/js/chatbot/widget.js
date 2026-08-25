const sessionKey = crypto.randomUUID();
const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
const wsUrl = `${wsScheme}://${window.location.host}/ws/chatbot/?token=${encodeURIComponent(FIREBASE_TOKEN)}`;
const ws = new WebSocket(wsUrl);

const history = []; // in-memory, max 20 items
let lastUserMessage = "";

function getCookie(name) {
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
}

function send(message) {
  // Push user turn to history
  history.push({ role: "user", content: message });
  if (history.length > 20) {
    history.shift();
  }

  // Track the last user message for feedback
  lastUserMessage = message;

  // Clear chat input
  const input = document.getElementById("chat-input");
  if (input) input.value = "";

  renderUserMessage(message);

  // Hide initial prompt chips on first interaction
  const chips = document.getElementById("chat-chips");
  if (chips) chips.style.display = "none";

  ws.send(JSON.stringify({ message, history }));
}

function sendMessage() {
  const input = document.getElementById("chat-input");
  if (!input) return;
  const value = input.value.trim();
  if (value === "") return;
  send(value);
}

function sendChip(message) {
  send(message);
}

ws.onmessage = (event) => {
  try {
    const data = JSON.parse(event.data);

    if (data.message) {
      history.push({ role: "assistant", content: data.message });
      if (history.length > 20) {
        history.shift();
      }
    }

    handleResponse(data);
  } catch (e) {
    console.error("Error parsing message payload:", e);
  }
};

ws.onerror = (error) => {
  console.error("WebSocket connection error:", error);
  renderBotMessage("Connection error. Please refresh.");
};

ws.onclose = () => {
  console.warn("WebSocket connection closed.");
};

// Listen for enter key press on input field
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("chat-input");
  if (input) {
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        sendMessage();
      }
    });
  }
});

function renderUserMessage(text) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble user";
  bubble.innerText = text;
  container.appendChild(bubble);

  scrollToBottom();
}

function renderBotMessage(text) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble bot";
  bubble.innerText = text;
  container.appendChild(bubble);

  scrollToBottom();
}

function renderChips(options, onSelect) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const chipRow = document.createElement("div");
  chipRow.className = "chip-row";

  options.forEach((option) => {
    const button = document.createElement("button");
    button.className = "chip";
    button.innerText = option;
    button.onclick = () => {
      onSelect(option);
      chipRow.remove();
    };
    chipRow.appendChild(button);
  });

  container.appendChild(chipRow);
  scrollToBottom();
}

function renderSuccess(text) {
  renderBotMessage("✓ " + text);
}

function renderFeedback(botMessage, userMessage) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const feedbackRow = document.createElement("div");
  feedbackRow.className = "feedback-row";

  const thumbsUp = document.createElement("button");
  thumbsUp.innerText = "👍";
  thumbsUp.title = "Helpful";
  thumbsUp.onclick = () => submitFeedback(feedbackRow, botMessage, userMessage, "thumbs_up");

  const thumbsDown = document.createElement("button");
  thumbsDown.innerText = "👎";
  thumbsDown.title = "Not helpful";
  thumbsDown.onclick = () => submitFeedback(feedbackRow, botMessage, userMessage, "thumbs_down");

  feedbackRow.appendChild(thumbsUp);
  feedbackRow.appendChild(thumbsDown);
  container.appendChild(feedbackRow);

  scrollToBottom();
}

function submitFeedback(feedbackRow, botMessage, userMessage, rating) {
  fetch("/api/chatbot/feedback/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({
      user_message: userMessage,
      bot_message: botMessage,
      rating: rating,
      session_key: sessionKey,
    }),
  })
    .then((response) => {
      if (response.ok) {
        feedbackRow.innerHTML = "";
        const thanks = document.createElement("span");
        thanks.className = "feedback-thanks";
        thanks.innerText = "Thanks!";
        feedbackRow.appendChild(thanks);
      }
    })
    .catch(() => {
      // Silently ignore errors
    });
}

function scrollToBottom() {
  const container = document.getElementById("chat-messages");
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

function handleResponse(data) {
  switch (data.type) {
    case "text":
      renderBotMessage(data.message);
      renderFeedback(data.message, lastUserMessage);
      break;
    case "action_done":
      renderSuccess(data.message);
      renderFeedback(data.message, lastUserMessage);
      break;
    case "ask":
      renderBotMessage(data.message);
      renderFeedback(data.message, lastUserMessage);
      renderChips(data.options, sendChip);
      break;
    case "redirect":
      renderBotMessage(data.message);
      renderFeedback(data.message, lastUserMessage);
      setTimeout(() => {
        window.location.href = data.url;
      }, 1200);
      break;
    default:
      console.warn("Unhandled message type received:", data.type);
  }
}
