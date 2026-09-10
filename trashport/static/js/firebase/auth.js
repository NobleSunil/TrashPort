/**
 * TrashPort Firebase Client Authentication Service
 * Provides helper functions for client-side Firebase Auth interactions.
 */

/**
 * Initiates Google OAuth 2.0 Sign-In via popup window.
 * Forces account selection prompt to let users choose their Google account.
 * @returns {Promise<firebase.auth.UserCredential>} Firebase authentication credential
 */
TrashPortFirebase.signInWithGoogle = async function() {
  const provider = new firebase.auth.GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  return await firebase.auth().signInWithPopup(provider);
};

/**
 * Authenticates an existing user with Email and Password credentials via Firebase Auth SDK.
 * @param {string} email User email address
 * @param {string} password User password
 * @returns {Promise<firebase.auth.UserCredential>} Firebase authentication credential
 */
TrashPortFirebase.signInWithEmail = async function(email, password) {
  return await firebase.auth().signInWithEmailAndPassword(email, password);
};

/**
 * Registers a new user account with Email and Password in Firebase Authentication.
 * @param {string} email User email address
 * @param {string} password User password
 * @returns {Promise<firebase.auth.UserCredential>} Firebase authentication credential
 */
TrashPortFirebase.createUserWithEmail = async function(email, password) {
  return await firebase.auth().createUserWithEmailAndPassword(email, password);
};

/**
 * Signs out the currently authenticated user from the client Firebase session.
 * @returns {Promise<void>}
 */
TrashPortFirebase.signOut = async function() {
  return await firebase.auth().signOut();
};
