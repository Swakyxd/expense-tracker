# Failure log

Run 1 of each prompt version (pre-filter off). "Likely cause" is an automatic first guess; review it by hand, and check the label too.

## Before / after candidates (wrong in v1, fully correct in v4)

- **SMS 202**, `date`: v1 returned `04-Nov-26`, expected `2026-11-04` (date format not normalised correctly)
  > USD 15.49 spent on ICICI Bank Card XX4005 at NETFLIX.COM on 04-Nov-26. Equivalent amount debited: INR 1,309.90. Avl Limit: INR 1,10,041.10

- **SMS 203**, `date`: v1 returned `6 Nov`, expected `2026-11-06` (date format not normalised correctly)
  > Rs.340 paid to ZOMATO via Paytm UPI on 6 Nov at 8:42 PM. UPI Ref 431087651100. Paytm Payments

- **SMS 204**, `date`: v1 returned `07Nov26`, expected `2026-11-07` (date format not normalised correctly)
  > Your A/c XX9087 debited by Rs.5,000.00 on 07Nov26; MOHIT ARORA credited (IMPS Ref 631198765432). If not done by you call 1800111109 -SBI

## v1: 18 wrong predictions

| id | field | expected | predicted | likely cause | SMS |
|---|---|---|---|---|---|
| 201 | date | 2026-11-03 | 03-Nov-26 | date format not normalised correctly | Rs.2,000.00 withdrawn at ICICI Bank ATM on 03-Nov-26 from Acct XX219. Charge of Rs.23.60 for exceeding free ATM transactions will be debited separately. Avl Bal Rs.11,540.20 |
| 201 | merchant | null | ICICI Bank ATM | value invented or inferred; the SMS does not state it | Rs.2,000.00 withdrawn at ICICI Bank ATM on 03-Nov-26 from Acct XX219. Charge of Rs.23.60 for exceeding free ATM transactions will be debited separately. Avl Bal Rs.11,540.20 |
| 202 | date | 2026-11-04 | 04-Nov-26 | date format not normalised correctly | USD 15.49 spent on ICICI Bank Card XX4005 at NETFLIX.COM on 04-Nov-26. Equivalent amount debited: INR 1,309.90. Avl Limit: INR 1,10,041.10 |
| 203 | date | 2026-11-06 | 6 Nov | date format not normalised correctly | Rs.340 paid to ZOMATO via Paytm UPI on 6 Nov at 8:42 PM. UPI Ref 431087651100. Paytm Payments |
| 204 | date | 2026-11-07 | 07Nov26 | date format not normalised correctly | Your A/c XX9087 debited by Rs.5,000.00 on 07Nov26; MOHIT ARORA credited (IMPS Ref 631198765432). If not done by you call 1800111109 -SBI |
| 205 | date | 2026-11-08 | 08-11-26 | date format not normalised correctly | Standing Instruction executed: Rs.1,499.00 charged to your Axis Bank Card XX8123 for YOUTUBE PREMIUM on 08-11-26. Next charge on 08-12-26. |
| 205 | mode | AUTOPAY | CARD | payment mode inferred or confused (e.g. autopay vs the rail it ran on) | Standing Instruction executed: Rs.1,499.00 charged to your Axis Bank Card XX8123 for YOUTUBE PREMIUM on 08-11-26. Next charge on 08-12-26. |
| 206 | date | 2026-11-09 | 09-Nov-26 | date format not normalised correctly | Dear Customer, your UPI txn of Rs.899.00 to MEESHO on 09-Nov-26 was unsuccessful. Rs.899.00 has been credited back to A/c XX219. Ref 631287651234 -ICICI Bank |
| 206 | status | reversed | success | failed / reversed wording misread | Dear Customer, your UPI txn of Rs.899.00 to MEESHO on 09-Nov-26 was unsuccessful. Rs.899.00 has been credited back to A/c XX219. Ref 631287651234 -ICICI Bank |
| 206 | category | Refund | Shopping | merchant not in rules; LLM fallback chose differently (or upstream merchant error) | Dear Customer, your UPI txn of Rs.899.00 to MEESHO on 09-Nov-26 was unsuccessful. Rs.899.00 has been credited back to A/c XX219. Ref 631287651234 -ICICI Bank |
| 208 | date | 2026-11-10 | 10-11-26 | date format not normalised correctly | Rs.750.00 debited from A/c XX4417 on 10-11-26 to VPA bharatpe.9087654321@fbpe (GANESH MEDICALS). UPI Ref 431887650022 -HDFC Bank |
| 209 | date | 2026-11-10 | 10-Nov-26 | date format not normalised correctly | INR 1,299.00 spent on ICICI Bank Card XX4005 on 10-Nov-26 at DECATHLON SPORTS IN. Avl Lmt: INR 1,08, |
| 210 | date | 2026-11-11 | 11-11-26 | date format not normalised correctly | Your A/c XX3390 is credited with Rs.3,200.00 on 11-11-26 by NEFT from ZERODHA BROKING LTD (Ref HDFCN26315998877). Avl Bal Rs.55,510.40 -ICICI Bank |
| 212 | date | 2026-11-12 | 12-11-26 | date format not normalised correctly | Rs.20,000.00 transferred from A/c XX4417 to own A/c XX8830 via NEFT on 12-11-26. Ref HDFCN26316009988. -HDFC Bank |
| 213 | date | 2026-11-13 | 13-11-26 | date format not normalised correctly | INR 1,25,000 debited from A/c XX5521 on 13-11-26 towards NEFT to DELHI PUBLIC SCHOOL. Ref AXISN26317004512. Avl Bal INR 2,14,845.10 - Axis Bank |
| 214 | date | 2026-11-13 | 13/11/2026 | date format not normalised correctly | INR 2,640.00 spent on Kotak Debit Card XX9912 at HPCL SRI SAI FUELS on 13/11/2026. Fuel surcharge of INR 26.40 reversed. Avl bal INR 30,465.45 |
| 215 | date | 2026-11-13 | 13-11-26 | date format not normalised correctly | ANANYA RAO paid you Rs.850.00 via UPI on 13-11-26. Credited to A/c XX4417. UPI Ref 432087650055 |
| 216 | date | 2026-11-12 | 12-11-26 | date format not normalised correctly | Mandate executed: Rs.299.00 debited from A/c XX4417 for HOTSTAR via UPI AutoPay on 12-11-26. UMN 5d7e11aa@okhdfcbank |

