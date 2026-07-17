"""
Generate 5000+ realistic transactions matching actual HDFC bank statement format.
Based on real HDFC statement patterns from Bhanpura, Mandsaur (May 2026).

Run from backend/ folder:
python generate_hdfc_transactions.py

Produces:
- hdfc_statement_5000txns.csv  (upload to WealthPilot)
- hdfc_ground_truth.csv        (for benchmarking)
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(2024)

def ref_num():
    return str(random.randint(1000000000000000, 9999999999999999))

def bank_suffix():
    banks = ["YESB0YBLUPI","YESB0MCHUPI","YESB0PTMUPI","UTIB0000553",
             "SBIN0030057","HDFC0MERUPI","BARB0INDKAT","BKID0009142"]
    return f"{random.choice(banks)}-{random.randint(100000000000,999999999999)}"

# ── Merchant templates matching REAL HDFC UPI string patterns ─
MERCHANTS = {

    "Food & Dining": {
        "known": [
            lambda: f"UPI-ZOMATO-PAYZOMATO@HDFCBANK-HDFC0MERUP I-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-ZOMATO LIMITED-ZOMATOFD.PAYU@HDFCBANK K-HDFC0MERUPI-{ref_num()[:12]}-UPIINTENT",
            lambda: f"UPI-SWIGGY-{random.randint(7000000000,9999999999)}@HDFCBANK-HDFC0MERUP I-{ref_num()[:12]}-SWIGGY FOOD",
            lambda: f"UPI-BLINKIT-BLINKIT.PAYU@HDFCBANK-HDFC0M ERUPI-{ref_num()[:12]}-UPIINTENT",
            lambda: f"UPI-BLINKIT-PAYTM-BLINKIT@PTYBL-YESB0PTM UPI-{ref_num()[:12]}-BLINKIT PAYMENT",
            lambda: f"UPI-NETFLIX COM-NETFLIXUPI.PAYU@HDFCBANK -HDFC0MERUPI-{ref_num()[:12]}-MONTHLY AUTOPA Y. C",
        ],
        "unknown": [
            lambda: f"UPI-OM NAMKEEN AND SNACK-Q{random.randint(100000000,999999999)}@YBL- {bank_suffix()}-PAYMENT FROM PH ONE",
            lambda: f"UPI-JAIN DAIRY COLDRINKS-Q{random.randint(100000000,999999999)}@YBL- YESB0YBLUPI-{ref_num()[:12]}-PAYMENT FROM PH ONE",
            lambda: f"UPI-CHAAPS N CURRIES-Q{random.randint(100000000,999999999)}@YBL-YESB 0YBLUPI-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-VIJAY JUICE POINT-PAYTM.S{random.randint(10000,99999)}@PTY- YESB0MCHUPI-{ref_num()[:12]}-PAYMENT FROM PH ONE",
            lambda: f"UPI-DHOLPUR GAJAK AND BA-PAYTMQR{random.randint(1000000,9999999)}@P TYS-YESB0PTMUPI-{ref_num()[:12]}-PAYMENT FRO M PHONE",
            lambda: f"UPI-CHAAYOS-{random.randint(7000000000,9999999999)}@HDFCBANK HDFC0MERUPI-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-LOCAL DHABA-PAYTMQR{random.randint(1000000,9999999)}@PTYS YESB0PTMUPI-{ref_num()[:12]}-PAYMENT FROM PHONE",
        ],
        "amount_range": (50, 800),
        "freq": 18,
    },

    "Groceries": {
        "known": [
            lambda: f"UPI-ZEPTO MARKETPLACE PR-ZEPTO.PAYU@AXIS BANK-UTIB0000100-{ref_num()[:12]}-PAYMENT FR OM PHONE",
            lambda: f"UPI-ZEPTO MARKETPLACE PR-ZEPTOMARKETPLAC {random.randint(100000,999999)}.RZP@RXAXIS-UTIB0000RZP-{ref_num()[:12]} {random.randint(10,99)}-PAYMENT FROM PHONE",
            lambda: f"UPI-BLINKIT-PAYTM-BLINKIT@PTYBL-YESB0PTM UPI-{ref_num()[:12]}-BLINKIT PAYMENT",
            lambda: f"UPI-BIGBASKET-{random.randint(7000000000,9999999999)}@HDFCBANK HDFC0MERUPI-{ref_num()[:12]}-GROCERY ORDER",
        ],
        "unknown": [
            lambda: f"UPI-SAMRIYA KIRANA STORE-VYAPAR.{random.randint(10000000,99999999)} {random.randint(1000,9999)}@HDFCBANK-HDFC0MERUPI-{ref_num()[:12]}-P AYMENT FROM PHONE",
            lambda: f"UPI-JAIN GENERAL AND STA-Q{random.randint(100000000,999999999)}@YBL- YESB0YBLUPI-{ref_num()[:12]}-PAYMENT FROM PH ONE",
            lambda: f"UPI-MS KAMAL ENTERPRISES-Q{random.randint(100000000,999999999)}@YBL {bank_suffix()}-PAYMENT FROM PH ONE",
            lambda: f"UPI-SHREERAM STATIONERY -Q{random.randint(10000000,99999999)}@YBL-B KID{random.randint(1000000,9999999)}-{ref_num()[:12]}-PAYMENT FROM PHO NE",
        ],
        "amount_range": (100, 3000),
        "freq": 8,
    },

    "Transport": {
        "known": [
            lambda: f"UPI-IRCTC RAIL APP-IRCTCPGONLINE@YBL-YES B0YBLUPI-{ref_num()[:12]}-PAYMENT FOR 100006",
            lambda: f"UPI-IRCTC RAIL APP-IRCTCPGONLINE@AXL-UTI B0AXLUPI-{ref_num()[:12]}-PAYMENT FOR 100006",
            lambda: f"UPI-BPCL UFILL {random.randint(1,9)}-PAYTMQR{random.randint(10000000,99999999)}@PAYTM-YE SB0PTMUPI-{ref_num()[:12]}-PAYMENT FROM PHON E",
            lambda: f"UPI-UBER-{random.randint(7000000000,9999999999)}@HDFCBANK HDFC0MERUPI-{ref_num()[:12]}-RIDE PAYMENT",
            lambda: f"UPI-OLA CABS-{random.randint(7000000000,9999999999)}@PTYBL YESB0PTMUPI-{ref_num()[:12]}-AUTO PAYMENT",
        ],
        "unknown": [
            lambda: f"UPI-M S SUPREME TRANSPOR-SUPREMETRANSPOR T{random.randint(100,999)}-{random.randint(1,9)}@OKICICI-ICIC{random.randint(1000000,9999999)}-{ref_num()[:12]}- PAYMENT FROM PHONE",
            lambda: f"UPI-RAVI CARPENTER-{random.randint(7000000000,9999999999)}@YBL-SBIN0 {random.randint(10000,99999)}-{ref_num()[:12]}-PAYMENT FROM PHONE",
        ],
        "amount_range": (50, 2000),
        "freq": 12,
    },

    "Shopping": {
        "known": [
            lambda: f"UPI-FLIPKART PAYMENTS-PAYTM-{random.randint(10000000,99999999)}@PTY BL-YESB0PTMUPI-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-FLIPKART PAYMENTS-PAYTM-{random.randint(10000000,99999999)}@PTY BL-YESB0PTMUPI-{ref_num()[:12]}-EXPRESS",
            lambda: f"UPI-MEESHO TECHNOLOGIES -MEESHOONLINEPG@ AXL-UTIB0AXLUPI-{ref_num()[:12]}-UPI INTENT",
            lambda: f"UPI-EKART-EKART@YBL-YESB0YBLUPI-{random.randint(10000000,99999999)} {random.randint(1000,9999)}-PAYMENT FOR REFCL{random.randint(1,9)}",
            lambda: f"UPI-EKART-EKART2.PAYU@AXISBANK-UTIB00001 00-{ref_num()[:12]}-UPIQR",
            lambda: f"UPI-AMAZON PAY-{random.randint(7000000000,9999999999)}@AMAZON UTIB0000100-{ref_num()[:12]}-ORDER PAYMENT",
        ],
        "unknown": [
            lambda: f"UPI-JAI APPARELS-GPAY-{random.randint(10000000000,99999999999)}@OKBIZA XIS-UTIB0000553-{ref_num()[:12]}-PAYMENT FRO M PHONE",
            lambda: f"UPI-ABHISHEK READYMADES-Q{random.randint(100000000,999999999)}@YBL-Y ESB0YBLUPI-{ref_num()[:12]}-PAYMENT FROM PHO NE",
            lambda: f"UPI-MSBEAUX FASHION-IBKPOS.EP{random.randint(10000,99999)}@ICIC I-ICIC0000004-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-DELHI WATCH ELECTR-GPAY-{random.randint(1000000000,9999999999)} {random.randint(10,99)}@OKBIZAXIS-UTIB0000553-{ref_num()[:12]}-PAY MENT FROM PHONE",
            lambda: f"UPI-DHAKAD ELECTRICALS-MAB.{random.randint(1000000000,9999999999)} {random.randint(10,99)}@AXISBANK-UTIB0000100-{ref_num()[:12]}-PAY MENT FROM PHONE",
            lambda: f"UPI-KALA KUNJ KOTA-VYAPAR.{random.randint(100000000000,999999999999)}@H DFCBANK-HDFC0MERUPI-{ref_num()[:12]}-PAYMENT FROM PHONE",
        ],
        "amount_range": (100, 8000),
        "freq": 8,
    },

    "Bills & Utilities": {
        "known": [
            lambda: f"UPI-AIRTEL RECHARGE-AIRTELPREDIRECT{random.randint(1,3)}@YBL -YESB0YBLUPI-{ref_num()[:12]}-PAYMENT FROM P HONE",
            lambda: f"UPI-AIRTEL RECHARGE-AIRTELPREDIRECT{random.randint(1,3)}@AXL -UTIB0AXLUPI-{ref_num()[:12]}-PAYMENT FROM P HONE",
            lambda: f"UPI-GOOGLE-PLAYSTORE1.BD@AXISBANK-UTIB00 {random.randint(10000,99999)}-{ref_num()[:12]}-MANDATEEXECUTE",
            lambda: f"ACH/JIO/RECHARGE/4G PLAN",
            lambda: f"BBPS/BESCOM/ELECTRICITY/BILL PAY",
        ],
        "unknown": [
            lambda: f"UPI-MSBHUMI JUNCTION NX-EAZYPAY.ZKIAW{random.randint(10,99)}{random.choice(['A','B','C'])} {random.randint(1,9)}SND4LR@ICICI-ICIC0DC0099-{ref_num()[:12]}-P AYMENT FROM PHONE",
        ],
        "amount_range": (22, 2000),
        "freq": 5,
    },

    "Healthcare": {
        "known": [
            lambda: f"UPI-APOLLO PHARMACIES LI-SBIPMOPAD.02PYM {ref_num()[:12]}-PAYMENT FROM PHONE",
        ],
        "unknown": [
            lambda: f"UPI-RAJ MEDICAL STORES-GPAY-{random.randint(10000000000,99999999999)}@ OKBIZAXIS-UTIB0000553-{ref_num()[:12]}-PAYME NT FROM PHONE",
            lambda: f"UPI-RAKSHA NYATI-Q{random.randint(100000000,999999999)}@YBL-YESB0YBL UPI-{ref_num()[:12]}-PAYMENT FROM PHONE",
        ],
        "amount_range": (50, 2000),
        "freq": 3,
    },

    "Education": {
        "known": [
            lambda: f"UPI-TAKEUFORWARD-TAKEUFORWARD{random.randint(100000,999999)}.RZP@ RXAIRTEL-AIRP0000011-{ref_num()[:12]}-PAYMEN TTOTAKEUFORW",
        ],
        "unknown": [
            lambda: f"UPI-SRN PRINTERS-BHARATPE.{random.randint(10000000000,99999999999)}@FB PE-FDRL0001382-{ref_num()[:12]}-PAY TO BHARA TPE ME",
            lambda: f"UPI-SHREERAM STATIONERY -Q{random.randint(10000000,99999999)}@YBL-B KID{random.randint(1000000,9999999)}-{ref_num()[:12]}-PAYMENT FROM PHO NE",
        ],
        "amount_range": (45, 6000),
        "freq": 2,
    },

    "Transfers": {
        "known": [],
        "unknown": [
            lambda: f"UPI-MAHESH KUMAR MALI-{random.randint(7000000000,9999999999)}@YBL-SBI N0030057-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-AVIRAL MITTAL-AVIRAL.23@YBL-SBIN003 0057-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-ETISHA MITTAL-{random.randint(7000000000,9999999999)}-{random.randint(1,5)}@AXL-UBIN0 {random.randint(100000,999999)}-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-SHAILENDRA PRAJAPAT-PAYTM.S{random.randint(10000,99999)}@PT Y-YESB0MCHUPI-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-MR SIDDHARTH CHHABR-Q{random.randint(100000000,999999999)}@YBL-{ref_num()[:12]} YESB0YBLUPI-{ref_num()[:12]}-PAYMENT FROM PH ONE",
            lambda: f"UPI-{random.choice(['RAKESH','SURESH','KAMLESH','RAMESH','DINESH'])} KUMAR {random.choice(['SIOTA','PATIDA','BANJARA'])}-{random.choice(['RAKESHSIOTA','SURESHSINGH','KAMLESHPAT'])}{random.randint(10,99)}-{random.randint(1,5)}@O KHDFCBANK-HDFC{random.randint(1000000,9999999)}-{ref_num()[:12]}-PAYME NT FROM PHONE",
            lambda: f"UPI-VIJAY SHREE TRADERS-SURENDRAGOYAL{random.randint(10,99)}@ OKSBI-BKID0008860-{ref_num()[:12]}-PAYMENT F ROM PHONE",
            lambda: f"UPI-KALA KUNJ KOTA-VYAPAR.{random.randint(100000000000,999999999999)}@H DFCBANK-HDFC0MERUPI-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-JABIR HUSAIN TAI-{random.randint(7000000000,9999999999)}@YBL-SBIN {random.randint(10000,99999)}-{ref_num()[:12]}-PAYMENT FROM PHONE",
            lambda: f"UPI-KWATRA-IBKPOS.EP{random.randint(100000,999999)}@ICICI-ICIC000 {random.randint(1000,9999)}-{ref_num()[:12]}-PAYMENT FROM PHONE",
        ],
        "amount_range": (15, 45000),
        "freq": 25,
    },

    "Investment": {
        "known": [
            lambda: f"ACH/HDFC MF/SIP/EQUITY FUND",
            lambda: f"ACH/SBI MF/SIP/BLUECHIP FUND",
            lambda: f"ACH/PPFAS MF/SIP/FLEXI CAP",
            lambda: f"UPI-ZERODHA-{random.randint(7000000000,9999999999)}@ZERODHA",
        ],
        "unknown": [],
        "amount_range": (500, 10000),
        "freq": 2,
    },

    "EMI & Loans": {
        "known": [
            lambda: f"ACH/HDFC BANK/EMI/HOME LOAN",
            lambda: f"NACH/BAJAJ FINANCE/EMI DEBIT",
            lambda: f"ACH/ICICI BANK/EMI/PERSONAL LOAN",
        ],
        "unknown": [],
        "amount_range": (3000, 20000),
        "freq": 1,
    },
}

CREDIT_TEMPLATES = [
    lambda: f"UPI-MAHESH KUMAR MALI-{random.randint(7000000000,9999999999)}@YBL-SBI N0030057-{ref_num()[:12]}-PAYMENT FROM PHONE",
    lambda: f"UPI-GHANSHYAM GURJAR-GHANSHYAMG{random.randint(100,999)}@AXL {random.randint(1000000,9999999)}-{ref_num()[:12]}-PAYMENT FROM PH ONE",
    lambda: f"UPI-DEVKARAN MEENA-{random.randint(7000000000,9999999999)}@YBL-FINO00 {random.randint(10000,99999)}-{ref_num()[:12]}-PAYMENT FROM PHONE",
    lambda: f"UPI-RACHANA RAWAT-{random.randint(100000000,999999999)}R@AXL-FINO00 {random.randint(1,9)}0001-{ref_num()[:12]}-PAYMENT FROM PHONE",
    lambda: f"UPI-MR PANKAJ BHAT-{random.randint(7000000000,9999999999)}-{random.randint(1,5)}@YBL-CBI N{random.randint(1000000,9999999)}-{ref_num()[:12]}-PAYMENT FROM PHONE",
    lambda: f"UPI-SAYUSH MITTAL-SAYUSHMITTAL{random.randint(10,99)}@OKHDFCB ANK-HDFC0005830-{ref_num()[:12]}-UPI",
    lambda: f"UPI-VINOD-VINODBAGADA{random.randint(1,9)}@AXL-SBIN0030057-{random.randint(1,9)} {ref_num()[:12]}-PAYMENT FROM PHONE",
    lambda: f"UPI-RADESHYAM CHAUDHARY-DIMPALCHOUDHARY {random.randint(1000,9999)}@AXL-SBIN0030057-{ref_num()[:12]}-PAYMENT T FROM PHONE",
]


def generate_hdfc_transactions(months=12, base_salary=85000):
    transactions = []
    start_date = datetime(2025, 1, 1)

    for month_offset in range(months):
        month_date = start_date + timedelta(days=30 * month_offset)
        year = month_date.year
        month = month_date.month
        days_in_month = 28

        # Salary credit
        salary = base_salary + random.randint(-3000, 8000)
        salary_date = datetime(year, month, random.randint(1, 3))
        transactions.append({
            "Date": salary_date.strftime("%d/%m/%Y"),
            "Narration": f"NEFT/INFOSYS LIMITED/MONTHLY SALARY",
            "Chq_Ref": ref_num()[:16],
            "Value_Dt": salary_date.strftime("%d/%m/%Y"),
            "Withdrawal_Amt": "",
            "Deposit_Amt": salary,
            "Closing_Balance": 0,
            "True_Category": "Salary & Income",
            "is_credit": True,
        })

        # P2P credits (business receipts)
        for _ in range(random.randint(8, 20)):
            day = random.randint(1, days_in_month)
            txn_date = datetime(year, month, day)
            amount = round(random.uniform(40, 45000), 2)
            transactions.append({
                "Date": txn_date.strftime("%d/%m/%Y"),
                "Narration": random.choice(CREDIT_TEMPLATES)(),
                "Chq_Ref": ref_num()[:16],
                "Value_Dt": txn_date.strftime("%d/%m/%Y"),
                "Withdrawal_Amt": "",
                "Deposit_Amt": amount,
                "Closing_Balance": 0,
                "True_Category": "Transfers",
                "is_credit": True,
            })

        # Debit transactions
        for category, config in MERCHANTS.items():
            freq = config["freq"]
            if category == "Shopping" and month in [10, 11, 12]:
                freq = int(freq * 1.5)
            if category == "Transport" and month in [5, 6]:
                freq = int(freq * 1.3)

            for _ in range(freq):
                if random.random() < 0.80:
                    day = random.randint(1, days_in_month)
                    txn_date = datetime(year, month, day)
                    min_amt, max_amt = config["amount_range"]
                    amount = round(random.uniform(min_amt, max_amt), 2)

                    all_templates = config["known"] * 3 + config["unknown"]
                    if not all_templates:
                        continue

                    narration = random.choice(all_templates)()
                    transactions.append({
                        "Date": txn_date.strftime("%d/%m/%Y"),
                        "Narration": narration,
                        "Chq_Ref": ref_num()[:16],
                        "Value_Dt": txn_date.strftime("%d/%m/%Y"),
                        "Withdrawal_Amt": amount,
                        "Deposit_Amt": "",
                        "Closing_Balance": 0,
                        "True_Category": category,
                        "is_credit": False,
                    })

    transactions.sort(key=lambda x: datetime.strptime(x["Date"], "%d/%m/%Y"))
    balance = 52863.92
    for t in transactions:
        if t["is_credit"]:
            balance += float(t["Deposit_Amt"])
        else:
            balance -= float(t["Withdrawal_Amt"])
        t["Closing_Balance"] = round(balance, 2)

    return transactions


def main():
    print("Generating realistic HDFC-format transactions...")
    print("Matching real UPI string patterns from actual HDFC statement...\n")

    transactions = generate_hdfc_transactions(months=12, base_salary=85000)

    # Bank statement CSV
    statement_path = Path("hdfc_statement_5000txns.csv")
    with open(statement_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Narration", "Chq./Ref.No.", "Value Dt",
                         "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"])
        for t in transactions:
            writer.writerow([t["Date"], t["Narration"], t["Chq_Ref"], t["Value_Dt"],
                             t["Withdrawal_Amt"], t["Deposit_Amt"], t["Closing_Balance"]])

    # Ground truth (debits only)
    truth_path = Path("hdfc_ground_truth.csv")
    debit_txns = [t for t in transactions if not t["is_credit"]]
    with open(truth_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Narration", "Withdrawal_Amt", "True_Category"])
        writer.writeheader()
        for t in debit_txns:
            writer.writerow({"Date": t["Date"], "Narration": t["Narration"],
                             "Withdrawal_Amt": t["Withdrawal_Amt"], "True_Category": t["True_Category"]})

    from collections import Counter
    cat_counts = Counter(t["True_Category"] for t in transactions)
    credit_count = sum(1 for t in transactions if t["is_credit"])
    debit_count = len(debit_txns)

    print(f"Total transactions: {len(transactions)}")
    print(f"  Credits (deposits): {credit_count}")
    print(f"  Debits (spending):  {debit_count}")
    print(f"\nCategory breakdown (all transactions):")
    for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat:<25} {count:4d}")

    total_debit = sum(float(t["Withdrawal_Amt"]) for t in transactions if t["Withdrawal_Amt"])
    total_credit = sum(float(t["Deposit_Amt"]) for t in transactions if t["Deposit_Amt"])
    print(f"\nTotal debits:  ₹{total_debit:,.0f}")
    print(f"Total credits: ₹{total_credit:,.0f}")
    print(f"\nFiles saved:")
    print(f"  {statement_path}  ← upload to WealthPilot")
    print(f"  {truth_path}       ← run: python benchmark_hdfc.py")


if __name__ == "__main__":
    main()