from flask import Flask, request, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
import requests
import json
from id import get_user_id_from_username

app = Flask(__name__)

# Define accounts
accounts = [
    {"email": "ahmed.yaqub786", "password": "Ramisha_12"},
]

# Global variable for the driver, initialized once
driver = None
driver_initialized = False

def initialize_driver():
    global driver, driver_initialized
    if not driver_initialized:
        chrome_options = Options()
        # chrome_options.add_argument("--headless=new")
        driver = uc.Chrome(options=chrome_options)
        driver_initialized = True

def instagram_login(username, password):
    try:
        driver.get("https://www.instagram.com/accounts/login/?next=%2Flogin%2F&source=desktop_nav")
        time.sleep(3)
        username_field = driver.find_element(By.NAME, "username")
        username_field.send_keys(username)
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(password)
        password_field.send_keys(Keys.RETURN)
        time.sleep(5)
        return True
    except Exception as e:
        print(f"Login failed for {username}: {e}")
        return False

def get_reels_data(reel_username):
    try:
        reels_url = f"https://www.instagram.com/{reel_username}/reels/"
        driver.get(reels_url)
        time.sleep(5)
        
        cookies = driver.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'accept': '*/*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'x-ig-app-id': '936619743392459'
        }

        reels = []
        has_more_reels = True
        after = None
        user_id = get_user_id_from_username(reel_username)

        while has_more_reels and len(reels) < 100:
            variables = {
                "after": after,
                "first": 12,
                "data": {
                    "include_feed_video": True,
                    "page_size": 12,
                    "target_user_id": user_id
                }
            }
            
            data = {
                'fb_api_req_friendly_name': 'PolarisProfileReelsTabContentQuery_connection',
                'variables': json.dumps(variables),
                'doc_id': '8515196628595751'
            }

            response = session.post("https://www.instagram.com/graphql/query", headers=headers, data=data)

            if response.status_code == 200:
                reels_data = response.json()
                edges = reels_data.get("data", {}).get("xdt_api__v1__clips__user__connection_v2", {}).get("edges", [])
                
                for edge in edges:
                    node = edge.get("node", {})
                    media = node.get("media", {})
                    play_count = media.get("play_count")
                    code = media.get("code")
                    reels.append({"link": f"https://www.instagram.com/reel/{code}/", "viewcount": play_count})

                    if len(reels) >= 1000:
                        has_more_reels = False
                        break

                page_info = reels_data.get("data", {}).get("xdt_api__v1__clips__user__connection_v2", {}).get("page_info", {})
                after = page_info.get("end_cursor")
                has_more_reels = page_info.get("has_next_page", False)

            else:
                break

        reels.sort(key=lambda x: x["viewcount"], reverse=True)
        return reels
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

    reels_data = None

    # Try each account until one succeeds
    for account in accounts:
        login_successful = instagram_login(account['email'], account['password'])
        if login_successful:
            reels_data = get_reels_data(reel_username)
            if reels_data:
                break  
        else:
            print(f"Skipping account {account['email']} due to login failure")

    if reels_data:
        # Format the response as specified
        response = {
            "ListName": list_name,
        }
        for idx, reel in enumerate(reels_data, start=1):
            response[f"reel{idx}"] = reel

        return jsonify(response)
    else:
        return jsonify({"error": "All accounts failed to scrape data"}), 500

# Ensure the driver closes properly when the server stops
@app.teardown_appcontext
def shutdown_driver(exception=None):
    global driver
    if driver is not None:
        driver.quit()

if __name__ == "__main__":
    app.run(debug=True)
