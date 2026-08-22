/**
 * Firebase ID Token Auto Refresh Listener
 */
TrashPortFirebase.listenTokenRefresh = function(onTokenChanged) {
  if (typeof firebase !== "undefined" && firebase.auth) {
    firebase.auth().onIdTokenChanged(async function(user) {
      if (user) {
        const token = await user.getIdToken();
        if (typeof onTokenChanged === "function") {
          onTokenChanged(token);
        }
      }
    });
  }
};
