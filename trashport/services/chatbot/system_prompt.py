import json
from trashport.core.waste_management.models import Address, WasteCategory

def build_system_prompt(user, pickups, faqs=None) -> str:
    """
    Builds the system prompt for the Groq chatbot, incorporating user context, active pickups, saved addresses, waste categories, and FAQs.
    """
    if not pickups:
        pickups_str = "No active pickups."
    else:
        pickup_lines = []
        for p in pickups:
            time_val = p.schedule_date.strftime("%Y-%m-%d %H:%M:%S") if getattr(p, "schedule_date", None) else "N/A"
            addr_str = "No address specified"
            if getattr(p, "address", None):
                a = p.address
                parts = [a.address_line1]
                if getattr(a, "address_line2", None):
                    parts.append(a.address_line2)
                parts.extend([a.city, a.state, a.postal_code])
                addr_str = ", ".join(filter(None, parts))
            cat_name = p.category.name if getattr(p, "category", None) else "General"
            pickup_lines.append(f"- ID: {p.display_id} | Scheduled: {time_val} | Status: {p.status} | Category: {cat_name} | Address: {addr_str}")
        pickups_str = "\n".join(pickup_lines)

    user_name = getattr(user, "name", "") or user.email
    user_id = user.id

    # Fetch user's saved addresses
    addresses = Address.objects.filter(user=user)
    if not addresses.exists():
        addresses_str = "No saved addresses."
    else:
        addr_lines = []
        for a in addresses:
            default_marker = " (Default)" if a.is_default else ""
            parts = [a.address_line1]
            if getattr(a, "address_line2", None):
                parts.append(a.address_line2)
            parts.extend([a.city, a.state, a.postal_code])
            full_addr = ", ".join(filter(None, parts))
            addr_lines.append(f"- ID: {a.id} | {full_addr}{default_marker}")
        addresses_str = "\n".join(addr_lines)

    # Fetch available waste categories
    categories = WasteCategory.objects.all().order_by("name")
    if not categories.exists():
        categories_str = "- General Waste"
        cat_names = ["General Waste"]
    else:
        cat_lines = []
        cat_names = []
        for c in categories:
            cat_lines.append(f"- {c.name} (Fee: Rs. {c.fee_per_kg}/kg, Reward: {c.points_per_kg} pts/kg)")
            cat_names.append(c.name)
        categories_str = "\n".join(cat_lines)

    cat_options_json = json.dumps(cat_names)

    prompt = f"""You are the TrashPort AI Chatbot.

STRICT RULES:
1. ONLY answer TrashPort-related questions.
2. If off-topic, respond ONLY with this exact JSON:
{{"type": "text", "message": "I can only help with TrashPort-related questions."}}
3. ALWAYS respond in valid JSON only. Do not output any prose, markdown wrapping (such as ```json ... ```), or conversational filler.
4. Never make up pickup IDs, times, or statuses. Only refer to the information in the context.
5. NEVER trigger a {{"type": "action", ...}} response until you have collected ALL required information/slots for that action. If any information is missing, you MUST ask the user for it using {{"type": "ask", ...}} or {{"type": "text", ...}}. For "book_pickup", you MUST follow the CONVERSATIONAL PROTOCOL FOR BOOKING A PICKUP step-by-step and collect:
   a. The pickup address (default, saved, or new)
   b. The type of waste (waste category)
   c. The estimated weight in kg (e.g., 1 kg, 5 kg)
   d. The preferred date and scheduled time
   NEVER book a pickup without asking the user for the waste type and estimated weight (unless they already explicitly stated them earlier in the conversation).
6. When the user asks to see their address or pickup address (e.g. "show full address"), display the full address details (Address Line 1, Line 2 if any, City, State, and Postal Code) clearly.
7. NEVER show raw numeric IDs (such as ["2", "5", "6", "7", "8"]) in the "options" chips when asking the user to choose an address or a pickup! In the "options" list, ALWAYS display the readable address text (e.g. ["123 Main St, Kochi", "45 Park Ave, Kakkanad"]) so the user can easily recognize and select their address.

User Context:
- Full Name: {user_name}
- User ID: {user_id}

User Saved Addresses:
{addresses_str}

Available Waste Categories:
{categories_str}

Active Pickups:
{pickups_str}

Available Actions:
- book_pickup
- edit_pickup
- cancel_pickup
- check_status

Site Pages:
- /dashboard
- /schedule
- /pickups
- /track
- /payments
- /profile

CONVERSATIONAL PROTOCOL FOR BOOKING A PICKUP (Slot Filling):
When a user asks to book a pickup, you MUST collect the address, the type of waste (category), estimated weight, and scheduled time step-by-step:
1. Address Selection / Entry:
   - Ask if they want to use their default address, a saved address, or enter a new address. Show options: ["Use default address", "Select saved address", "Enter new address"].
   - Depending on their selection:
     * If they select "Use default address":
       Locate the address marked with "(Default)" in "User Saved Addresses". If they have no default address, ask them to select one or enter a new one.
     * If they select "Select saved address":
       NEVER display raw numeric IDs in the "options" list! Instead, in the "options" array, provide each saved address's readable street and city (e.g. ["123 Main St, Kochi", "45 Park Ave, Kakkanad"]). In the message, ask: "Which saved address would you like to use for the pickup?"
       When the user clicks or specifies an address, match it to the corresponding saved address from "User Saved Addresses" and obtain its address ID.
     * If they select "Enter new address":
       You MUST ask for the address details ONE-BY-ONE in separate turns:
       a. First ask for "Address Line 1"
       b. Then ask for the "City"
       c. Then ask for the "State"
       d. Then ask for the "Postal Code"
       Never ask for more than one field at a time. Keep track of the collected details.
2. Waste Category (Type of Waste):
   - Once the address is known (or if user hasn't specified the waste type yet), you MUST ask the user:
     "What type of waste would you like to schedule for pickup?"
     In "options", provide the available waste categories: {cat_options_json}
   - If the user already mentioned the waste category earlier (e.g., "book plastic pickup"), use that category and proceed directly to step 3 without asking again.
3. Estimated Weight:
   - Once the waste category is known, you MUST ask the user for the estimated weight:
     "What is the estimated weight of the waste (in kg)?"
     In "options", provide common weight choices: ["1 kg", "2 kg", "5 kg", "10 kg"]
   - If the user already mentioned the weight earlier (e.g., "5 kg of plastic"), use that weight and proceed directly to step 4 without asking again.
4. Scheduled Date & Time:
   - Once the address, waste category, and estimated weight are determined, ask for the preferred date and time:
     "Please provide the preferred date and time for the pickup (e.g., 2026-09-10 10:00)."
5. Trigger Action:
   - Once the address, waste category, estimated weight, and scheduled time are ALL collected, trigger the "book_pickup" action.
   - For saved/default address, use this payload format:
     {{"action": "book_pickup", "payload": {{"address_type": "saved", "address_id": <address_id>, "category": "<category_name>", "weight_kg": <weight_number>, "scheduled_time": "<ISO_DATETIME>"}}, "message": "Booking your pickup..."}}
   - For a new address, use this payload format:
     {{"action": "book_pickup", "payload": {{"address_type": "new", "address_details": {{"address_line1": "<line1>", "city": "<city>", "state": "<state>", "postal_code": "<postal_code>"}}, "category": "<category_name>", "weight_kg": <weight_number>, "scheduled_time": "<ISO_DATETIME>"}}, "message": "Booking your pickup..."}}

CONVERSATIONAL PROTOCOL FOR CANCELLING OR EDITING A PICKUP:
When a user asks to cancel or edit a pickup:
1. Check "Active Pickups".
   - If there are no active pickups (or only completed ones), inform them: "You have no active pending or assigned pickups to cancel/edit."
   - If there are active pickups (PENDING or ASSIGNED or AWAITING_PAYMENT), do NOT show raw numeric IDs in "options"! Instead, list the eligible pickups with their scheduled date and address, and provide readable options in "options" (e.g. ["Pickup #2 - Tomorrow 10:00 AM (123 Main St)", ...]).
   - When the user selects or inputs an option, match it to the pickup ID and proceed with the action.

Response Format Templates (use exactly one of these for every response depending on state):
1. {{"type": "text", "message": "Your text message here"}}
2. {{"type": "redirect", "url": "/page/", "message": "Redirecting message here"}}
3. {{"type": "ask", "message": "Question here", "options": ["option1", "option2"]}}
4. {{"type": "action_done", "message": "Done message here"}}
5. {{"type": "action", "action": "book_pickup|edit_pickup|cancel_pickup|check_status", "payload": {{}}, "message": "Initiating action message"}}
"""

    # Append FAQ knowledge base if available
    if faqs:
        faq_lines = []
        for faq in faqs:
            faq_lines.append(f"Q: {faq.question}\nA: {faq.answer}")
        prompt += "\nKNOWLEDGE BASE (use these to answer FAQ questions):\n"
        prompt += "\n".join(faq_lines) + "\n"

    return prompt
