# Failure log

Run 1 of each prompt version (pre-filter off). "Likely cause" is an automatic first guess; review it by hand, and check the label too.

## Before / after candidates (wrong in v1, fully correct in v4)

- **SMS 1**, `date`: v1 returned `02Nov26`, expected `2026-11-02` (date format not normalised correctly)
  > Dear UPI user A/C X8842 debited by 180.00 on date 02Nov26 trf to ZOMATO Refno 430712345678. If not u? call 1800111109. -SBI

- **SMS 2**, `date`: v1 returned `03/11/26`, expected `2026-11-03` (date format not normalised correctly)
  > Sent Rs.350.00 From HDFC Bank A/C *4417 To UBER INDIA On 03/11/26 Ref 430823456789 Not You? Call 18002586161/SMS BLOCK UPI to 7308080808

- **SMS 3**, `date`: v1 returned `04-Nov-26`, expected `2026-11-04` (date format not normalised correctly)
  > ICICI Bank Acct XX219 debited for Rs 1,240.00 on 04-Nov-26; BLINKIT credited. UPI:430934567890. Call 18002662 for dispute. SMS BLOCK 219 to 9215676766.

## v1: 40 wrong predictions

| id | field | expected | predicted | likely cause | SMS |
|---|---|---|---|---|---|
| 1 | date | 2026-11-02 | 02Nov26 | date format not normalised correctly | Dear UPI user A/C X8842 debited by 180.00 on date 02Nov26 trf to ZOMATO Refno 430712345678. If not u? call 1800111109. -SBI |
| 2 | date | 2026-11-03 | 03/11/26 | date format not normalised correctly | Sent Rs.350.00 From HDFC Bank A/C *4417 To UBER INDIA On 03/11/26 Ref 430823456789 Not You? Call 18002586161/SMS BLOCK UPI to 7308080808 |
| 3 | date | 2026-11-04 | 04-Nov-26 | date format not normalised correctly | ICICI Bank Acct XX219 debited for Rs 1,240.00 on 04-Nov-26; BLINKIT credited. UPI:430934567890. Call 18002662 for dispute. SMS BLOCK 219 to 9215676766. |
| 4 | date | 2026-11-05 | 05-11-26 | date format not normalised correctly | INR 89.00 debited from A/c no. XX5521 on 05-11-26 14:22:10 IST UPI/P2M/431045678901/RAPIDO. Not you? SMS BLOCKUPI Cust ID to 919951860002 - Axis Bank |
| 5 | date | 2026-11-05 | 05-11-26 | date format not normalised correctly | Sent Rs.2,500.00 from Kotak Bank AC X7730 to rahul.verma@okaxis on 05-11-26.UPI Ref 431156789012. Not you, https://kotak.com/KBANKT/Fraud |
| 6 | date | 2026-11-06 | 06-11-26 | date format not normalised correctly | A/c XX6034 debited INR 60.00 Dt 06-11-26 10:15 thru UPI:431267890123.Bal INR 8,412.55 Not u?Fwd this SMS to 9264092640 to block UPI.-PNB |
| 7 | date | 2026-11-06 | 2026:11:06 | date format not normalised correctly | Rs.450.00 Dr. from A/C XXXXXX2291 and Cr. to swiggy@axisbank. Ref:431378901234. AvlBal:Rs15,220.10(2026:11:06 20:41:09). Not you? Call 18005700/5000-BOB |
| 8 | date | 2026-11-07 | 07 Nov 2026 | date format not normalised correctly | Paid Rs. 199 to JIO via PhonePe UPI on 07 Nov 2026. Txn ID T2611071234567890. Bal: Rs. 4,311.20 |
| 9 | date | 2026-11-08 | 08Nov26 | date format not normalised correctly | Your a/c XX9087 is debited by Rs.1,200.00 on 08Nov26 and credited to PRIYA SHARMA (UPI Ref no 431489012345). -SBI |
| 10 | date | 2026-11-08 | 08/11/26 | date format not normalised correctly | Sent Rs.75.00 From HDFC Bank A/C *4417 To CHAI POINT On 08/11/26 Ref 431590123456 Not You? Call 18002586161/SMS BLOCK UPI to 7308080808 |
| 11 | date | 2026-11-09 | 09-11-26 | date format not normalised correctly | INR 640.00 debited from A/c no. XX5521 on 09-11-26 18:02:44 IST UPI/P2M/431601234567/DMART. Not you? SMS BLOCKUPI Cust ID to 919951860002 - Axis Bank |
| 12 | date | 2026-11-01 | 01-11-26 | date format not normalised correctly | Rs.15,000.00 debited from A/c XX9087 on 01-11-26 to VPA nobroker@icici (UPI Ref No 430590123111). If not done by you, call 1800111109 -SBI |
| 13 | date | 2026-11-10 | 10-Nov-26 | date format not normalised correctly | ICICI Bank Acct XX219 debited for Rs 520.00 on 10-Nov-26; APOLLO PHARMACY credited. UPI:431712345670. Call 18002662 for dispute. SMS BLOCK 219 to 9215676766. |
| 14 | date | 2026-11-11 | 2026:11:11 | date format not normalised correctly | Rs.30.00 Dr. from A/C XXXXXX2291 and Cr. to paytmqr28100505@paytm. Ref:431823456781. AvlBal:Rs14,740.10(2026:11:11 09:12:45). Not you? Call 18005700/5000-BOB |
| 16 | date | 2026-11-03 | 03-Nov-26 | date format not normalised correctly | INR 649.00 spent using ICICI Bank Card XX4005 on 03-Nov-26 on NETFLIX. Avl Limit: INR 1,12,351.00. If not you, call 1800 2662/SMS BLOCK 4005 to 9215676766. |
| 17 | date | 2026-11-06 | 06-11-26 | date format not normalised correctly | Spent INR 3,150.75 Axis Bank Card no. XX8123 06-11-26 13:45:20 IST MAKEMYTRIP Avl Lmt INR 96,849.25 Not you? SMS BLOCK 8123 to 919951860002 |
| 18 | date | 2026-11-07 | 07Nov26 | date format not normalised correctly | Dear Customer, transaction number 631012345678 for Rs.899.00 by SBI Debit Card X3345 done at PYU*MYNTRA DESIGNS on 07Nov26 at 16:20:11. Your updated available balance is Rs.18,240.60. If not done by you, forward this SMS to 7400165218 -SBI |
| 19 | date | 2026-11-09 | 09/11/2026 | date format not normalised correctly | Rs.1,675.00 spent via Kotak Debit Card XX9912 at STARBUCKS COFFEE on 09/11/2026. Avl bal Rs.33,105.45. Not you? Call 18602662666 |
| 20 | date | 2026-11-10 | 10-11-26 | date format not normalised correctly | Rs.560.00 debited from HDFC Bank Debit Card ending 5566 at BOOKMYSHOW on 10-11-26. Avl bal: Rs.27,430.00. Not you? Call 18002586161 |
| 21 | date | 2026-11-01 | 01-NOV-26 | date format not normalised correctly | Update! INR 52,000.00 deposited in HDFC Bank A/c XX4417 on 01-NOV-26 for NEFT Cr-UTIB0000123-INFOTECH SOLUTIONS PVT LTD-SALARY OCT. Avl bal INR 61,540.20. Cheque deposits in A/C are subject to clearing |
| 22 | date | 2026-11-04 | 04Nov26 | date format not normalised correctly | Dear SBI User, your A/c X9087-credited by Rs.500 on 04Nov26 transfer from ANKIT GUPTA Ref No 430998765432 -SBI |
| 22 | mode | OTHER | UPI | payment mode inferred or confused (e.g. autopay vs the rail it ran on) | Dear SBI User, your A/c X9087-credited by Rs.500 on 04Nov26 transfer from ANKIT GUPTA Ref No 430998765432 -SBI |
| 23 | date | 2026-11-06 | 06-11-26 | date format not normalised correctly | Received Rs.1,250.00 in your Kotak Bank AC X7730 from sneha.iyer@okhdfcbank on 06-11-26.UPI Ref:431087654321. |
| 24 | date | 2026-10-31 | 31-10-26 | date format not normalised correctly | Dear Customer, Interest of Rs.212.00 has been credited to your SB A/c XX6034 on 31-10-26. Avl Bal Rs.8,624.55 -PNB |
| 25 | date | 2026-11-08 | 08-11-26 | date format not normalised correctly | INR 8,000.00 credited to A/c no. XX5521 on 08-11-26 at 11:05:32 IST. Info- IMPS/P2A/631312345678/MOHAN DAS/HDFCBANK. Avl Bal- INR 19,345.10 - Axis Bank |
| 26 | date | 2026-11-09 | 09-Nov-26 | date format not normalised correctly | Rs.25.00 cashback from CRED credited to your ICICI Bank Acct XX219 on 09-Nov-26. Avl Bal Rs.6,480.75 |
| 27 | date | 2026-11-03 | 03Nov26 | date format not normalised correctly | Dear Customer, Rs.2,000.00 withdrawn at SBI ATM S1BW000345 from A/c X9087 on 03Nov26. Transaction Number 6307. Available Balance Rs.14,250.00. If not withdrawn by you, forward this SMS to 7400165218 -SBI |
| 28 | date | 2026-11-07 | 07-11-26 | date format not normalised correctly | Rs.5000 withdrawn from HDFC Bank A/c XX4417 at ATM +MG ROAD BANGALORE on 07-11-26. Avl bal: Rs.56,540.20. Not you? Call 18002586161 |
| 29 | date | 2026-11-10 | 10-11-26 | date format not normalised correctly | INR 1,500.00 withdrawn from A/c no. XX5521 at ATM ID SPCN01234 on 10-11-26 20:15:03 IST. Avl Bal INR 17,845.10. Not you? Call 18604195555 - Axis Bank |
| 30 | date | 2026-11-05 | 05-Nov-26 | date format not normalised correctly | Rs.199.00 has been debited from your A/c XX3318 towards your e-mandate for NETFLIX on 05-Nov-26 (UMN: a1b2c3d4@okhdfcbank). Avl Bal Rs.9,801.00 -HDFC Bank |
| 31 | date | 2026-11-08 | 08-11-26 | date format not normalised correctly | Your UPI AutoPay payment of Rs.119.00 to SPOTIFY INDIA has been successfully debited from Kotak Bank AC X7730 on 08-11-26. UPI Ref 431298761234. |
| 32 | date | 2026-11-10 | 10-11-26 | date format not normalised correctly | INR 2,000.00 debited from A/c no. XX5521 on 10-11-26 towards NACH/ACH-DR-GROWW MF SIP-BSE0000012. Avl Bal INR 15,845.10 - Axis Bank |
| 33 | date | 2026-11-05 | 05-Nov-26 | date format not normalised correctly | Refund of Rs.1,299.00 from AMAZON has been processed to your ICICI Bank Card XX4005 on 05-Nov-26. |
| 34 | date | 2026-11-07 | 07-Nov-26 | date format not normalised correctly | Dear Customer, refund of INR 349.00 from SWIGGY credited to your A/c XX219 on 07-Nov-26. UPI:431487650987 -ICICI Bank |
| 35 | date | 2026-11-11 | 11Nov26 | date format not normalised correctly | Rs.4,500.00 refunded by IRCTC to your SBI A/c X9087 on 11Nov26 against cancelled ticket. Ref 631598761234 |
| 36 | date | 2026-11-04 | 04-11-26 | date format not normalised correctly | Txn of Rs.1,100.00 on HDFC Bank Card x7788 at BIGBASKET was declined on 04-11-26 due to insufficient limit. Not you? Call 18002586161 |
| 37 | date | 2026-11-06 | 06-Nov-26 | date format not normalised correctly | UPI payment of Rs 240.00 to OLA CABS failed on 06-Nov-26. Any amount debited will be reversed in 3-5 days. Ref 431687659876 -ICICI Bank |
| 38 | date | 2026-11-08 | 08Nov26 | date format not normalised correctly | Dear Customer, your ATM withdrawal of Rs.3,000.00 on 08Nov26 was unsuccessful. If amount is debited, it will be credited back within 5 working days. -SBI |
| 39 | date | 2026-11-08 | 08-Nov-26 | date format not normalised correctly | Rs.240.00 reversed to your ICICI Bank Acct XX219 on 08-Nov-26 against failed UPI txn Ref 431687659876. |
| 40 | date | 2026-11-09 | 09-11-26 | date format not normalised correctly | Dear Customer, Rs.560.00 debited from your A/c XX4417 on 09-11-26 for a failed UPI transaction to zepto@icici has been reversed and credited back to your account. -HDFC Bank |

