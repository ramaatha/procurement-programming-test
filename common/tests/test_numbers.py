# filepath: common/tests/test_numbers.py
import importlib
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase


class NumbersTests(SimpleTestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('common.numbers'), 'Parser angka belum tersedia.')
        self.numbers = importlib.import_module('common.numbers')

    def test_TC04_quantity_and_money_keep_their_scale(self):
        n = self.numbers
        self.assertEqual(n.parse_quantity('0.333'), 333)
        self.assertEqual(n.parse_money('0.05'), 5)
        self.assertEqual(n.parse_quantity('0002.010'), 2010)
        self.assertEqual(n.format_quantity(333), '0.333')
        self.assertEqual(n.format_money(5), '0.05')
        self.assertEqual(n.parse_quantity('0', allow_zero=True), 0)

    def test_TC04_round_each_line_half_up_before_summing(self):
        n = self.numbers
        self.assertEqual(n.line_total(333, 5), 2)
        self.assertEqual(n.line_total(1, 1), 0)
        self.assertEqual(n.line_total(500, 1), 1)
        self.assertEqual(n.document_total([n.line_total(500, 1), n.line_total(500, 1)]), 2)

    def test_TC04_reject_ambiguous_or_non_string_input(self):
        for value in ['NaN', 'Infinity', '1e3', '-1', '+1', ' 1', '1 ', '1,5', '.5', '1.', '', '١', 1.5, 1, True, None, Decimal('1')]:
            for parser in [self.numbers.parse_quantity, self.numbers.parse_money]:
                with self.subTest(value=value, parser=parser.__name__), self.assertRaises(ValidationError):
                    parser(value)

    def test_TC04_reject_zero_excess_precision_and_overflow(self):
        n = self.numbers
        for parser, value in [(n.parse_quantity, '0'), (n.parse_money, '0'), (n.parse_quantity, '1.0000'), (n.parse_money, '1.001'), (n.parse_quantity, '9223372036854775.808'), (n.parse_money, '92233720368547758.08'), (n.parse_quantity, '9' * 10000)]:
            with self.subTest(value=str(value)[:40]), self.assertRaises(ValidationError):
                parser(value)
        self.assertEqual(n.parse_quantity('9223372036854775.807'), 9223372036854775807)
        self.assertEqual(n.parse_money('92233720368547758.07'), 9223372036854775807)
        with self.assertRaises(ValidationError):
            n.line_total(9223372036854775807, 1001)
        with self.assertRaises(ValidationError):
            n.document_total([9223372036854775807, 1])

    def test_TC04_internal_math_and_formatters_reject_invalid_integers(self):
        n = self.numbers
        for value in [-1, True, 0.5, 9223372036854775808]:
            for formatter in [n.format_quantity, n.format_money]:
                with self.subTest(value=value, formatter=formatter.__name__), self.assertRaises(ValidationError):
                    formatter(value)
            with self.subTest(value=value), self.assertRaises(ValidationError):
                n.document_total([value])
        for qty, price in [(0, 1), (1, 0), (1.2, 1), (1, True)]:
            with self.subTest(qty=qty, price=price), self.assertRaises(ValidationError):
                n.line_total(qty, price)
