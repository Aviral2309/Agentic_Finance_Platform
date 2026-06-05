import csv
import random
from datetime import datetime, timedelta

# --- CONFIGURATION ---
START_DATE = datetime(2026, 1, 1)
END_DATE = datetime(2026, 5, 31)
INITIAL_BALANCE = 5450.00
OUTPUT_FILE = "synthetic_bank_statement_20_pages.csv"

# --- REALISTIC MERCHANDIST & EXPENSE MAPPING ---
CATEGORIES = {
    "Food & Dining": [
        ("Starbucks", -4.50, -12.00),
        ("UberEats", -15.00, -45.00),
        ("McDonalds", -6.00, -15.00),
        ("Whole Foods Market", -40.00, -120.00),
        ("Trader Joe's", -30.00, -90.00),
        ("Local Pizzeria", -18.00, -35.00),
        ("Subway", -7.50, -14.00),
        ("Chipotle", -11.00, -22.00)
    ],
    "Travel & Transport": [
        ("Uber/Lyft Ride", -12.50, -38.00),
        ("Shell Oil Gas", -35.00, -65.00),
        ("Delta Air Lines", -180.00, -450.00),
        ("Amtrak Train", -45.00, -120.00),
        ("City Parking Garage", -8.00, -25.00),
        ("Airbnb Booking", -120.00, -350.00)
    ],
    "Hobbies & Recreation": [
        ("Steam Games", -9.99, -59.99),
        ("Amazon - Books & Hobby", -15.00, -75.00),
        ("Local Climbing Gym", -25.00, -25.00),
        ("Guitar Center", -15.00, -150.00),
        ("Audible Subscription", -14.95, -14.95),
        ("Netflix Subscription", -15.49, -15.49),
        ("Spotify Premium", -10.99, -10.99)
    ],
    "Other/Utilities/Income": [
        ("Monthly Rent Payment", -1200.00, -1200.00),
        ("Electric Utility Bill", -60.00, -110.00),
        ("Verizon Wireless", -70.00, -95.00),
        ("Target - Miscellaneous", -15.00, -85.00),
        ("Bi-Weekly Paycheck", 2200.00, 2200.00), # Income
        ("Venmo Peer Transfer", -10.00, 45.00)     # Can be +/-
    ]
}

def generate_statement():
    current_balance = INITIAL_BALANCE
    current_date = START_DATE
    transactions = []

    print(f"Generating synthetic statement from {START_DATE.date()} to {END_DATE.date()}...")

    while current_date <= END_DATE:
        # Determine number of transactions for the day (0 to 6 to simulate busy days)
        num_tx = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[10, 20, 25, 20, 15, 7, 3])[0]
        
        day_transactions = []
        for _ in range(num_tx):
            # Pick a random category weighted towards Food and Hobbies
            cat = random.choices(
                list(CATEGORIES.keys()), 
                weights=[40, 20, 25, 15]
            )[0]
            
            merchant, min_amt, max_amt = random.choice(CATEGORIES[cat])
            
            # Generate random amount within boundaries
            if min_amt == max_amt:
                amount = min_amt
            else:
                amount = round(random.uniform(min_amt, max_amt), 2)
            
            # Logic check: Force Paychecks only on specific intervals (e.g., 1st and 15th)
            if merchant == "Bi-Weekly Paycheck":
                if current_date.day not in [1, 15]:
                    continue
            
            # Generate unique Mock Reference ID
            ref_id = f"TXN{random.randint(100000, 999999)}X{random.randint(10, 99)}"
            
            day_transactions.append({
                "Date": current_date.strftime("%Y-%m-%d"),
                "Description": merchant,
                "Category": cat,
                "Amount": amount,
                "Reference_ID": ref_id
            })

        # Sort daily transactions so income hits first (to minimize artificial overdrafts)
        day_transactions.sort(key=lambda x: x["Amount"], reverse=True)

        for tx in day_transactions:
            current_balance += tx["Amount"]
            tx["Balance"] = round(current_balance, 2)
            transactions.append(tx)
            
        current_date += timedelta(days=1)

    # Write out to CSV
    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Category", "Amount", "Balance", "Reference_ID"])
        writer.writeheader()
        writer.writerows(transactions)

    print(f"Success! Generated {len(transactions)} transactions in '{OUTPUT_FILE}'.")
    print(f"Final Account Balance: ${current_balance:,.2f}")

if __name__ == "__main__":
    generate_statement()