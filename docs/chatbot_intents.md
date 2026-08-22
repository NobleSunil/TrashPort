# TrashPort Chatbot & AI Assistant Intents

The TrashPort AI Assistant uses hybrid classification (pattern + LLM) across 8 intents:

| Intent | Description | Sample Utterance | Target Action |
| :--- | :--- | :--- | :--- |
| `SCHEDULE_PICKUP` | Book a new waste collection | "I need a plastic pickup tomorrow" | Opens booking form with pre-filled category |
| `CHANGE_SCHEDULE` | Reschedule upcoming pickup | "Can I reschedule pickup #45?" | Deep-links to pickup modification view |
| `CANCEL_PICKUP` | Cancel active collection | "Cancel collection request #12" | Validates state and cancels request |
| `TRACK_COLLECTOR` | Live GPS collector tracking | "Where is my driver right now?" | Activates live map overlay |
| `FILE_COMPLAINT` | Submit a service issue | "My trash was not collected today" | Opens complaint submission form |
| `CHECK_PAYMENT` | Inspect points & subscriptions | "How many green points do I have?" | Displays points and rewards balance |
| `NAVIGATE` | UI page transition | "Take me to addresses" | Performs client-side navigation |
| `GENERAL_ANSWER` | Waste segregation FAQ | "Is styrofoam recyclable?" | Returns eco-friendly advice |
