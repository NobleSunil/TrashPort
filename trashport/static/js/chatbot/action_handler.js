/**
 * Chatbot Action Dispatcher
 */
function handleChatbotAction(actionData) {
  if (!actionData) return;
  if (actionData.action === "NAVIGATE" && actionData.url) {
    window.location.href = actionData.url;
  }
}
