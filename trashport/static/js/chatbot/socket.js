/**
 * Chatbot WebSocket Manager
 */
function initChatSocket(sessionKey, onMessageReceived) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socketUrl = `${protocol}//${window.location.host}/ws/chat/${sessionKey}/`;
  try {
    const socket = new WebSocket(socketUrl);
    socket.onmessage = function(e) {
      const data = JSON.parse(e.data);
      if (typeof onMessageReceived === "function") {
        onMessageReceived(data);
      }
    };
    return socket;
  } catch (e) {
    console.warn("WebSocket connection unavailable, falling back to HTTP API.", e);
    return null;
  }
}
