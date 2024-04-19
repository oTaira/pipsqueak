import sqlite3
import argparse
from datetime import datetime

parser = argparse.ArgumentParser(description='Weight Progress Database Manager')
parser.add_argument('--action', required=True, choices=['add', 'remove', 'retrieve'], help='Action to perform')
parser.add_argument('--date', help='Date of the measurement (YYYY-MM-DD)')
parser.add_argument('--fat', type=float, help='Fat percentage')
parser.add_argument('--muscle', type=float, help='Muscle percentage')
parser.add_argument('--water', type=float, help='Water percentage')
parser.add_argument('--weight', type=float, help='Weight')
parser.add_argument('--age', type=int, help='Age')
parser.add_argument('--id', type=int, help='ID of the entry to remove')

args = parser.parse_args()

conn = sqlite3.connect('weight_progress.db')
cursor = conn.cursor()

try:
    if args.action == 'add':
        if not all([args.date, args.fat, args.muscle, args.water, args.weight, args.age]):
            print("Please provide all the required arguments for adding an entry.")
        else:
            date = datetime.strptime(args.date, '%Y-%m-%d').date()
            cursor.execute('''
                INSERT INTO weight_measurements (date, fat_percentage, muscle_percentage, water_percentage, weight, age)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date, args.fat, args.muscle, args.water, args.weight, args.age))
            conn.commit()
            print("Entry added successfully.")

    elif args.action == 'remove':
        if not args.id:
            print("Please provide the ID of the entry to remove.")
        else:
            cursor.execute('DELETE FROM weight_measurements WHERE id = ?', (args.id,))
            conn.commit()
            print("Entry removed successfully.")

    elif args.action == 'retrieve':
        cursor.execute('SELECT * FROM weight_measurements')
        entries = cursor.fetchall()
        if entries:
            print("ID | Date | Fat % | Muscle % | Water % | Weight | Age")
            print("-" * 60)
            for entry in entries:
                print(f"{entry[0]} | {entry[1]} | {entry[2]} | {entry[3]} | {entry[4]} | {entry[5]} | {entry[6]}")
        else:
            print("No entries found.")
    conn.close()
finally:
    conn.close()