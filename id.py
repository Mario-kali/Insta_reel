import requests
import re

# Define the proxy details
proxy_host = "5.161.202.98"
proxy_port = "823"
proxy_username = "4c6cc4a9101e6db9d7fe"
proxy_password = "4e8da6d5bdc21c95"

# Format the proxy with authentication
proxy = f"http://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
proxies = {
    "http": proxy,
    "https": proxy
}

def get_user_id_from_username(username):
    url = f"https://www.instagram.com/{username}/"
    response = requests.get(url, proxies=proxies)
    if response.status_code == 200:
        # Extract user ID from HTML using regex
        user_id = re.search(r'"profilePage_([0-9]+)"', response.text)
        if user_id:
            return user_id.group(1)
        else:
            print("User ID not found.")
    else:
        print("Failed to retrieve page.")
    return None

username = "fcbarcelona"
user_id = get_user_id_from_username(username)
print(f"User ID for {username}: {user_id}")
