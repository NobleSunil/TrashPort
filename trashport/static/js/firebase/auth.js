/**
 * Firebase Client Auth Methods
 */
TrashPortFirebase.signInWithGoogle = async function() {
  const provider = new firebase.auth.GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  return await firebase.auth().signInWithPopup(provider);
};

TrashPortFirebase.signInWithEmail = async function(email, password) {
  return await firebase.auth().signInWithEmailAndPassword(email, password);
};

TrashPortFirebase.createUserWithEmail = async function(email, password) {
  return await firebase.auth().createUserWithEmailAndPassword(email, password);
};

TrashPortFirebase.signOut = async function() {
  return await firebase.auth().signOut();
};