## v2: 4 wrong predictions

| id | field | expected | predicted | likely cause | SMS |
|---|---|---|---|---|---|
| 22 | mode | OTHER | UPI | payment mode inferred or confused (e.g. autopay vs the rail it ran on) | Dear SBI User, your A/c X9087-credited by Rs.500 on 04Nov26 transfer from ANKIT GUPTA Ref No 430998765432 -SBI |
| 27 | merchant | null | SBI ATM S1BW000345 | value invented or inferred; the SMS does not state it | Dear Customer, Rs.2,000.00 withdrawn at SBI ATM S1BW000345 from A/c X9087 on 03Nov26. Transaction Number 6307. Available Balance Rs.14,250.00. If not withdrawn by you, forward this SMS to 7400165218 -SBI |
| 28 | merchant | null | ATM +MG Road Bangalore | value invented or inferred; the SMS does not state it | Rs.5000 withdrawn from HDFC Bank A/c XX4417 at ATM +MG ROAD BANGALORE on 07-11-26. Avl bal: Rs.56,540.20. Not you? Call 18002586161 |
| 29 | merchant | null | ATM ID SPCN01234 | value invented or inferred; the SMS does not state it | INR 1,500.00 withdrawn from A/c no. XX5521 at ATM ID SPCN01234 on 10-11-26 20:15:03 IST. Avl Bal INR 17,845.10. Not you? Call 18604195555 - Axis Bank |

## v3: 1 wrong predictions

| id | field | expected | predicted | likely cause | SMS |
|---|---|---|---|---|---|
| 22 | mode | OTHER | UPI | payment mode inferred or confused (e.g. autopay vs the rail it ran on) | Dear SBI User, your A/c X9087-credited by Rs.500 on 04Nov26 transfer from ANKIT GUPTA Ref No 430998765432 -SBI |

## v4: 1 wrong predictions

| id | field | expected | predicted | likely cause | SMS |
|---|---|---|---|---|---|
| 22 | mode | OTHER | UPI | payment mode inferred or confused (e.g. autopay vs the rail it ran on) | Dear SBI User, your A/c X9087-credited by Rs.500 on 04Nov26 transfer from ANKIT GUPTA Ref No 430998765432 -SBI |
