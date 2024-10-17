now integrate this from flask import Flask, request, jsonify
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client['mahakal_jackpot']
collection = db['time_series_data']

# Define columns for 30-minute intervals
time_columns = [
    "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
    "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM", "06:00 PM", "06:30 PM",
    "07:00 PM", "07:30 PM", "08:00 PM", "08:30 PM", "09:00 PM", "09:30 PM",
    "10:00 PM", "10:30 PM", "11:00 PM"
]

@app.route('/submit_data', methods=['POST'])
def submit_data():
    # Get the data from the request
    data = request.json
    number = data.get('number')

    # Validate that the number is an integer and in the range 0-99
    if not isinstance(number, int) or number < 0 or number > 99:
        return jsonify({"error": "Number must be an integer between 0 and 99!"}), 400

    current_time = datetime.now()
    hour = current_time.strftime('%I:%M %p')

    # Check if the current time is within the allowed range (10 AM - 11 PM)
    if current_time.hour < 10 or current_time.hour > 22:  # 10 AM is 10 and 11 PM is 22 in 24-hour format
        return jsonify({"error": "Out of time! Please submit between 10 AM and 11 PM."}), 400

    # Retrieve the current date to update or create a record for today
    date_str = current_time.strftime('%d-%m-%Y')

    # Check if data for today already exists
    existing_record = collection.find_one({"Date": date_str})

    if existing_record:
        # Check if the current time slot already has a value
        if hour in time_columns:
            if existing_record.get(hour) is not None:
                return jsonify({"error": "Number already selected, cannot update!"}), 400
            
            # Update the specific time slot with the entered number
            collection.update_one(
                {"Date": date_str},
                {"$set": {hour: number}}
            )
        else:
            return jsonify({"error": "Invalid time slot!"}), 400
    else:
        # Create a new record for today with the entered number
        new_record = {column: None for column in time_columns}
        new_record['Date'] = date_str
        if hour in time_columns:
            new_record[hour] = number
        collection.insert_one(new_record)

    return jsonify({"message": "Data submitted successfully!"})



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

in this frontend remove static data all will come dynamiclly from above apis       <div class="play-card-body">
                      <span class="add-more-text">All Selected</span>
                      <div class="table-responsive">
                        <table class="table text-center text-uppercase table-bordered table22">
                          <thead>
                            
                          </tbody>
                        </table>
                      </div>
                    </div>

                    api data - 
                    http://127.0.0.1:5000/get_data
                    [
    {
        "01:00 PM": "wait...",
        "01:30 PM": "wait...",
        "02:00 PM": "wait...",
        "02:30 PM": "wait...",
        "03:00 PM": "wait...",
        "03:30 PM": "wait...",
        "04:00 PM": "wait...",
        "04:30 PM": "wait...",
        "05:00 PM": "wait...",
        "05:30 PM": "wait...",
        "06:00 PM": "wait...",
        "06:30 PM": "wait...",
        "07:00 PM": "wait...",
        "07:30 PM": "wait...",
        "08:00 PM": "wait...",
        "08:30 PM": "wait...",
        "09:00 PM": "wait...",
        "09:30 PM": "wait...",
        "10:00 AM": "wait...",
        "10:00 PM": "wait...",
        "10:30 AM": "wait...",
        "10:30 PM": "wait...",
        "11:00 AM": "wait...",
        "11:00 PM": 50,
        "11:30 AM": "wait...",
        "12:00 PM": "wait...",
        "12:30 PM": "wait...",
        "Date": "15-10-2024"
    }
]