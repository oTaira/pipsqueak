import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# Connect to the database
conn = sqlite3.connect('weight_progress.db')
cursor = conn.cursor()

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
    return deleted_date

# Function to reset ids based on date
def reset_ids():
    cursor.execute('SELECT id, date FROM weight_measurements ORDER BY date')
    entries = cursor.fetchall()
    for new_id, (old_id, date) in enumerate(entries, start=1):
        cursor.execute('UPDATE weight_measurements SET id = ? WHERE id = ?', (new_id, old_id))
    conn.commit()

# Function to add a new entry to the database
def add_entry(date, fat, muscle, water, weight, age):
    cursor.execute('''
        INSERT INTO weight_measurements (date, fat_percentage, muscle_percentage, water_percentage, weight, age)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, fat, muscle, water, weight, age))
    conn.commit()
    cursor.execute('SELECT last_insert_rowid()')
    entry_id = cursor.fetchone()[0]
    calculate_mass(entry_id, weight, fat, muscle)

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
        reset_ids()
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
                st.experimental_rerun()

       # Pie chart section
        st.subheader('Body Composition')
        cursor.execute('SELECT fat_percentage, muscle_percentage, weight FROM weight_measurements WHERE fat_mass IS NOT NULL AND muscle_mass IS NOT NULL ORDER BY date DESC LIMIT 1')
        latest_entry = cursor.fetchone()
        if latest_entry:
            fat_percentage, muscle_percentage, weight = latest_entry
            water_percentage = 100 - fat_percentage - muscle_percentage

            fat_mass = weight * (fat_percentage / 100)
            muscle_mass = weight * (muscle_percentage / 100)
            water_mass = weight * (water_percentage / 100)

            fat_mass_without_water = fat_mass * (1 - water_percentage / 100)
            muscle_mass_without_water = muscle_mass * (1 - water_percentage / 100)

            labels = ['Fat Mass (without water)', 'Muscle Mass (without water)', 'Water Mass']
            values = [fat_mass_without_water, muscle_mass_without_water, water_mass]

            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
            fig.update_layout(title_text='Body Composition')
            st.plotly_chart(fig)
        else:
            st.warning('No entries found with fat mass and muscle mass data.')

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

if __name__ == '__main__':
    try:
        main()
    finally:
        conn.close()