from trashport.chatbot.intent import IntentClassifier, IntentType, SlotExtractor


class TestIntentClassifier:
    def test_schedule_pickup_intent(self):
        text = "I want to schedule a plastic waste pickup tomorrow"
        intent = IntentClassifier.classify(text)
        assert intent == IntentType.SCHEDULE_PICKUP

    def test_cancel_pickup_intent(self):
        text = "Please cancel pickup #45"
        intent = IntentClassifier.classify(text)
        assert intent == IntentType.CANCEL_PICKUP

    def test_check_payment_intent(self):
        text = "How many wallet points do I have?"
        intent = IntentClassifier.classify(text)
        assert intent == IntentType.CHECK_PAYMENT

    def test_slot_extractor(self):
        text = "Please collect 15kg of plastic from #88"
        slots = SlotExtractor.extract_slots(text)
        assert slots.get("pickup_id") == 88
        assert slots.get("category") == "Plastic"
