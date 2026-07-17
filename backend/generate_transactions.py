"""
Generate realistic Indian bank transaction data for WealthPilot testing.
Produces 800-1000 transactions across 12 months with:
- Messy UPI strings (the kind real banks produce)
- Multiple merchant categories
- Realistic spending patterns for a salaried Indian professional
- Salary credits, EMIs, UPI payments, ATM withdrawals, online transfers

Run from backend/ folder:
python generate_transactions.py
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ── Realistic UPI merchant strings (messy, like real bank statements) ──
MERCHANTS = {
    "Food & Dining": [
        "UPI/SWIGGY/9876543210/SWIGGY*FOOD",
        "UPI/ZOMATO/8765432109/ZOMATO*ORDER",
        "UPI/P2A/DOMINOS PIZZA INDIA/FOOD",
        "POS/MCDONALDS INDIA/BANGALORE",
        "UPI/BLINKIT/7654321098/QUICK GROCERY",
        "UPI/P2A/SARAVANA BHAVAN/RESTAURANT",
        "NEFT/STARBUCKS INDIA/COFFEE",
        "POS/KFC INDIA/BANGALORE/DEBIT",
        "UPI/SUBWAY/6543210987/SANDWICH",
        "UPI/P2A/LOCAL DHABA/FOOD PAYMENT",
        "POS/CHAAYOS/INDIRANAGAR/DEBIT",
        "UPI/BIRYANI BLUES/5432109876",
    ],
    "Groceries": [
        "UPI/BIGBASKET/4321098765/GROCERY",
        "UPI/ZEPTO/3210987654/INSTANT DELIVERY",
        "UPI/BLINKIT/2109876543/GROCERY ORDER",
        "POS/DMART/BANGALORE/GROCERY",
        "UPI/RELIANCE SMART/1098765432",
        "POS/MORE SUPERMARKET/ELECTRONIC CITY",
        "UPI/GROFERS/0987654321/GROCERY",
        "POS/SPAR HYPERMARKET/KORAMANGALA",
        "UPI/P2A/NILGIRIS/DAIRY PRODUCTS",
    ],
    "Transport": [
        "UPI/UBER/9876512340/RIDE",
        "UPI/OLA CABS/8765401239/AUTO",
        "UPI/RAPIDO/7654390128/BIKE TAXI",
        "IRCTC/TKT/BLR-MAS/2A/RAIL BOOKING",
        "UPI/P2A/BMTC/BUS PASS RENEWAL",
        "POS/PETRO BUNK/HPCL/FUEL",
        "UPI/FASTAG/NHAI/TOLL PAYMENT",
        "UPI/IXIGO/6543012780/TRAIN TICKET",
        "UPI/MAKEMYTRIP/5432901670/FLIGHT BLR DEL",
        "UPI/REDBUS/4321890560/BUS TICKET",
    ],
    "Shopping": [
        "UPI/AMAZON PAY/IN/ORDER PAYMENT",
        "UPI/FLIPKART/3210789450/PURCHASE",
        "UPI/MYNTRA/2109678340/FASHION",
        "UPI/MEESHO/1098567230/ORDER",
        "POS/RELIANCE DIGITAL/KORAMANGALA/GADGET",
        "UPI/NYKAA/0987456120/BEAUTY",
        "UPI/AJIO/9876345010/CLOTHING",
        "POS/LIFESTYLE/FORUM MALL/SHOPPING",
        "UPI/CROMA/8765234900/ELECTRONICS",
        "UPI/SNAPDEAL/7654123790",
    ],
    "Bills & Utilities": [
        "BBPS/BESCOM/ELECTRICITY/BILL PAY",
        "BBPS/AIRTEL/MOBILE RECHARGE/PREPAID",
        "BBPS/JIO/RECHARGE/4G PLAN",
        "UPI/TATAPLAY/DTH RECHARGE",
        "BBPS/BWSSB/WATER BILL/PAYMENT",
        "UPI/GASPAY/IGL/PIPED GAS",
        "ACH/HATHWAY/BROADBAND/MONTHLY",
        "BBPS/BESCOM/B2/ELECTRICITY BILL",
        "UPI/VODAFONE IDEA/MOBILE BILL",
    ],
    "Healthcare": [
        "UPI/APOLLO PHARMACY/9876100001/MEDICINES",
        "UPI/1MG/8765200002/MEDICINE ORDER",
        "UPI/NETMEDS/7654300003/PHARMA",
        "POS/COLUMBIA ASIA/HOSPITAL/CONSULTATION",
        "UPI/PRACTO/6543400004/DR APPOINTMENT",
        "POS/MAX HEALTHCARE/PATHOLOGY/LAB TEST",
        "UPI/MEDPLUS/5432500005/PHARMACY",
    ],
    "Entertainment": [
        "UPI/BOOKMYSHOW/4321600006/MOVIE TICKETS",
        "UPI/NETFLIX/3210700007/SUBSCRIPTION",
        "UPI/SPOTIFY/2109800008/PREMIUM",
        "UPI/HOTSTAR/1098900009/SUBSCRIPTION",
        "POS/PVR CINEMAS/FORUM MALL/MOVIES",
        "UPI/AMAZON PRIME/0988000010/MEMBERSHIP",
        "UPI/INOX/9877100011/MOVIE BOOKING",
        "UPI/YOUTUBE PREMIUM/8766200012",
    ],
    "Investment": [
        "UPI/ZERODHA/7655300013/EQUITY PURCHASE",
        "ACH/HDFC MF/SIP/EQUITY FUND",
        "ACH/SBI MF/SIP/BLUECHIP FUND",
        "UPI/GROWW/6544400014/MF INVESTMENT",
        "ACH/PPFAS MF/SIP/FLEXI CAP",
        "UPI/KUVERA/5433500015/MUTUAL FUND",
        "ACH/AXIS MF/SIP/SMALL CAP FUND",
        "UPI/COIN ZERODHA/4322600016/MF SIP",
    ],
    "EMI & Loans": [
        "ACH/HDFC BANK/EMI/HOME LOAN",
        "ACH/ICICI BANK/EMI/PERSONAL LOAN",
        "ACH/BAJAJ FINANCE/EMI/CONSUMER LOAN",
        "ACH/HDFC BANK/EMI/CAR LOAN",
        "NACH/TATA CAPITAL/EMI DEBIT",
        "ACH/SBI/EDUCATION LOAN/EMI",
    ],
    "Travel": [
        "UPI/MAKEMYTRIP/3211700017/HOTEL BOOKING",
        "UPI/OYO/2100800018/HOTEL STAY",
        "UPI/GOIBIBO/1099900019/FLIGHT TICKET",
        "POS/TAJ HOTELS/BANGALORE/STAY",
        "UPI/AIRBNB/0989000020/ACCOMMODATION",
        "UPI/YATRA/9878100021/HOLIDAY PACKAGE",
    ],
    "Education": [
        "UPI/UDEMY/8767200022/COURSE PURCHASE",
        "UPI/COURSERA/7656300023/SUBSCRIPTION",
        "UPI/UNACADEMY/6545400024/SUBSCRIPTION",
        "ACH/BYJU/5434500025/EMI INSTALLMENT",
        "UPI/LEETCODE/4323600026/PREMIUM",
    ],
    "ATM Withdrawal": [
        "ATM/SBI ATM/KORAMANGALA/CASH",
        "ATM/HDFC BANK/INDIRANAGAR/WITHDRAWAL",
        "ATM/ICICI BANK/MG ROAD/CASH WITHDRAWAL",
        "ATM/AXIS BANK/BTM LAYOUT/CASH",
    ],
    "Transfers": [
        "UPI/P2P/TRANSFER/FAMILY",
        "NEFT/TRANSFER/RENT PAYMENT",
        "UPI/P2P/SPLIT/FRIENDS",
        "IMPS/TRANSFER/PERSONAL",
    ],
}

INCOME_SOURCES = [
    "NEFT/INFOSYS BPO/SALARY/OCTOBER",
    "NEFT/INFOSYS LIMITED/MONTHLY SALARY",
    "SALARY/CREDIT/INFOSYS/NET PAY",
    "NEFT/EMPLOYER/SALARY CREDIT",
]

SPENDING_PROFILE = {
    "Food & Dining":    {"min": 300,   "max": 800,   "freq_per_month": 12},
    "Groceries":        {"min": 800,   "max": 3000,  "freq_per_month": 5},
    "Transport":        {"min": 80,    "max": 1500,  "freq_per_month": 14},
    "Shopping":         {"min": 500,   "max": 8000,  "freq_per_month": 4},
    "Bills & Utilities":{"min": 200,   "max": 2500,  "freq_per_month": 4},
    "Healthcare":       {"min": 200,   "max": 3000,  "freq_per_month": 2},
    "Entertainment":    {"min": 149,   "max": 800,   "freq_per_month": 5},
    "Investment":       {"min": 2000,  "max": 10000, "freq_per_month": 3},
    "EMI & Loans":      {"min": 8000,  "max": 15000, "freq_per_month": 1},
    "Travel":           {"min": 2000,  "max": 12000, "freq_per_month": 1},
    "Education":        {"min": 500,   "max": 3000,  "freq_per_month": 1},
    "ATM Withdrawal":   {"min": 2000,  "max": 5000,  "freq_per_month": 2},
    "Transfers":        {"min": 3000,  "max": 20000, "freq_per_month": 2},
}

def generate_transactions(months=12, base_salary=85000):
    transactions = []
    start_date = datetime(2025, 1, 1)

    for month_offset in range(months):
        month_date = start_date + timedelta(days=30 * month_offset)
        year = month_date.year
        month = month_date.month

        # Salary credit on 1st or 2nd of month
        salary = base_salary + random.randint(-2000, 5000)
        salary_date = datetime(year, month, random.randint(1, 3))
        transactions.append({
            "Date": salary_date.strftime("%d/%m/%Y"),
            "Description": random.choice(INCOME_SOURCES),
            "Debit": "",
            "Credit": salary,
            "Balance": 0,
            "True_Category": "Salary & Income",
        })

        # Interest credit mid-month
        if random.random() > 0.5:
            interest_date = datetime(year, month, random.randint(14, 18))
            transactions.append({
                "Date": interest_date.strftime("%d/%m/%Y"),
                "Description": "INTEREST CREDIT/SAVINGS ACCOUNT",
                "Debit": "",
                "Credit": random.randint(100, 500),
                "Balance": 0,
                "True_Category": "Salary & Income",
            })

        # Spending transactions
        for category, profile in SPENDING_PROFILE.items():
            freq = profile["freq_per_month"]
            # Add seasonality — more travel in Dec/Jan, more shopping in Oct/Nov
            if category == "Travel" and month in [12, 1, 5]:
                freq += 1
            if category == "Shopping" and month in [10, 11]:
                freq += 2

            for _ in range(freq):
                if random.random() < 0.85:  # 85% chance of each transaction occurring
                    day = random.randint(1, 28)
                    txn_date = datetime(year, month, day)
                    amount = round(random.uniform(profile["min"], profile["max"]), 2)
                    merchant = random.choice(MERCHANTS.get(category, ["UNKNOWN MERCHANT"]))

                    transactions.append({
                        "Date": txn_date.strftime("%d/%m/%Y"),
                        "Description": merchant,
                        "Debit": amount,
                        "Credit": "",
                        "Balance": 0,
                        "True_Category": category,
                    })

    # Sort by date
    transactions.sort(key=lambda x: datetime.strptime(x["Date"], "%d/%m/%Y"))

    # Add running balance
    balance = 45000
    for t in transactions:
        if t["Credit"]:
            balance += float(t["Credit"])
        else:
            balance -= float(t["Debit"])
        t["Balance"] = round(balance, 2)

    return transactions


def main():
    print("Generating 12-month transaction dataset...")
    transactions = generate_transactions(months=12, base_salary=85000)

    # Save as CSV (for upload to WealthPilot)
    output_path = Path("realistic_bank_statement_12months.csv")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
        writer.writeheader()
        for t in transactions:
            writer.writerow({k: v for k, v in t.items() if k != "True_Category"})

    print(f"Saved: {output_path}")
    print(f"Total transactions: {len(transactions)}")

    # Save ground truth (for accuracy measurement)
    truth_path = Path("ground_truth_labels.csv")
    with open(truth_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "True_Category"])
        writer.writeheader()
        for t in transactions:
            if t["Debit"]:
                writer.writerow({
                    "Date": t["Date"],
                    "Description": t["Description"],
                    "Debit": t["Debit"],
                    "True_Category": t["True_Category"],
                })

    print(f"Saved ground truth: {truth_path}")

    # Print summary
    from collections import Counter
    categories = Counter(t["True_Category"] for t in transactions if t["Debit"])
    print("\nTransaction breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

    debit_total = sum(float(t["Debit"]) for t in transactions if t["Debit"])
    credit_total = sum(float(t["Credit"]) for t in transactions if t["Credit"])
    print(f"\nTotal debit: ₹{debit_total:,.0f}")
    print(f"Total credit: ₹{credit_total:,.0f}")
    print(f"Net: ₹{credit_total - debit_total:,.0f}")


if __name__ == "__main__":
    main()
