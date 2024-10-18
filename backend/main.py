from flask import Flask, request, jsonify
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from flask_cors import CORS  # Import CORS
from datetime import datetime,timedelta
import pytz
# Initialize Flask app
app = Flask(__name__)
CORS(app)  # This will allow all domains to access your API

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client['mahakal_jackpot']
collection = db['time_series_data']
user_collection = db['users']
multiple_numbers_collection = db['multiple_numbers']

# Define columns for 30-minute intervals
time_columns = [
    "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
    "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM", "06:00 PM", "06:30 PM",
    "07:00 PM", "07:30 PM", "08:00 PM", "08:30 PM", "09:00 PM", "09:30 PM",
    "10:00 PM", "10:30 PM", "11:00 PM"
]


@app.route('/login', methods=['POST'])
def login():
    # Get the data from the request
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Check if username and password are provided
    if not username or not password:
        return jsonify({"error": "Username and password are required!"}), 400

    # Check for the user in the MongoDB collection
    user = user_collection.find_one({"username": username, "password": password})

    if user:
        return jsonify({"message": "Login successful!"}), 200
    else:
        return jsonify({"error": "Invalid username or password!"}), 401

def round_time_to_nearest_slot(current_time):
    # Get the current minute
    minute = current_time.minute
    # Round to the nearest 30 minutes
    if minute < 15:
        minute = 0
    elif minute < 45:
        minute = 30
    else:
        # Handle the rounding to the next hour
        current_time += timedelta(hours=1)
        minute = 0

    # Special case for early morning (round 9:46 AM - 9:59 AM to 10:00 AM)
    if current_time.hour == 9 and current_time.minute < 46:
        return current_time.replace(hour=10, minute=0, second=0, microsecond=0)

    # Return the rounded time
    return current_time.replace(minute=minute, second=0, microsecond=0)

@app.route('/submit_data', methods=['POST'])
def submit_data():
    # Get the data from the request
    data = request.json
    number = data.get('number')

    # Validate that the number is an integer and in the range 0-99
    if not isinstance(number, int) or number < 0 or number > 99:
        return jsonify({"error": "Number must be an integer between 0 and 99!"}), 400

    # Format the number as a two-digit string (e.g., 01, 05, 12)
    formatted_number = f"{number:02d}"

    # Set the timezone to your local timezone
    local_tz = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(local_tz)

    # Check if the current time is within the allowed range (9:46 AM - 11:14 PM)
    if (current_time.hour == 9 and current_time.minute < 46) or (current_time.hour == 23 and current_time.minute >= 15):
        return jsonify({"error": "Out of time! Please submit between 9:46 AM and 11:14 PM."}), 400

    # Round the current time to the nearest valid time slot
    rounded_time = round_time_to_nearest_slot(current_time)

    # Retrieve the current date to update or create a record for today
    date_str = rounded_time.strftime('%d-%m-%Y')

    # Get the hour in a format that matches your time columns (e.g., "10:00 AM", "11:00 AM")
    hour = rounded_time.strftime('%I:%M %p')

    # Debugging print statements
    print(f"Rounded time: {hour}")
    print(f"Available time slots: {time_columns}")

    # Check if data for today already exists
    existing_record = collection.find_one({"Date": date_str})

    if existing_record:
        # Check if the current time slot already has a value
        if hour in time_columns:  # Ensure time_columns contain values like '10:00 AM', '11:00 AM', etc.
            if existing_record.get(hour) is not None:
                return jsonify({"error": "Number already selected, cannot update!"}), 400
            
            # Update the specific time slot with the entered number
            collection.update_one(
                {"Date": date_str},
                {"$set": {hour: formatted_number}}
            )
        else:
            return jsonify({"error": "Invalid time slot!"}), 400
    else:
        # Create a new record for today with the entered number
        new_record = {column: None for column in time_columns}  # Ensure time_columns match format
        new_record['Date'] = date_str
        if hour in time_columns:
            new_record[hour] = formatted_number
        collection.insert_one(new_record)

    return jsonify({"message": "Data submitted successfully!"})

