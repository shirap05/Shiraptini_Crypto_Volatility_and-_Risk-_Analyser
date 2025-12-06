from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

API_KEY = "CG-j36Jb6fjM7XXadA6CDJPLLAU"  # your key

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/milestone1")
def milestone1():
    return render_template("milestone1.html")

@app.route("/api/crypto")
def crypto_api():

    url = "https://api.coingecko.com/api/v3/coins/markets"

    params = {
        "vs_currency": "usd",
        "ids": "bitcoin,ethereum,solana,dogecoin,cardano",
        "order": "market_cap_desc",
        "sparkline": False
    }

    headers = {
        "x-cg-demo-api-key": API_KEY
    }

    try:
        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            return jsonify({
                "error": "Error fetching data",
                "status": response.status_code,
                "details": response.text
            }), 500

        data = response.json()

        result = []

        for c in data:
            result.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "symbol": c.get("symbol", "").upper(),
                "price": c.get("current_price"),
                "change_24h": c.get("price_change_percentage_24h"),
                "volume": c.get("total_volume")
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": "Server crashed", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
