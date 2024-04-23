import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import os
import subprocess
import cv2
import pytesseract
import numpy as np

#Important enter path to tesseract object
pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'

def preprocess_image(image):
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply bilateral filter for smoothing while preserving edges
    gray = cv2.bilateralFilter(gray, 11, 17, 17)

    # Apply adaptive thresholding to create a binary image
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

    # Find contours in the binary image
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Create a mask for the display area
    mask = np.zeros_like(binary)
    display_contour = max(contours, key=cv2.contourArea)
    cv2.drawContours(mask, [display_contour], 0, 255, -1)

    # Apply the mask to the binary image to isolate the display area
    display_binary = cv2.bitwise_and(binary, mask)

    return display_binary

# Create the database
def create_database():
    subprocess.run(["python", "create_database.py"])

# Connect to the database
db_exists = os.path.exists('weight_progress.db')
conn = sqlite3.connect('weight_progress.db')
cursor = conn.cursor()

if not db_exists:
    create_database()

# Function to retrieve all entries from the database
def get_all_entries():
    cursor.execute('SELECT * FROM weight_measurements')
    return cursor.fetchall()

# Function to remove an entry from the database
def remove_entry(entry_id):
    cursor.execute('SELECT date FROM weight_measurements WHERE id = ?', (entry_id,))
    deleted_date = cursor.fetchone()[0]
    cursor.execute('DELETE FROM weight_measurements WHERE id = ?', (entry_id,))
    conn.commit()
    reset_ids()
    return deleted_date

def reset_ids():
    # Remove the primary key constraint
    cursor.execute('PRAGMA foreign_keys=off')
    cursor.execute('BEGIN TRANSACTION')
    cursor.execute('CREATE TEMPORARY TABLE temp_table AS SELECT * FROM weight_measurements')
    cursor.execute('DROP TABLE weight_measurements')
    cursor.execute('''
        CREATE TABLE weight_measurements (
            id INTEGER PRIMARY KEY,
            date DATE,
            fat_percentage FLOAT,
            muscle_percentage FLOAT,
            water_percentage FLOAT,
            weight FLOAT,
            age INTEGER,
            fat_mass FLOAT DEFAULT 0,
            muscle_mass FLOAT DEFAULT 0
        )
    ''')

    # Reset the index based on date
    cursor.execute('SELECT id, date FROM temp_table ORDER BY date')
    entries = cursor.fetchall()

    for new_id, (old_id, date) in enumerate(entries, start=1):
        cursor.execute('INSERT INTO weight_measurements SELECT ?, date, fat_percentage, muscle_percentage, water_percentage, weight, age, fat_mass, muscle_mass FROM temp_table WHERE id = ?', (new_id, old_id))

    cursor.execute('DROP TABLE temp_table')
    cursor.execute('COMMIT')
    conn.commit()

