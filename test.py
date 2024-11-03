import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import requests
import re
import json
import platform

# Global variable for the driver, initialized once
driver = None
driver_initialized = False

# Proxy details (replace with your actual proxy if needed)
proxy_host = "103.88.235.25"
proxy_port = "823"

def initialize_driver():
    global driver, driver_initialized
    if not driver_initialized:
        chrome_options = Options()
        # chrome_options.add_argument("--headless=new")
        chrome_options.add_argument(f'--proxy-server={proxy_host}:{proxy_port}')
        driver = uc.Chrome(options=chrome_options)
        driver_initialized = True

def get_dynamic_headers(driver, csrf_token):
    # Use JavaScript to retrieve browser and OS details for dynamic headers
    user_agent = driver.execute_script("return navigator.userAgent;")
    sec_ua = driver.execute_script("return navigator.userAgentData.brands.map(b => `${b.brand};v=\"${b.version}\"`).join(', ');")
    sec_platform = platform.system().lower()  # e.g., 'darwin', 'linux', or 'windows'

    headers = {
        "accept": "*/*",
        "accept-language": "en-GB,en;q=0.9",
        "content-type": "application/x-www-form-urlencoded",
        "priority": "u=1, i",
        "sec-ch-prefers-color-scheme": "dark",
        "sec-ch-ua": f"\"{sec_ua}\"",
        "sec-ch-ua-full-version-list": f"\"{user_agent}\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-model": "\"\"",
        "sec-ch-ua-platform": f"\"{sec_platform}\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-asbd-id": "129477",
        "x-csrftoken": csrf_token,
        "x-ig-app-id": "936619743392459",
        "x-ig-www-claim": "0",
        "x-instagram-ajax": "1017905023",
        "x-requested-with": "XMLHttpRequest"
    }
    return headers

def get_reels_data(reel_username="memezar", target_reel_count=100):
    initialize_driver()  # Ensure the driver is initialized
    try:
        reels_url = "https://www.instagram.com/api/v1/clips/user/"
        driver.get(f"https://www.instagram.com/{reel_username}/reels/")
        time.sleep(5)

        # Check if a dialog element is present and delete its main parent if found
        try:
            dialog_element = driver.find_element(By.XPATH, '//*[@role="dialog"]')
            driver.execute_script("arguments[0].parentNode.removeChild(arguments[0]);", dialog_element)
            print("Dialog element removed.")
        except Exception:
            print("No dialog element found, continuing...")

        # Extract user ID directly from the page HTML
        page_source = driver.page_source
        user_id_match = re.search(r'"profilePage_([0-9]+)"', page_source)
        if user_id_match:
            user_id = user_id_match.group(1)
            print(f"User ID for {reel_username}: {user_id}")
        else:
            print("User ID not found on the page.")
            with open("page_source.html", "w", encoding='utf-8') as f:
                f.write(driver.page_source)
            return None

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

        headers = get_dynamic_headers(driver, csrf_token)

        max_id = None
        reels = []
        
        while len(reels) < target_reel_count:
            body = {
                "include_feed_video": "true",
                "page_size": "12",
                "target_user_id": user_id
            }
            if max_id:
                body["max_id"] = max_id

            response = session.post(reels_url, headers=headers, data=body)

            print("Response:", response.json())
            if response.status_code == 200:
                reels_data = response.json()
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

            else:
                print("Failed to fetch reels data.")
                break


        reels.sort(key=lambda x: x["viewcount"], reverse=True)
        return reels[:target_reel_count]

    except Exception as e:
        print(f"Error scraping data for {reel_username}: {e}")
        return None

    finally:
        if driver:
            driver.quit()


reels_data = get_reels_data()
print(json.dumps(reels_data, indent=4))