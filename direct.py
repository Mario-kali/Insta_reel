from flask import Flask, request, jsonify
import traceback 
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import requests
import json
import re
import platform
import subprocess

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
    chrome_options = Options()
    # chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument(f'--proxy-server={proxy_host}:{proxy_port}')
    driver = uc.Chrome(options=chrome_options)
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


def get_reels_data(reel_username, target_reel_count=100):
    for proxy_host in proxies:
        try:
            driver = initialize_driver(proxy_host)
            reels_url = "https://www.instagram.com/api/v1/clips/user/"
            driver.get(f"https://www.instagram.com/{reel_username}/reels/")
            time.sleep(5)

            time.sleep(2)
            close_dialog(driver)
            time.sleep(4)

            # Extract user ID from page HTML
            page_source = driver.page_source
            user_id_match = re.search(r'"profilePage_([0-9]+)"', page_source)
            if user_id_match:
                user_id = user_id_match.group(1)
                print(f"User ID for {reel_username}: {user_id}")
            else:
                print("User ID not found on the page.")
                raise Exception("User ID not found")

            # Collect cookies for curl command
            cookies = driver.get_cookies()
            csrf_token = None
            cookie_str = ""
            for cookie in cookies:
                cookie_str += f"{cookie['name']}={cookie['value']}; "
                if cookie['name'] == 'csrftoken':
                    csrf_token = cookie['value']

            if not csrf_token:
                print("CSRF token not found in cookies")
                raise Exception("CSRF token not found")

            # Static headers based on provided request
            headers = {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/x-www-form-urlencoded",
                "priority": "u=1, i",
                "sec-ch-prefers-color-scheme": "light",
                "sec-ch-ua": "\"Chromium\";v=\"130\", \"Google Chrome\";v=\"130\", \"Not?A_Brand\";v=\"99\"",
                "sec-ch-ua-full-version-list": "\"Chromium\";v=\"130.0.6723.91\", \"Google Chrome\";v=\"130.0.6723.91\", \"Not?A_Brand\";v=\"99.0.0.0\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-model": "\"\"",
                "sec-ch-ua-platform": "\"Linux\"",
                "sec-ch-ua-platform-version": "\"5.15.0\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-asbd-id": "129477",
                "x-csrftoken": csrf_token,
                "x-ig-app-id": "936619743392459",
                "x-ig-www-claim": "0",
                "x-instagram-ajax": "1017912114",
                "x-requested-with": "XMLHttpRequest",
                "x-web-device-id": "90775CD2-2724-4FFE-8282-74A3B47BED05"
            }

            max_id = None
            reels = []

            # Main loop for fetching reels
            while len(reels) < target_reel_count:
                body_data = f"include_feed_video=true&page_size=12&target_user_id={user_id}"
                if max_id:
                    body_data += f"&max_id={max_id}"

                # Convert headers to curl format
                curl_headers = [f"-H '{key}: {value}'" for key, value in headers.items()]

                # Rotate to the next proxy for the request
                next_proxy = proxies[(proxies.index(proxy_host) + 1) % len(proxies)]

                # Prepare the curl command with the next proxy
                curl_command = [
                    "curl", "-X", "POST", reels_url,
                    "-x", f"http://{next_proxy}:{proxy_port}",
                    *curl_headers,
                    "-b", cookie_str.strip("; "),
                    "--data", body_data
                ]

                # Print command for debugging
                print("Executing CURL:", " ".join(curl_command))

                # Execute the curl command
                result = subprocess.run(curl_command, capture_output=True, text=True)
                
                # Check response
                if result.returncode == 0:
                    try:
                        reels_data = json.loads(result.stdout)
                        items = reels_data.get("items", [])
                        paging_info = reels_data.get("paging_info", {})

                        for item in items:
                            media = item.get("media", {})
                            play_count = media.get("play_count")
                            code = media.get("code")
                            reels.append({"link": f"https://www.instagram.com/reel/{code}/", "viewcount": play_count})

                            if len(reels) >= target_reel_count:
                                break

                        max_id = paging_info.get("max_id")
                        if not max_id:
                            break
                    except json.JSONDecodeError as e:
                        print("Error decoding JSON response:", e)
                        print("Response:", result.stdout)
                        raise Exception("Failed to decode JSON response")
                else:
                    print("CURL command failed. Response:", result.stderr)
                    raise Exception("CURL command failed")

            reels.sort(key=lambda x: x["viewcount"] if x["viewcount"] is not None else 0, reverse=True)
            driver.quit()
            return reels[:target_reel_count]  # Return only up to the target count if successful

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
