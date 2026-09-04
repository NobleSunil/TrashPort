const sessionKey = crypto.randomUUID();
const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
const wsUrl = `${wsScheme}://${window.location.host}/ws/chatbot/?token=${encodeURIComponent(typeof FIREBASE_TOKEN !== "undefined" ? FIREBASE_TOKEN : "")}`;

let ws = null;
let reconnectTimeout = null;
let messageQueue = [];

const history = []; // in-memory, max 20 items
let lastUserMessage = "";
let greetingRendered = false;

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

function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("Chatbot WebSocket connected.");
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }
      // Flush any queued messages
      while (messageQueue.length > 0 && ws.readyState === WebSocket.OPEN) {
        const payload = messageQueue.shift();
        ws.send(payload);
      }
    };

    ws.onmessage = (event) => {
      removeThinkingIndicator();
      try {
        const data = JSON.parse(event.data);

        if (data.message && data.type !== "greeting") {
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
      removeThinkingIndicator();
    };

    ws.onclose = () => {
      console.warn("WebSocket connection closed. Attempting reconnect...");
      removeThinkingIndicator();
      if (!reconnectTimeout) {
        reconnectTimeout = setTimeout(() => {
          reconnectTimeout = null;
          connectWebSocket();
        }, 2000);
      }
    };
  } catch (err) {
    console.error("Error initializing WebSocket:", err);
    if (!reconnectTimeout) {
      reconnectTimeout = setTimeout(() => {
        reconnectTimeout = null;
        connectWebSocket();
      }, 3000);
    }
  }
}

// Initialize connection
connectWebSocket();

function renderThinkingIndicator() {
  removeThinkingIndicator();
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.id = "chat-thinking-indicator";
  bubble.className = "msg-bubble bot thinking-bubble";
  bubble.innerHTML = `<span>Thinking</span><div class="thinking-dots"><span></span><span></span><span></span></div>`;
  container.appendChild(bubble);

  scrollToBottom();
}

function removeThinkingIndicator() {
  const indicator = document.getElementById("chat-thinking-indicator");
  if (indicator) {
    indicator.remove();
  }
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
  renderThinkingIndicator();

  // Hide initial prompt chips on first interaction
  const chips = document.getElementById("chat-chips");
  if (chips) chips.style.display = "none";

  const payload = JSON.stringify({ message, history });

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(payload);
  } else {
    messageQueue.push(payload);
    connectWebSocket();
  }
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

function saveChatToSession() {
  const container = document.getElementById("chat-messages");
  if (container) {
    sessionStorage.setItem("trashport_chat_html", container.innerHTML);
    sessionStorage.setItem("trashport_chat_history", JSON.stringify(history));
  }
}

// Listen for enter key press on input field and restore chat state
document.addEventListener("DOMContentLoaded", () => {
  const savedHtml = sessionStorage.getItem("trashport_chat_html");
  const savedHistory = sessionStorage.getItem("trashport_chat_history");
  if (savedHtml) {
    const container = document.getElementById("chat-messages");
    if (container && container.innerHTML.trim() === "") {
      container.innerHTML = savedHtml;
      greetingRendered = true;
      scrollToBottom();
    }
  }
  if (savedHistory) {
    try {
      const parsed = JSON.parse(savedHistory);
      if (Array.isArray(parsed) && history.length === 0) {
        history.push(...parsed);
      }
    } catch (e) {}
  }

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
    button.onclick = (e) => {
      if (e && typeof e.stopPropagation === "function") {
        e.stopPropagation();
      }
      onSelect(option);
      chipRow.remove();
    };
    chipRow.appendChild(button);
  });

  container.appendChild(chipRow);
  scrollToBottom();
}

function renderSuccess(text) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble bot success-msg";
  bubble.innerText = "✓ " + text;
  container.appendChild(bubble);

  scrollToBottom();
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
    case "greeting":
      if (!greetingRendered) {
        renderBotMessage(data.message);
        greetingRendered = true;
      }
      break;
    case "text":
      // Deduplicate if greeting was sent as standard text or on reconnect
      if (data.message && data.message.startsWith("Hi ") && data.message.includes("How can I help you today?")) {
        if (!greetingRendered) {
          renderBotMessage(data.message);
          greetingRendered = true;
        }
        break;
      }
      renderBotMessage(data.message);
      if (lastUserMessage) {
        renderFeedback(data.message, lastUserMessage);
      }
      break;
    case "action_done":
      renderSuccess(data.message);
      if (lastUserMessage) {
        renderFeedback(data.message, lastUserMessage);
      }
      saveChatToSession();
      // If user is on dashboard, reload page after a moment so the newly added pickup appears immediately!
      if (window.location.pathname.includes("dashboard") || window.location.pathname === "/") {
        setTimeout(() => {
          saveChatToSession();
          window.location.reload();
        }, 1200);
      }
      break;
    case "ask":
      renderBotMessage(data.message);
      if (lastUserMessage) {
        renderFeedback(data.message, lastUserMessage);
      }
      if (Array.isArray(data.options)) {
        renderChips(data.options, sendChip);
      }
      break;
    case "redirect":
      renderBotMessage(data.message);
      if (lastUserMessage) {
        renderFeedback(data.message, lastUserMessage);
      }
      setTimeout(() => {
        window.location.href = data.url;
      }, 1200);
      break;
    default:
      console.warn("Unhandled message type received:", data.type);
  }
}