# Function to add a new entry to the database
def add_entry(date, fat, muscle, water, weight, age):
    cursor.execute('''
        INSERT OR REPLACE INTO weight_measurements (date, fat_percentage, muscle_percentage, water_percentage, weight, age)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, fat, muscle, water, weight, age))
    conn.commit()
    calculate_mass(date, weight, fat, muscle)

# Function to calculate muscle mass and fat mass and update the database
def calculate_mass(date, weight, fat_percentage, muscle_percentage):
    fat_mass = weight * (fat_percentage / 100)
    muscle_mass = weight * (muscle_percentage / 100)
    cursor.execute('''
        UPDATE weight_measurements
        SET fat_mass = ?, muscle_mass = ?
        WHERE date = ?
    ''', (fat_mass, muscle_mass, date))
    conn.commit()

# Streamlit app
def main():
    st.title('Weight Progress Dashboard')

    # Display all entries in a table
    entries = get_all_entries()
    if entries:
        st.subheader('All Entries')
        table_data = []
        for entry in entries:
            id_, date_, fat_percentage, muscle_percentage, water_percentage, weight, age, fat_mass, muscle_mass = entry
            fat_mass = fat_mass or '?'
            muscle_mass = muscle_mass or '?'
            table_data.append([id_, date_, fat_percentage, muscle_percentage, water_percentage, weight, age, fat_mass, muscle_mass])
        table_headers = ['ID', 'Date', 'Fat %', 'Muscle %', 'Water %', 'Weight', 'Age', 'Fat Mass', 'Muscle Mass']
        table_df = pd.DataFrame(table_data, columns=table_headers)
        st.dataframe(table_df, width=800, height=300)

        # Remove entry section
        st.subheader('Remove Entry')
        entry_id = st.number_input('Enter the ID of the entry to remove', min_value=1, step=1)
        if st.button('Remove Entry'):
            confirmation = st.warning('Are you sure you want to remove this entry?')
            if confirmation:
                deleted_date = remove_entry(entry_id)
                reset_ids()
                st.success('Entry removed successfully.')
                st.rerun()

       # Pie chart section
        st.subheader('Body Composition')
        cursor.execute('SELECT fat_percentage, muscle_percentage, water_percentage, weight FROM weight_measurements ORDER BY date DESC LIMIT 1')
        latest_entry = cursor.fetchone()
        if latest_entry:
            fat_percentage, muscle_percentage, water_percentage, weight = latest_entry

            fat_mass = weight * (fat_percentage / 100)
            muscle_mass = weight * (muscle_percentage / 100)
            water_mass = weight * (water_percentage / 100)

            labels = ['Fat Mass', 'Muscle Mass', 'Water Mass']
            values = [fat_mass, muscle_mass, water_mass]

            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
            fig.update_layout(title_text='Body Composition')
            st.plotly_chart(fig)
        else:
            st.warning('No entries found.')

        # Line graph section
        st.subheader('Progress Over Time')
        cursor.execute('SELECT date, fat_percentage, muscle_percentage, fat_mass, muscle_mass FROM weight_measurements ORDER BY date')
        data = cursor.fetchall()

        if len(data) >= 1:
            dates, fat_percentages, muscle_percentages, fat_masses, muscle_masses = zip(*data)
            progress_df = pd.DataFrame({
                'Date': dates,
                'Fat Percentage': fat_percentages,
                'Muscle Percentage': muscle_percentages,
                'Fat Mass': fat_masses,
                'Muscle Mass': muscle_masses
            })

            plot_mode = st.radio('Select Plot Mode', ['Percentage', 'Mass'])

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)

            if plot_mode == 'Mass':
                fig.add_trace(go.Scatter(x=progress_df['Date'], y=progress_df['Fat Mass'], mode='lines', name='Fat Mass'), row=1, col=1)
                fig.add_trace(go.Scatter(x=progress_df['Date'], y=progress_df['Muscle Mass'], mode='lines', name='Muscle Mass'), row=2, col=1)
                fig.update_layout(title_text='Mass Over Time', height=800, width=800, title_x=0.5)
            else:
                fig.add_trace(go.Scatter(x=progress_df['Date'], y=progress_df['Fat Percentage'], mode='lines', name='Fat Percentage'), row=1, col=1)
                fig.add_trace(go.Scatter(x=progress_df['Date'], y=progress_df['Muscle Percentage'], mode='lines', name='Muscle Percentage'), row=2, col=1)
                fig.update_layout(title_text='Percentage Over Time', height=800, width=800, title_x=0.5)

            st.plotly_chart(fig)

        else:
            st.warning('Insufficient entries to display progress over time.')

    # Add new entry section
    st.subheader('Add New Entry')
    entry_method = st.radio("Select Entry Method", ("Manual Entry", "Image Upload"))

    if entry_method == "Manual Entry":
        date = st.date_input('Date')
        fat = st.number_input('Fat Percentage', min_value=0.0, max_value=100.0, step=0.1)
        muscle = st.number_input('Muscle Percentage', min_value=0.0, max_value=100.0, step=0.1)
        water = st.number_input('Water Percentage', min_value=0.0, max_value=100.0, step=0.1)
        weight = st.number_input('Weight', min_value=0.0, step=0.1)
        age = st.number_input('Age', min_value=0, step=1)

        if st.button('Add Entry'):
            add_entry(date, fat, muscle, water, weight, age)
            reset_ids()
            st.success('Entry added successfully.')
            st.rerun()

    elif entry_method == "Image Upload":
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

        if uploaded_file is not None:
            # Read the uploaded image using OpenCV
            image = cv2.imdecode(np.fromstring(uploaded_file.read(), np.uint8), 1)

            # Preprocess the image
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

            # Apply OCR using pytesseract
            text = pytesseract.image_to_string(thresh)

            # Extract the stats from the OCR text
            lines = text.split('\n')
            print(lines)
            for line in lines:
                if 'lb' in line:
                    weight = float(line.split('lb')[0].strip())
                elif '%' in line:
                    if 'fat' in line.lower():
                        fat = float(line.split('%')[0].strip())
                    elif 'mus' in line.lower():
                        muscle = float(line.split('%')[0].strip())
                    elif 'water' in line.lower():
                        water = float(line.split('%')[0].strip())

            # Display the extracted values
            st.write("Extracted Stats:")
            st.write(f"Weight: {weight} lb")
            st.write(f"Fat: {fat}%")
            st.write(f"Muscle: {muscle}%")
            st.write(f"Water: {water}%")

            if st.button('Add Entry'):
                # Extract the date from the image filename or ask the user to input it
                date = st.date_input('Date')
                add_entry(date, fat, muscle, water, weight, age)
                st.success('Entry added successfully.')
                st.rerun()

if __name__ == '__main__':
    try:
        main()
    finally:
        conn.close()