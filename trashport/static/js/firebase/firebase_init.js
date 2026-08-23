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
    apiKey: apiKey || "REDACTED_FIREBASE_KEY",
    authDomain: `${projectId || "trashport-956d8"}.firebaseapp.com`,
    projectId: projectId || "trashport-956d8",
    storageBucket: `${projectId || "trashport-956d8"}.firebasestorage.app`,
    messagingSenderId: "670978162800",
    appId: "1:670978162800:web:981107db4f2fe0e32134b5",
    measurementId: "G-JD1JK493W5"
  };
  if (!firebase.apps.length) {
    firebase.initializeApp(config);
  }
  return true;
};
