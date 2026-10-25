from django.test import SimpleTestCase
from procurement.templatetags.procurement_numbers import quantity_id, money_id
from common.numbers import format_quantity, format_quantity_display, MAX_INT64
from django.core.exceptions import ValidationError


class QuantityDisplayTests(SimpleTestCase):
    def test_integer_zero_fraction_and_thousands_are_unambiguous(self):
        for value, expected in ((0, '0'), (4000, '4'), (10000, '10'),
                                (333, '0,333'), (1500, '1,5'), (2010, '2,01'),
                                (1000000, '1.000'), (1234567, '1.234,567'),
                                (MAX_INT64, '9.223.372.036.854.775,807')):
            with self.subTest(value=value):
                self.assertEqual(quantity_id(value), expected)

    def test_money_and_canonical_input_keep_their_precision(self):
        self.assertEqual(money_id(90000000), '900.000,00')
        self.assertEqual(format_quantity(4000), '4.000')

    def test_historical_rejections_above_single_line_limit_still_display(self):
        self.assertEqual(format_quantity_display(MAX_INT64 * 2), '18.446.744.073.709.551,614')

    def test_display_rejects_non_integer_and_negative_values(self):
        for value in (-1, True, 1.5, '4000', None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                format_quantity_display(value)
