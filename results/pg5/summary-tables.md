| Value type | Planted | Tesseract read it (original) | Rules covered it (box 90%+ black) | Covered, of those read | Read but NOT covered | Never read by Tesseract | Never read and not covered |
|---|---|---|---|---|---|---|---|
| account_number | 83 | 62 | 58 | 58 of 62 (94%) | 4 | 21 | 21 |
| card_number | 35 | 17 | 18 | 17 of 17 (100%) | 0 | 18 | 17 |
| dob | 85 | 73 | 57 | 56 of 73 (77%) | 17 | 12 | 11 |
| email | 43 | 25 | 16 | 15 of 25 (60%) | 10 | 18 | 17 |
| iban | 42 | 21 | 19 | 19 of 21 (90%) | 2 | 21 | 21 |
| ni_number | 46 | 31 | 30 | 30 of 31 (97%) | 1 | 15 | 15 |
| phone | 41 | 21 | 23 | 21 of 21 (100%) | 0 | 20 | 18 |
| postcode | 113 | 70 | 68 | 68 of 70 (97%) | 2 | 43 | 43 |
| sort_code | 84 | 62 | 60 | 60 of 62 (97%) | 2 | 22 | 22 |
| address (no rule) | 241 | 189 | 0 | 0 of 189 (0%) | 189 | 52 | 52 |
| id_number (no rule) | 56 | 44 | 0 | 0 of 44 (0%) | 44 | 12 | 12 |
| name (no rule) | 276 | 232 | 0 | 0 of 232 (0%) | 232 | 44 | 44 |
| **all 9 rule types** | 572 | 382 | 349 | 344 of 382 (90%) | 38 | 190 | |

Leak list by value type and picture type (planted values Tesseract never read on the original):
- account_number: {'payslip': 6, 'letter': 8, 'chat': 7}
- card_number: {'letter': 9, 'chat': 9}
- dob: {'payslip': 6, 'id_card': 2, 'chat': 4}
- email: {'letter': 13, 'chat': 5}
- iban: {'letter': 16, 'chat': 5}
- ni_number: {'payslip': 10, 'chat': 5}
- phone: {'letter': 8, 'chat': 12}
- postcode: {'payslip': 10, 'letter': 22, 'id_card': 11}
- sort_code: {'payslip': 6, 'letter': 7, 'chat': 9}
- address: {'payslip': 12, 'letter': 29, 'id_card': 1, 'chat': 10}
- id_number: {'id_card': 5, 'chat': 7}
- name: {'payslip': 6, 'letter': 35, 'id_card': 2, 'chat': 1}

Totals: values planted 1145 | never read 298
ordinary spans 3033 readable on original 2089 readable on safe copy (ablation) 1960
plain-text box pixels still visible (mean): 98.8 %

By picture type, values of the 9 rule types: {'payslip': '149 of 190 covered, 3 left readable', 'letter': '93 of 185 covered, 1 left readable', 'id_card': '45 of 76 covered, 17 left readable', 'chat': '62 of 121 covered, 2 left readable'}
