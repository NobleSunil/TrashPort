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
    apiKey: apiKey || "AIzaSyYourFirebaseWebApiKeyHere",
    authDomain: `${projectId || "trashport-project"}.firebaseapp.com`,
    projectId: projectId || "trashport-project",
    storageBucket: `${projectId || "trashport-project"}.firebasestorage.app`,
    messagingSenderId: "123456789012",
    appId: "1:123456789012:web:abcdef1234567890",
    measurementId: "G-XXXXXXXXXX"
  };
  if (!firebase.apps.length) {
    firebase.initializeApp(config);
  }
  return true;
};
