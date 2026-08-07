import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class ComplexityValidator:
    def __init__(self, min_digits=1, min_uppercase=1, min_special=1):
        self.min_digits = min_digits
        self.min_uppercase = min_uppercase
        self.min_special = min_special

    def validate(self, password, user=None):
        if len(re.findall(r'[0-9]', password)) < self.min_digits:
            raise ValidationError(
                _("The password must contain at least %(min_digits)d digit(s)."),
                code='password_no_digits',
                params={'min_digits': self.min_digits},
            )
        if len(re.findall(r'[A-Z]', password)) < self.min_uppercase:
            raise ValidationError(
                _("The password must contain at least %(min_uppercase)d uppercase letter(s)."),
                code='password_no_uppercase',
                params={'min_uppercase': self.min_uppercase},
            )
        if len(re.findall(r'[^A-Za-z0-9]', password)) < self.min_special:
            raise ValidationError(
                _("The password must contain at least %(min_special)d special character(s)."),
                code='password_no_special',
                params={'min_special': self.min_special},
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least %(min_digits)d digit(s), "
            "%(min_uppercase)d uppercase letter(s), and %(min_special)d special character(s)."
        ) % {
            'min_digits': self.min_digits,
            'min_uppercase': self.min_uppercase,
            'min_special': self.min_special,
        }
