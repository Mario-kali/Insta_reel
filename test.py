from flask import Flask, request, jsonify
import requests
import threading

app = Flask(__name__)

# Zapier webhook URL
zapier_url = "https://hooks.zapier.com/hooks/catch/xxxxxx/yyyyyy"  # Replace with actual Zapier URL

# Hardcoded response data
hardcoded_response = {
    "ListName": "test",
    "reel1": {"link": "https://www.instagram.com/reel/C_qV5D9vRLn/", "viewcount": 6963011},
    "reel2": {"link": "https://www.instagram.com/reel/C_qV5D9vRLn/", "viewcount": 6963011},
    "reel3": {"link": "https://www.instagram.com/reel/C_qV5D9vRLn/", "viewcount": 6963011},
    "reel4": {"link": "https://www.instagram.com/reel/C_qV5D9vRLn/", "viewcount": 6963011},
    "reel5": {"link": "https://www.instagram.com/reel/C_qV5D9vRLn/", "viewcount": 6963011},
    "reel6": {"link": "https://www.instagram.com/reel/C_qV5D9vRLn/", "viewcount": 6963011},
    "reel7": {"link": "https://www.instagram.com/reel/C_qV5D9vRLn/", "viewcount": 6963011},
    "reel8": {"link": "https://www.instagram.com/reel/C_qV5D9vRLn/", "viewcount": 6963011},
    "reel9": {"link": "https://www.instagram.com/reel/C_BHJUVPQHb/", "viewcount": 5332258},
    "reel10": {"link": "https://www.instagram.com/reel/C_BHJUVPQHb/", "viewcount": 5332258},
    "reel11": {"link": "https://www.instagram.com/reel/C_BHJUVPQHb/", "viewcount": 5332258},
    "reel12": {"link": "https://www.instagram.com/reel/C_BHJUVPQHb/", "viewcount": 5332258},
    "reel13": {"link": "https://www.instagram.com/reel/C_BHJUVPQHb/", "viewcount": 5332258},
    "reel14": {"link": "https://www.instagram.com/reel/DAd0PlzPF7M/", "viewcount": 4740477},
    "reel15": {"link": "https://www.instagram.com/reel/DAd0PlzPF7M/", "viewcount": 4740477},
    "reel16": {"link": "https://www.instagram.com/reel/DAd0PlzPF7M/", "viewcount": 4740477},
    "reel17": {"link": "https://www.instagram.com/reel/DAd0PlzPF7M/", "viewcount": 4740477},
    "reel18": {"link": "https://www.instagram.com/reel/DAd0PlzPF7M/", "viewcount": 4740477},
    "reel19": {"link": "https://www.instagram.com/reel/DAd0PlzPF7M/", "viewcount": 4740477},
    "reel20": {"link": "https://www.instagram.com/reel/DAd0PlzPF7M/", "viewcount": 4740477}
}

def send_to_zapier(list_name):
    payload = {"ListName": list_name}
    payload.update(hardcoded_response)
    
    try:
        response = requests.post(zapier_url, json=payload)
        print(f"Data sent to Zapier with status code {response.status_code}")
    except Exception as e:
        print(f"Error sending data to Zapier: {e}")

@app.route('/scrape_reels', methods=['POST'])
def scrape_reels():
    data = request.json
    list_name = data.get("listName")

    if not list_name:
        return jsonify({"error": "Missing required parameters"}), 400

    # Immediately return a 200 response and start the async Zapier call
    threading.Thread(target=send_to_zapier, args=(list_name,)).start()
    return jsonify({"message": "Scraping in progress"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
