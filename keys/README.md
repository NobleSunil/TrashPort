# Firebase Service Account Credentials

This directory / root path is used for storing your local Firebase Admin SDK service account key.

## Setup Instructions for Developers:

1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Open **Project Settings** (gear icon) > **Service accounts** tab.
3. Click **Generate new private key** and download the `.json` file.
4. Copy `serviceAccountKey.example.json` to `serviceAccountKey.json` in the project root (or inside this `keys/` directory):
   ```bash
   cp serviceAccountKey.example.json serviceAccountKey.json
   ```
5. Open `serviceAccountKey.json` and paste your downloaded Firebase private key credentials into it.
6. Verify your `.envs/.local/.django` file has:
   ```env
   DJANGO_FIREBASE_CREDENTIALS=serviceAccountKey.json
   ```

> **Note:** `serviceAccountKey.json` and all `.json` keys in this folder (except `*.example.json`) are strictly gitignored to keep credentials secure. Never commit real private keys to git.
