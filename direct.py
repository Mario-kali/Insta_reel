from flask import Flask, request, jsonify
import traceback 
from seleniumwire.undetected_chromedriver.v2 import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
from seleniumwire.utils import decode as sw_decode
import time
import requests
import json
import re
import platform
import subprocess
from selenium.webdriver.common.action_chains import ActionChains

app = Flask(__name__)

# List of proxy IPs to cycle through
proxies = [
    "5.78.64.26",
    "5.161.202.98",
    "45.250.255.245",
    "103.88.235.25",
    "139.99.181.179",
    "144.76.124.83",
    "177.54.154.91",
]
proxy_port = "823"  # Assuming all proxies use the same port

def initialize_driver(proxy_host):
    chrome_options = ChromeOptions()
    # chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-insecure-localhost")
    chrome_options.add_argument(f'--proxy-server={proxy_host}:{proxy_port}')
    driver = Chrome(options=chrome_options)
    print(f"Initialized driver with proxy: {proxy_host}:{proxy_port}")
    return driver

def close_dialog(driver):
    try:
        # Try to find and click the 'Close' button
        close_button = driver.find_element(By.XPATH, '//*[@aria-label="Close"]')
        close_button.click()
        print("Dialog closed using 'Close' button.")
    except Exception:
        # If 'Close' button is not found, click outside the dialog
        print("Close button not found. Attempting to click outside the dialog.")
        driver.execute_script("document.body.click();")

def capture_user_requests(driver):
    requests_data = []
    
    # Get all requests
    network_events = driver.execute_cdp_cmd("Network.getAllCookies", {})
    
    for event in network_events:
        if "request" in event and "url" in event["request"]:
            request_url = event["request"]["url"]
            if "clips/user/" in request_url:
                print("Captured request URL:", request_url)
                requests_data.append(request_url)
    
    return requests_data

    
def get_reels_data(reel_username, scroll_count=20):
    for proxy_host in proxies:
        driver = initialize_driver(proxy_host)
        try:
            
            driver.get(f"https://www.instagram.com/{reel_username}/reels/")
            time.sleep(5)

            close_dialog(driver)
            time.sleep(2)
            captured_requests = []
            action = ActionChains(driver)

            for _ in range(scroll_count):
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)

                # Check for dialog again in case it reappears
                close_dialog(driver)
                 # Scroll and capture requests



                # Capture 'clips/user/' requests made by the browser
                for idx, request in enumerate(driver.requests):
                    if 'clips/user/' in request.url and request.response:
                        try:
                            # Attempt to decode as UTF-8
                            data = sw_decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
                            response_data = data.decode('utf-8')
                            # print (response_data)
                            captured_requests.append(json.loads(response_data))
                        except UnicodeDecodeError as e:
                            print(f"Error decoding response for request {idx}: {e}")
                            # Save the raw binary data to a file for inspection
                            raw_file_path = f"raw_response_{idx}.bin"
                            with open(raw_file_path, "wb") as raw_file:
                                raw_file.write(request.response.body)
                            print(f"Raw response saved to {raw_file_path}")

            if (len(captured_requests)<=1):
                raise Exception

            # Process captured requests if any
            reels = []
            for data in captured_requests:
                items = data.get("items", [])
                for item in items:
                    media = item.get("media", {})
                    play_count = media.get("play_count")
                    code = media.get("code")
                    reels.append({"link": f"https://www.instagram.com/reel/{code}/", "viewcount": play_count})

            reels.sort(key=lambda x: x["viewcount"] if x["viewcount"] is not None else 0, reverse=True)
            return reels[:scroll_count] if reels else None

        except Exception as e:
            print(f"Error with proxy {proxy_host}: {e}")
            print("Traceback details:", traceback.format_exc())
            driver.save_screenshot("error.png")
            with open("page_source.html", "w", encoding='utf-8') as f:
                f.write(driver.page_source)
            driver.quit()

    print("All proxies failed.")
    return None


@app.route('/scrape_reels', methods=['POST'])
def scrape_reels():
    data = request.json
    reel_username = data.get("reel_username")
    list_name = data.get("listName")

    if not reel_username or not list_name:
        return jsonify({"error": "Missing required parameters"}), 400
    
    reels_data = get_reels_data(reel_username)

    if reels_data:
        response = {"ListName": list_name}
        for idx, reel in enumerate(reels_data, start=1):
            response[f"reel{idx}"] = reel

        return jsonify(response)
    else:
        return jsonify({"error": "Failed to scrape data"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
