from flask import Flask, request, jsonify
import requests
from apify_client import ApifyClient
import threading
import os
from datetime import datetime

app = Flask(__name__)

Insta_Token = "apify_api_qI26br3ucdk1JtCdJozAVBEbBFhfqM3M5E3N"
ZAPIER_WEBHOOK_URL = os.getenv("ZAPIER_WEBHOOK_URL")

print("ZAPIER URL: ", ZAPIER_WEBHOOK_URL)


def calculate_reels_count(timeframe):
    """
    Calculate the number of reels to fetch based on the timeframe.
    """
    now = datetime.now()
    try:
        timeframe_date = datetime.strptime(timeframe, "%d/%m/%Y")
        delta = (now.year - timeframe_date.year) * 12 + (now.month - timeframe_date.month)

        if delta <= 1:
            return 100
        elif delta == 2:
            return 200
        elif delta == 3:
            return 300
        else:
            return 700
    except ValueError:
        print("Invalid timeframe format. Expected format is 'day/month/year'.")
        return None


def run_insta_scraper(reel_username, reels_count):
    client = ApifyClient(Insta_Token)

    # Set up the input for the actor run
    run_input = {
        "reels_count": reels_count,
        "tags": [reel_username]
    }

    try:
        # Run the actor and wait for it to finish
        run = client.actor("hpix~ig-reels-scraper").call(run_input=run_input)

        # Fetch and return the dataset items from the run
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return items  # This is the dataset with top reels
    except Exception as e:
        print("Error running Insta Scraper:", str(e))
        return None


def format_response_for_zapier(data, list_name):
    reels = []
    for item in data:
        reels.append({
            "link": f"https://www.instagram.com/reel/{item.get('code', '')}/",
            "viewcount": item.get("play_count", 0)
        })

    # Sort by view count
    sorted_reels = sorted(reels, key=lambda x: x["viewcount"], reverse=True)

    # Prepare formatted response in the specified JSON format
    formatted_response = {
        "ListName": list_name,
        "ReelLinks": [reel["link"] for reel in sorted_reels],
        "ViewCounts": [reel["viewcount"] for reel in sorted_reels]
    }

    return formatted_response


def process_reels_in_background(reel_username, list_name, timeframe):
    reels_count = calculate_reels_count(timeframe)
    if reels_count is None:
        print("Invalid timeframe provided. Skipping process.")
        return

    result = run_insta_scraper(reel_username, reels_count)
    if result:
        formatted_result = format_response_for_zapier(result, list_name)
        zapier_response = requests.post(ZAPIER_WEBHOOK_URL, json=formatted_result)
        print(formatted_result)
        if zapier_response.status_code == 200:
            print("Data sent to Zapier successfully.")
        else:
            print("Error sending data to Zapier:", zapier_response.status_code, zapier_response.text)


@app.route('/scrape_reels', methods=['POST'])
def scrape_reels():
    data = request.json
    reel_username = data.get("reel_username")
    list_name = data.get("listName")
    timeframe = data.get("timeframe")  # Expected in "day/month/year" format

    if not reel_username or not list_name or not timeframe:
        return jsonify({"error": "Missing 'reel_username', 'listName', or 'timeframe'"}), 400

    # Start background thread for processing
    threading.Thread(target=process_reels_in_background, args=(reel_username, list_name, timeframe)).start()

    # Immediately respond with 200 OK
    return jsonify({"status": "Processing started"}), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
