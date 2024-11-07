from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# Your Apify API token
APIFY_TOKEN = "apify_api_qI26br3ucdk1JtCdJozAVBEbBFhfqM3M5E3N"
ZAPIER_WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/17969384/29cd3cy/"

def run_apify_actor(reel_username):
    url = f"https://api.apify.com/v2/acts/hpix~ig-reels-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    
    payload = {
        "reels_count": 3,
        "tags": [reel_username]
    }

    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200 or response.status_code == 201:
        print("Scraper ran successfully.")
        # print ("response: ", response.content)
        data = json.loads(response.content.decode('utf-8'))
        print("Response: ",data)
        return response.json()  # Contains dataset items (top reels)
    else:
        print("Error running Scraper:", response.status_code, response.text)
        return None


def format_response_for_zapier(data, list_name):
    reels = []

    # Collect reels from `edge_felix_video_timeline`
    for item in data:
        felix_edges = item.get('raw_data', {}).get('edge_felix_video_timeline', {}).get('edges', [])
        for edge in felix_edges:
            node = edge.get('node', {})
            reels.append({
                "link": f"https://www.instagram.com/reel/{node.get('shortcode', '')}/",
                "viewcount": node.get("video_view_count", 0)
            })

    # Collect reels from `edge_owner_to_timeline_media`
    for item in data:
        owner_edges = item.get('raw_data', {}).get('edge_owner_to_timeline_media', {}).get('edges', [])
        for edge in owner_edges:
            node = edge.get('node', {})
            reels.append({
                "link": f"https://www.instagram.com/reel/{node.get('shortcode', '')}/",
                "viewcount": node.get("video_view_count", 0)
            })

    # Sort reels by view count in descending order
    sorted_reels = sorted(reels, key=lambda x: x["viewcount"], reverse=True)

    # Format the response
    formatted_response = {"ListName": list_name}
    for i, reel_data in enumerate(sorted_reels, start=1):
        formatted_response[f"reel{i}"] = reel_data

    return formatted_response
@app.route('/scrape_reels', methods=['POST'])
def scrape_reels():
    data = request.json
    reel_username = data.get("reel_username")
    list_name = data.get("listName")

    if not reel_username or not list_name:
        return jsonify({"error": "Missing 'reel_username' or 'listName'"}), 400

    # Run the Apify actor and get results
    result = run_apify_actor(reel_username)

    # if result:
    #     formatted_result = format_response_for_zapier(result, list_name)
    #     zapier_response = requests.post(ZAPIER_WEBHOOK_URL, json=formatted_result)
    #     if zapier_response.status_code == 200:
    #         print("Data sent to Zapier successfully.")
    #     else:
    #         print("Error sending data to Zapier:", zapier_response.status_code, zapier_response.text)
    #     return jsonify(formatted_result)
    # else:
    #     return jsonify({"error": "Failed to run Apify actor"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
