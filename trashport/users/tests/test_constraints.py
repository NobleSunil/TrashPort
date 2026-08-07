from django.test import TestCase
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from trashport.users.forms import UserSignupForm

class ConstraintsTestCase(TestCase):
    def test_name_validation(self):
        # Invalid names
        form1 = UserSignupForm(data={"name": "John123", "role": "CITIZEN"})
        self.assertFalse(form1.is_valid())
        self.assertIn("name", form1.errors)
        self.assertEqual(form1.errors["name"][0], "Name must contain only letters and spaces.")

        form2 = UserSignupForm(data={"name": "John@Doe", "role": "CITIZEN"})
        self.assertFalse(form2.is_valid())
        self.assertIn("name", form2.errors)

    def test_password_complexity(self):
        # Missing digit
        with self.assertRaises(ValidationError) as ctx:
            validate_password("NoDigits!")
        self.assertIn("The password must contain at least 1 digit(s).", str(ctx.exception))

        # Missing uppercase
        with self.assertRaises(ValidationError) as ctx:
            validate_password("nouppercase1!")
        self.assertIn("The password must contain at least 1 uppercase letter(s).", str(ctx.exception))

        # Missing special character
        with self.assertRaises(ValidationError) as ctx:
            validate_password("NoSpecial1")
        self.assertIn("The password must contain at least 1 special character(s).", str(ctx.exception))

        # Too short
        with self.assertRaises(ValidationError) as ctx:
            validate_password("Short1!")
        self.assertIn("This password is too short.", str(ctx.exception))

        # Valid strong password
        try:
            validate_password("TrashPort123!")
        except ValidationError:
            self.fail("validate_password raised ValidationError unexpectedly!")
