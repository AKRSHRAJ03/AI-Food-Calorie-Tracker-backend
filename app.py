from flask import Flask, request, jsonify, url_for
from flask_cors import CORS
import requests
import os
import base64
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend

import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Load API keys
VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")


def recognize_dish(image_bytes):
    url = f"https://vision.googleapis.com/v1/images:annotate?key={VISION_API_KEY}"
    payload = {
        "requests": [{
            "image": {"content": base64.b64encode(image_bytes).decode()},
            "features": [{"type": "WEB_DETECTION", "maxResults": 3}]
        }]
    }
    response = requests.post(url, json=payload)
    result = response.json()
    try:
        entities = result["responses"][0]["webDetection"]["webEntities"]
        for e in entities:
            if "description" in e:
                return e["description"]
    except:
        pass
    return "Unknown"


def get_nutrition(dish_name):
    url = f"https://api.spoonacular.com/food/menuItems/search?query={dish_name}&apiKey={SPOONACULAR_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data["menuItems"]:
            dish_id = data["menuItems"][0]["id"]
            details_url = f"https://api.spoonacular.com/food/menuItems/{dish_id}?apiKey={SPOONACULAR_API_KEY}"
            detail_res = requests.get(details_url)
            if detail_res.status_code == 200:
                return detail_res.json()
    return None


def generate_chart(nutrition_data):
    nutrients = nutrition_data["nutrition"]["nutrients"]
    wanted = ["Protein", "Fat", "Total Carbohydrates", "Sugar", "Cholesterol", "Fiber"]
    labels, values = [], []
    for n in nutrients:
        if n["name"] in wanted:
            labels.append(n["name"])
            values.append(n["amount"])

    # Ensure the static folder exists
    os.makedirs("static", exist_ok=True)

    # Plot and save
    plt.figure(figsize=(8, 5))
    plt.bar(labels, values, color='skyblue')
    plt.xlabel("Nutrients")
    plt.ylabel("Amount")
    plt.title("Nutrition Breakdown")
    plt.tight_layout()

    chart_path = os.path.join("static", "chart.png")
    plt.savefig(chart_path)
    plt.close()

    return chart_path



@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("image")
    dish_name = request.form.get("dish_name")

    if file:
        image_bytes = file.read()
        dish_name = recognize_dish(image_bytes)

    if dish_name:
        nutrition_data = get_nutrition(dish_name)
        if nutrition_data:
            chart_path = generate_chart(nutrition_data)
            calories = next((n["amount"] for n in nutrition_data["nutrition"]["nutrients"] if n["name"] == "Calories"), 0)
            print("Chart generated at:", chart_path)
            print("File exists?", os.path.exists("static/chart.png"))
            print("File size:", os.path.getsize("static/chart.png") if os.path.exists("static/chart.png") else "N/A")

            chart_url = url_for('static_files', filename='chart.png', _external=True)

            return jsonify({
                "dish": dish_name,
                "calories": calories,
                "chart_url": chart_url
            })
    return jsonify({"error": "Dish not found or nutrition data unavailable."}), 400
from flask import send_from_directory

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


if __name__ == "__main__":
    app.run(debug=True)
