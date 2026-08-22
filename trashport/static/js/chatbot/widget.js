/**
 * TrashPort AI Chatbot Interactive Floating Widget
 */
(function() {
  const chatWidget = document.getElementById("trashport-chat-widget");
  if (!chatWidget) return;

  const chatToggle = document.getElementById("chat-toggle-btn");
  const chatWindow = document.getElementById("chat-window");
  const chatForm = document.getElementById("chat-input-form");
  const chatInput = document.getElementById("chat-message-input");
  const messagesContainer = document.getElementById("chat-messages-list");

  let sessionKey = localStorage.getItem("trashport_chat_session") || null;

  if (chatToggle && chatWindow) {
    chatToggle.addEventListener("click", () => {
      chatWindow.classList.toggle("hidden");
    });
  }

  function appendMessage(sender, text, actionData = null) {
    const isBot = sender === "BOT";
    const msgDiv = document.createElement("div");
    msgDiv.className = `flex mb-3 ${isBot ? "justify-start" : "justify-end"}`;

    let actionBtnHtml = "";
    if (actionData && actionData.action === "NAVIGATE" && actionData.url) {
      actionBtnHtml = `<a href="${actionData.url}" class="mt-2 inline-block px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg shadow">${actionData.button_text || "Open"}</a>`;
    }

    msgDiv.innerHTML = `
      <div class="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${isBot ? "bg-gray-100 text-gray-800 rounded-tl-sm" : "bg-brand-600 text-white rounded-tr-sm"} shadow-sm">
        <p>${text}</p>
        ${actionBtnHtml}
      </div>
    `;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  if (chatForm && chatInput) {
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const message = chatInput.value.trim();
      if (!message) return;

      appendMessage("USER", message);
      chatInput.value = "";

      try {
        const response = await fetch("/api/chatbot/message/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: message, session_key: sessionKey })
        });
        const data = await response.json();
        if (data.session_key) {
          sessionKey = data.session_key;
          localStorage.setItem("trashport_chat_session", sessionKey);
        }
        appendMessage("BOT", data.reply, data.action_data);
      } catch (err) {
        appendMessage("BOT", "Sorry, I'm having trouble connecting right now. Please try again.");
      }
    });
  }
})();
