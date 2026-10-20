"""Made-up personal values. Every value is fictional or from a published test range."""
import datetime

from faker import Faker

# Published test card numbers (payment-provider documentation). All pass Luhn.
TEST_CARDS = [
    "4111111111111111", "4012888888881881", "4242424242424242", "4000056655665556",
    "5555555555554444", "5105105105105100", "2223003122003222", "378282246310005",
    "371449635398431", "6011111111111117", "6011000990139424", "3056930009020004",
]
# Fictional bank code for IBANs (4 letters) — not a real bank.
FICTIONAL_BANK_CODE = "TSTB"
# Ofcom drama range 07700 900000-900999 is reserved and never allocated.
NI_PREFIX_BAD_FIRST = set("DFIQUV")
NI_PREFIX_BAD_SECOND = set("DFIQUVO")
NI_PREFIX_BAD_PAIRS = {"BG", "GB", "NK", "KN", "TN", "NT", "ZZ"}

EMPLOYERS = ["Brindlecombe Logistics Ltd", "Halcyon Wren Studios Ltd", "Tarnside Civil Engineering",
             "Oakhaven Dental Group", "Quillfeather Retail Ltd", "Pennywhistle Foods plc",
             "Dunmere Print & Pack Ltd", "Saltmarsh Care Services"]
BANKS = ["Marlowe & Finch Savings", "Corvane Building Society", "Ashgrove Mutual", "Lowmoor Bank plc",
         "Thistledown Credit Union"]
ID_ISSUERS = ["Kingdom of Vellorin", "Republic of Carrowmere", "Eastmarch Federation", "Isle of Tarn"]
CHAT_APPS = ["Chatterly", "Pingwell", "Hullo!", "Nestbird"]
NATIONALITIES = {"Kingdom of Vellorin": "Vellorian", "Republic of Carrowmere": "Carrowmerian",
                 "Eastmarch Federation": "Eastmarcher", "Isle of Tarn": "Tarnish"}


def luhn_ok(num: str) -> bool:
    total, alt = 0, False
    for ch in reversed(num):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def iban_check_digits(country: str, bban: str) -> str:
    rearranged = bban + country + "00"
    digits = "".join(str(int(c, 36)) for c in rearranged)
    return f"{98 - int(digits) % 97:02d}"


def iban_ok(iban: str) -> bool:
    s = iban.replace(" ", "")
    digits = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return int(digits) % 97 == 1


def ni_format_ok(ni: str) -> bool:
    s = ni.replace(" ", "")
    if len(s) != 9 or not s[:2].isalpha() or not s[2:8].isdigit() or s[8] not in "ABCD":
        return False
    return (s[0] not in NI_PREFIX_BAD_FIRST and s[1] not in NI_PREFIX_BAD_SECOND
            and s[:2] not in NI_PREFIX_BAD_PAIRS)


class Person:
    """All the planted values for one picture. Drawn only from the per-picture rng."""

    def __init__(self, rng, seed_int):
        fk = Faker("en_GB")
        fk.seed_instance(seed_int)
        self.first = fk.first_name()
        self.last = fk.last_name()
        self.name = f"{self.first} {self.last}"
        self.street = f"{fk.building_number()} {fk.street_name()}"
        self.city = fk.city()
        self.postcode = fk.postcode()
        self.address = f"{self.street}, {self.city}"
        self.sort_code = "-".join(f"{rng.randint(0, 99):02d}" for _ in range(3))
        self.account = "".join(str(rng.randint(0, 9)) for _ in range(8))
        self.ni = self._ni(rng)
        self.card = rng.choice(TEST_CARDS)
        self.iban = self._iban(rng)
        self.id_number = f"{rng.choice('ABCDEFGHJKLMNPRSTWXYZ')}{rng.choice('ABCDEFGHJKLMNPRSTWXYZ')}" \
                         f"{rng.randint(0, 9999999):07d}"
        dob = datetime.date(1950, 1, 1) + datetime.timedelta(days=rng.randint(0, 55 * 365))
        self.dob_dt = dob
        self.dob = dob.strftime(rng.choice(["%d %b %Y", "%d/%m/%Y", "%d %B %Y"]))
        self.email = (f"{self.first}.{self.last}".lower().replace("'", "").replace(" ", "")
                      + "@" + rng.choice(["example.com", "example.org", "example.net", "mail.test"]))
        self.phone = f"07700 900{rng.randint(0, 999):03d}"

    @staticmethod
    def _ni(rng) -> str:
        letters = "ABCEGHJKLMNPRSTWXYZ"
        while True:
            pre = rng.choice(letters) + rng.choice(letters)
            if pre not in NI_PREFIX_BAD_PAIRS and pre[1] != "O":
                break
        num = "".join(str(rng.randint(0, 9)) for _ in range(6))
        ni = f"{pre} {num[:2]} {num[2:4]} {num[4:]} {rng.choice('ABCD')}"
        assert ni_format_ok(ni)
        return ni

    @staticmethod
    def _iban(rng) -> str:
        bban = FICTIONAL_BANK_CODE + "".join(str(rng.randint(0, 9)) for _ in range(14))
        cd = iban_check_digits("GB", bban)
        raw = f"GB{cd}{bban}"
        assert iban_ok(raw)
        return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4))

    @property
    def card_spaced(self) -> str:
        c = self.card
        if len(c) == 15:
            return f"{c[:4]} {c[4:10]} {c[10:]}"
        return " ".join(c[i:i + 4] for i in range(0, len(c), 4))
