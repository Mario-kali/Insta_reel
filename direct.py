from flask import Flask, request, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import requests
import json
from id import get_user_id_from_username

app = Flask(__name__)

# Global variable for the driver, initialized once
driver = None
driver_initialized = False

def initialize_driver():
    global driver, driver_initialized
    if not driver_initialized:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument(f'--proxy-server=5.161.202.98:823')
        driver = uc.Chrome(options=chrome_options)
        driver_initialized = True

def get_reels_data(reel_username, target_reel_count=100):
    try:
        reels_url = "https://www.instagram.com/api/v1/clips/user/"
        driver.get(f"https://www.instagram.com/{reel_username}/reels/")
        time.sleep(5)

        # Initialize session and add cookies
        cookies = driver.get_cookies()
        session = requests.Session()
        csrf_token = None
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])
            if cookie['name'] == 'csrftoken':
                csrf_token = cookie['value']  # Retrieve CSRF token

        if not csrf_token:
            print("CSRF token not found in cookies")
            return None

        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded",
            "priority": "u=1, i",
            "sec-ch-prefers-color-scheme": "dark",
            "sec-ch-ua": "\"Chromium\";v=\"130\", \"Google Chrome\";v=\"130\", \"Not?A_Brand\";v=\"99\"",
            "sec-ch-ua-full-version-list": "\"Chromium\";v=\"130.0.6723.92\", \"Google Chrome\";v=\"130.0.6723.92\", \"Not?A_Brand\";v=\"99.0.0.0\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": "\"\"",
            "sec-ch-ua-platform": "\"macOS\"",
            "sec-ch-ua-platform-version": "\"15.1.0\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-asbd-id": "129477",
            "x-csrftoken": csrf_token,  # Use the dynamically retrieved CSRF token
            "x-ig-app-id": "936619743392459",
            "x-ig-www-claim": "0",
            "x-instagram-ajax": "1017905023",
            "x-requested-with": "XMLHttpRequest"
        }

        max_id = None  # Initialize max_id for pagination
        reels = []
        user_id = get_user_id_from_username(reel_username)

        while len(reels) < target_reel_count:
            # Update the body with max_id for pagination if it's available
            body = {
                "include_feed_video": "true",
                "page_size": "12",
                "target_user_id": user_id
            }
            if max_id:
                body["max_id"] = max_id

            response = session.post(reels_url, headers=headers, data=body)

            if response.status_code == 200:
                reels_data = response.json()
                items = reels_data.get("items", [])
                paging_info = reels_data.get("paging_info", {})

                # Append each reel to the list until the target count is reached
                for item in items:
                    media = item.get("media", {})
                    play_count = media.get("play_count")
                    code = media.get("code")
                    reels.append({"link": f"https://www.instagram.com/reel/{code}/", "viewcount": play_count})

                    if len(reels) >= target_reel_count:
                        break

                # Retrieve max_id from paging_info for the next request
                max_id = paging_info.get("max_id")
                if not max_id:
                    break  # No more pages if max_id is missing

            else:
                print("Failed to fetch reels data.")
                break

        reels.sort(key=lambda x: x["viewcount"], reverse=True)
        return reels[:target_reel_count]  # Return only up to the target count
    except Exception as e:
        print(f"Error scraping data for {reel_username}: {e}")
        return None

@app.before_request
def setup_driver():
    initialize_driver()

@app.route('/scrape_reels', methods=['POST'])
def scrape_reels():
    data = request.json
    reel_username = data.get("reel_username")
    list_name = data.get("listName")

    if not reel_username or not list_name:
        return jsonify({"error": "Missing required parameters"}), 400

    reels_data = get_reels_data(reel_username)

    if reels_data:
        # Format the response as specified
        response = {
            "ListName": list_name,
        }
        for idx, reel in enumerate(reels_data, start=1):
            response[f"reel{idx}"] = reel

        return jsonify(response)
    else:
        return jsonify({"error": "Failed to scrape data"}), 500

# Ensure the driver closes properly when the server stops
@app.teardown_appcontext
def shutdown_driver(exception=None):
    global driver
    if driver is not None:
        driver.quit()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
