const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
const wsUrl = `${wsScheme}://${window.location.host}/ws/chatbot/?token=${encodeURIComponent(FIREBASE_TOKEN)}`;
const ws = new WebSocket(wsUrl);

const history = []; // in-memory, max 20 items

function send(message) {
  // Push user turn to history
  history.push({ role: "user", content: message });
  if (history.length > 20) {
    history.shift();
  }

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
      break;
    case "action_done":
      renderSuccess(data.message);
      break;
    case "ask":
      renderBotMessage(data.message);
      renderChips(data.options, sendChip);
      break;
    case "redirect":
      renderBotMessage(data.message);
      setTimeout(() => {
        window.location.href = data.url;
      }, 1200);
      break;
    default:
      console.warn("Unhandled message type received:", data.type);
  }
}
