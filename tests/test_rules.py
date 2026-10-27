"""Pattern rules: good and bad examples for every rule, OCR swaps, and the 'can the rules judge this' check."""
import unittest

from picture_guard import rules
from picture_guard.ocr import Word


def lines_of(*texts):
    out = []
    for li, t in enumerate(texts):
        out.append([Word(tok, 95.0, (i * 10, li * 20, i * 10 + 9, li * 20 + 12), (1, 1, li)) for i, tok in enumerate(t.split())])
    return out


def types(*texts):
    found, _ = rules.find_values(lines_of(*texts))
    return sorted(f.type for f in found)


class Checks(unittest.TestCase):
    def test_luhn(self):
        for good in ("4242424242424242", "378282246310005", "4012888888881881", "6011111111111117"):
            self.assertTrue(rules.luhn_ok(good), good)
        for bad in ("4242424242424241", "378282246310006", "1234567890123456", "424242424242", "4242 4242 4242 4242"):
            self.assertFalse(rules.luhn_ok(bad), bad)

    def test_iban_mod97(self):
        self.assertTrue(rules.iban_ok("GB82WEST12345698765432"))
        self.assertTrue(rules.iban_ok("gb82 west 1234 5698 7654 32".replace(" ", "")))
        self.assertFalse(rules.iban_ok("GB83WEST12345698765432"))
        self.assertFalse(rules.iban_ok("GB82WEST1234569876543"))
        self.assertFalse(rules.iban_ok("HELLO"))

    def test_ni_prefixes_and_suffix(self):
        self.assertTrue(rules.ni_ok("AB", "C"))
        self.assertTrue(rules.ni_ok("XZ", "B"))
        for prefix in ("BG", "GB", "NK", "KN", "TN", "NT", "ZZ", "DA", "FA", "IA", "QA", "UA", "VA", "AO", "AD", "A"):
            self.assertFalse(rules.ni_ok(prefix, "A"), prefix)
        self.assertFalse(rules.ni_ok("AB", "E"))

    def test_phone_shapes(self):
        for good in ("07700 900123", "+44 7700 900123", "+44 (0)7700 900123", "020 7946 0018", "01632 960001"):
            self.assertTrue(rules.phone_ok(good), good)
        for bad in ("0770 90012", "17700 900123", "07700 9001234567", "+44 0", "12345678"):
            self.assertFalse(rules.phone_ok(bad), bad)


class Find(unittest.TestCase):
    def test_card_good_and_bad(self):
        self.assertEqual(types("Card 4242 4242 4242 4242 exp 12/28"), ["card_number"])
        self.assertEqual(types("Card 378282246310005"), ["card_number"])
        self.assertEqual(types("Card 4242 4242 4242 4241"), [])
        self.assertEqual(types("ref 1234 5678 9012 3456"), [])

    def test_card_with_ocr_swaps(self):
        self.assertEqual(types("Card 4III 1111 1111 1111"), ["card_number"])  # I read for 1
        self.assertEqual(types("Card 4242 4242 4242 4242O"), [])  # O makes a 17-digit run that fails Luhn

    def test_iban(self):
        self.assertEqual(types("IBAN GB82 WEST 1234 5698 7654 32"), ["iban"])
        self.assertEqual(types("IBAN GB83 WEST 1234 5698 7654 32"), [])

    def test_ni_number(self):
        self.assertEqual(types("NI number AB 12 34 56 C"), ["ni_number"])
        self.assertEqual(types("NI number AB123456C"), ["ni_number"])
        self.assertEqual(types("NI number BG 12 34 56 C"), [])
        self.assertEqual(types("NI number AB 12 34 56 E"), [])
        self.assertEqual(types("NI number AB 12 3O 56 C"), ["ni_number"])  # O read for 0 inside the digits

    def test_sort_code_and_account(self):
        self.assertEqual(types("Sort code 12-34-56 Account number 12345678"), ["account_number", "sort_code"])
        self.assertEqual(types("12-34-56 12345678"), ["account_number", "sort_code"])  # an account number follows the sort code
        self.assertEqual(types("on 12-34-56 we met"), [])  # no label and no account number: a date-like number, left alone
        self.assertEqual(types("Total 12345678"), [])  # 8 digits without an account label
        self.assertEqual(types("Account 4780461S"), ["account_number"])  # S read for 5

    def test_email(self):
        self.assertEqual(types("write to a.b-c@example.org now"), ["email"])
        self.assertEqual(types("write to nobody at example dot org"), [])

    def test_phone(self):
        self.assertEqual(types("Call 07700 900123"), ["phone"])
        self.assertEqual(types("Call +44 7700 900123"), ["phone"])
        self.assertEqual(types("Call 0770 90012"), [])

    def test_postcode(self):
        for pc in ("SW1A 1AA", "M1 1AE", "EC1A 1BB", "W8 1JW", "M9E 0TQ"):
            self.assertEqual(types(f"Postcode {pc}"), ["postcode"], pc)
        for bad in ("SW1A 1A", "12345", "Postcode AAA BBB"):
            self.assertEqual(types(bad), [], bad)

    def test_dob_needs_a_label(self):
        self.assertEqual(types("DOB 12 Jan 1976"), ["dob"])
        self.assertEqual(types("Date of birth: 03/04/1988"), ["dob"])
        self.assertEqual(types("Born 3 March 1990"), ["dob"])
        self.assertEqual(types("Date of birth", "12 Jan 1976"), ["dob"])  # label alone on the line above
        self.assertEqual(types("Date of pay 12/06/2026"), [])
        self.assertEqual(types("Meeting on 12 Jan 1976"), [])

    def test_finding_box_is_the_union_of_its_words(self):
        found, _ = rules.find_values(lines_of("Sort code 12-34-56"))
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0].first, found[0].last), (2, 2))
        self.assertEqual(found[0].box, (20, 0, 29, 12))


class Judge(unittest.TestCase):
    def unexplained(self, *texts):
        found, made = rules.find_values(lines_of(*texts))
        claimed = {(f.line, k) for f in found for k in range(f.first, f.last + 1)}
        return rules.unexplained_tokens(made, claimed)

    def test_ordinary_words_and_amounts_are_explained(self):
        self.assertEqual(self.unexplained("Total £2,163.71 on 12/06/2026 thanks"), 0)
        self.assertEqual(self.unexplained("Tax code 1060L"), 0)

    def test_names_and_addresses_are_not(self):
        self.assertEqual(self.unexplained("Katie Edwards"), 2)
        self.assertEqual(self.unexplained("4 Heath Inlet"), 2)
        self.assertEqual(self.unexplained("ID GH8048004"), 1)

    def test_tokens_inside_a_rule_match_do_not_count(self):
        self.assertEqual(self.unexplained("DOB 12 Jan 1976"), 0)
        self.assertEqual(self.unexplained("Sort code 12-34-56 Account 12345678"), 0)


if __name__ == "__main__":
    unittest.main()
