import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px

# Connect to the database
conn = sqlite3.connect('weight_progress.db')
cursor = conn.cursor()

# Function to retrieve all entries from the database
def get_all_entries():
    cursor.execute('SELECT * FROM weight_measurements')
    return cursor.fetchall()

# Function to remove an entry from the database
def remove_entry(entry_id):
    cursor.execute('DELETE FROM weight_measurements WHERE id = ?', (entry_id,))
    conn.commit()

# Function to add a new entry to the database
def add_entry(date, fat, muscle, water, weight, age):
    cursor.execute('''
        INSERT INTO weight_measurements (date, fat_percentage, muscle_percentage, water_percentage, weight, age)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, fat, muscle, water, weight, age))
    conn.commit()

# Function to calculate muscle mass and fat mass and update the database
def calculate_mass(entry_id, weight, fat_percentage, muscle_percentage):
    fat_mass = weight * (fat_percentage / 100)
    muscle_mass = weight * (muscle_percentage / 100)
    cursor.execute('''
        UPDATE weight_measurements
        SET fat_mass = ?, muscle_mass = ?
        WHERE id = ?
    ''', (fat_mass, muscle_mass, entry_id))
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
            calculate_mass(entry[0], entry[5], entry[2], entry[3])
            table_data.append([entry[0], entry[1], entry[2], entry[3], entry[4], entry[5], entry[6]])
        table_headers = ['ID', 'Date', 'Fat %', 'Muscle %', 'Water %', 'Weight', 'Age']
        table_df = pd.DataFrame(table_data, columns=table_headers)
        st.dataframe(table_df, width=800, height=300)

        # Remove entry section
        st.subheader('Remove Entry')
        entry_id = st.number_input('Enter the ID of the entry to remove', min_value=1, step=1)
        if st.button('Remove Entry'):
            confirmation = st.warning('Are you sure you want to remove this entry?')
            if confirmation:
                remove_entry(entry_id)
                st.success('Entry removed successfully.')
                st.experimental_rerun()

        # Pie chart section
        st.subheader('Body Composition')
        cursor.execute('SELECT fat_mass, muscle_mass FROM weight_measurements WHERE fat_mass IS NOT NULL AND muscle_mass IS NOT NULL ORDER BY date DESC LIMIT 1')
        latest_entry = cursor.fetchone()
        if latest_entry:
            fat_mass, muscle_mass = latest_entry
            labels = ['Fat Mass', 'Muscle Mass']
            values = [fat_mass, muscle_mass]
            fig = px.pie(values=values, names=labels, title='Body Composition')
            st.plotly_chart(fig)
        else:
            st.warning('No entries found with fat mass and muscle mass data.')

        # Line graph section
        st.subheader('Progress Over Time')
        cursor.execute('SELECT date, fat_percentage, muscle_percentage FROM weight_measurements ORDER BY date')

        data = cursor.fetchall()
        if len(data) > 1:
            dates, fat_percentages, muscle_percentages = zip(*data)
            progress_df = pd.DataFrame({
                'Date': dates,
                'Fat Percentage': fat_percentages,
                'Muscle Percentage': muscle_percentages
            })
            fig = px.line(progress_df, x='Date', y=['Fat Percentage', 'Muscle Percentage'], title='Progress Over Time')
            st.plotly_chart(fig)
        else:
            st.warning('Insufficient entries to display progress over time.')

    # Add new entry section
    st.subheader('Add New Entry')
    date = st.date_input('Date')
    fat = st.number_input('Fat Percentage', min_value=0.0, max_value=100.0, step=0.1)
    muscle = st.number_input('Muscle Percentage', min_value=0.0, max_value=100.0, step=0.1)
    water = st.number_input('Water Percentage', min_value=0.0, max_value=100.0, step=0.1)
    weight = st.number_input('Weight', min_value=0.0, step=0.1)
    age = st.number_input('Age', min_value=0, step=1)

    if st.button('Add Entry'):
        add_entry(date, fat, muscle, water, weight, age)
        st.success('Entry added successfully.')
        st.experimental_rerun()

if __name__ == '__main__':
    try:
        main()
    finally:
        conn.close()