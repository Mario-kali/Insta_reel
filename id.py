import requests
import re

def get_user_id_from_username(username):
    url = f"https://www.instagram.com/{username}/"
    response = requests.get(url)
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


