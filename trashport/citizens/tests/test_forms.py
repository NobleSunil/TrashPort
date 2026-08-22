import pytest
from trashport.citizens.forms import AddressForm


def test_address_form_valid():
    form = AddressForm(data={
        "address_line1": "123 Eco Way",
        "address_line2": "Apt 4B",
        "city": "Metropolis",
        "state": "NY",
        "postal_code": "10001",
        "is_default": True,
    })
    assert form.is_valid()