## v2: 4 wrong predictions

| id | field | expected | predicted | likely cause | SMS |
|---|---|---|---|---|---|
| 201 | merchant | null | ICICI Bank ATM | value invented or inferred; the SMS does not state it | Rs.2,000.00 withdrawn at ICICI Bank ATM on 03-Nov-26 from Acct XX219. Charge of Rs.23.60 for exceeding free ATM transactions will be debited separately. Avl Bal Rs.11,540.20 |
| 207 | date | null | 2026-11-07 | value invented or inferred; the SMS does not state it | Rs.2,150.00 debited from A/c XX5521 for UPI txn to MAKEMYTRIP could not be processed and will be reversed within 48 hrs. Ref 431787650011 - Axis Bank |
| 211 | date | null | 2026-11-11 | value invented or inferred; the SMS does not state it | Rs 60 paid to RAMESH TEA STALL using BHIM UPI. Aapka balance Rs 2,341.50 hai. Ref 431987650044 |
| 212 | merchant | null | Own Account | value invented or inferred; the SMS does not state it | Rs.20,000.00 transferred from A/c XX4417 to own A/c XX8830 via NEFT on 12-11-26. Ref HDFCN26316009988. -HDFC Bank |

## v3: 2 wrong predictions

| id | field | expected | predicted | likely cause | SMS |
|---|---|---|---|---|---|
| 201 | merchant | null | ICICI Bank ATM | value invented or inferred; the SMS does not state it | Rs.2,000.00 withdrawn at ICICI Bank ATM on 03-Nov-26 from Acct XX219. Charge of Rs.23.60 for exceeding free ATM transactions will be debited separately. Avl Bal Rs.11,540.20 |
| 205 | mode | AUTOPAY | CARD | payment mode inferred or confused (e.g. autopay vs the rail it ran on) | Standing Instruction executed: Rs.1,499.00 charged to your Axis Bank Card XX8123 for YOUTUBE PREMIUM on 08-11-26. Next charge on 08-12-26. |

## v4: 2 wrong predictions

| id | field | expected | predicted | likely cause | SMS |
|---|---|---|---|---|---|
| 201 | merchant | null | ICICI Bank ATM | value invented or inferred; the SMS does not state it | Rs.2,000.00 withdrawn at ICICI Bank ATM on 03-Nov-26 from Acct XX219. Charge of Rs.23.60 for exceeding free ATM transactions will be debited separately. Avl Bal Rs.11,540.20 |
| 205 | mode | AUTOPAY | CARD | payment mode inferred or confused (e.g. autopay vs the rail it ran on) | Standing Instruction executed: Rs.1,499.00 charged to your Axis Bank Card XX8123 for YOUTUBE PREMIUM on 08-11-26. Next charge on 08-12-26. |
