/**
 * TrashPort Client Firebase Initializer
 */
window.TrashPortFirebase = window.TrashPortFirebase || {};

TrashPortFirebase.init = function(apiKey, projectId) {
  if (typeof firebase === "undefined") {
    console.warn("Firebase SDK script not loaded.");
    return false;
  }
  const config = {
    apiKey: apiKey || "YOUR_API_KEY",
    authDomain: `${projectId || "trashport-fcb21"}.firebaseapp.com`,
    projectId: projectId || "trashport-fcb21",
    storageBucket: `${projectId || "trashport-fcb21"}.firebasestorage.app`,
    messagingSenderId: "892775193863",
    appId: "1:892775193863:web:6954b9f49b74805824b9a2",
  };
  if (!firebase.apps.length) {
    firebase.initializeApp(config);
  }
  return true;
};