@app.route('/latest_number', methods=['GET'])
def latest_number():
    # Fetch the latest record from the MongoDB collection
    latest_record = collection.find().sort([("Date", -1)]).limit(1)  # Get the most recent record
    latest_record = list(latest_record)  # Convert cursor to list

    if latest_record:
        latest_record = latest_record[0]  # Get the latest record from the list

        # Initialize variables for latest value, draw date, and draw time
        latest_value = None
        draw_date = latest_record["Date"]
        draw_time = None
        
        # Iterate through time_columns to find the most recent value
        for column in reversed(time_columns):  # Start from the last time slot
            if column in latest_record and latest_record[column] is not None:
                latest_value = latest_record[column]
                draw_time = column  # Store the corresponding time
                break  # Exit loop once found

        if latest_value is not None:
            return jsonify({
                "latest_value": latest_value,
                "draw_date": draw_date,
                "draw_time": draw_time  # Include the draw time
            })

        return jsonify({"latest_value": "Loading..."})  # If no values found
    else:
        return jsonify({"error": "No records found."}), 404


@app.route('/submit_multiple_numbers', methods=['POST'])
def submit_multiple_numbers():
    # Get the data from the request
    data = request.json
    numbers = data.get('numbers')

    # Check if 'numbers' is provided and is a comma-separated string
    if not numbers:
        return jsonify({"error": "Numbers must be provided in a comma-separated format!"}), 400

    # Split the numbers by comma and validate each one
    numbers_list = numbers.split(',')
    
    # Ensure we have exactly 10 numbers
    if len(numbers_list) != 10:
        return jsonify({"error": "You must provide exactly 10 numbers!"}), 400

    formatted_numbers = []
    for number in numbers_list:
        # Try to convert each number to an integer and check if it's in the valid range
        try:
            num = int(number.strip())
            if num < 0 or num > 99:
                return jsonify({"error": f"Number {num} is out of range! Must be between 00 and 99."}), 400
            formatted_numbers.append(f"{num:02d}")  # Format as two-digit string
        except ValueError:
            return jsonify({"error": f"Invalid number '{number}'! Numbers must be integers."}), 400

    # Define the entry to update or insert
    entry = {
        "numbers": formatted_numbers,
        "submitted_at": datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')
    }

    # Update the existing record or insert a new one if it doesn't exist
    result = multiple_numbers_collection.update_one(
        {},  # This will target the first document in the collection
        {"$set": entry},  # Update with the new entry
        upsert=True  # Create a new document if no document matches
    )

    if result.modified_count > 0:
        return jsonify({"message": "Numbers updated successfully!", "submitted_numbers": formatted_numbers})
    else:
        return jsonify({"message": "Numbers inserted successfully!", "submitted_numbers": formatted_numbers})

@app.route('/latest_dates', methods=['GET'])
def latest_dates():
    # Fetch the latest two records from the time_series_data collection
    latest_records = list(collection.find({}, {"_id": 0}).sort([("Date", -1)]).limit(2))

    if len(latest_records) == 0:
        return jsonify({"error": "No records found."}), 404

    # Prepare the response to return the latest and second latest entries
    response = {
        "latest_date": latest_records[0],
        "second_latest_date": latest_records[1] if len(latest_records) > 1 else None
    }

    return jsonify(response)

@app.route('/latest36jodidata', methods=['GET'])
def latest_36_jodi_data():
    # Fetch the last 36 records from the multiple_numbers_collection
    latest_records = list(multiple_numbers_collection.find().sort([("submitted_at", -1)]).limit(36))  # Sort by submission time

    if latest_records:
        # Remove the MongoDB `_id` field from each record
        for record in latest_records:
            record.pop("_id", None)
        return jsonify(latest_records)  # Return the latest records
    else:
        return jsonify({"error": "No records found."}), 404


@app.route('/get_data', methods=['GET'])
def get_data():
    # Fetch all records from the MongoDB collection
    data = list(collection.find({}, {"_id": 0}))
    
    # Iterate over each record to replace None values with "wait..."
    for record in data:
        for column in time_columns:
            if record.get(column) is None:
                record[column] = "wait..."
    
    # Return the modified data as JSON
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)
