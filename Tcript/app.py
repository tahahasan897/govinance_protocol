from flask import Flask, render_template_string, send_from_directory
from web3 import Web3
import json
import os
from dotenv import load_dotenv

# Always load environment variables from the repository root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(REPO_ROOT, "necessities.env")
load_dotenv(ENV_PATH)

# Configuration
RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

app = Flask(__name__)
w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 5}))

# Load the ABI relative to this file so running from other directories works
ABI_PATH = os.path.join(os.path.dirname(__file__), "abi.json")
with open(ABI_PATH) as f:
    abi = json.load(f)

if not CONTRACT_ADDRESS:
    raise EnvironmentError("CONTRACT_ADDRESS is not set in environment")

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=abi
)

@app.route("/supply-data")
def supply_data():
    # data_dir is Tcript/data
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    csv_path = os.path.join(data_dir, "supply.csv")
    print("-> looking in", data_dir)
    print("-> exists?", os.path.exists(csv_path))
    print("-> contents:", os.listdir(data_dir) if os.path.exists(data_dir) else "no folder")
    if not os.path.exists(csv_path):
        return f"CSV not found at {csv_path}", 404
    return send_from_directory(data_dir, "supply.csv", mimetype="text/csv")

@app.route("/")
def index():
    try:
        total_supply = contract.functions.totalSupply().call()
        # The contract stores totalSupply in wei-like units (18 decimals).
        supply = str(total_supply)
    except Exception:
        import traceback
        print("Exception fetching totalSupply:\n", traceback.format_exc())
        supply = "Unavailable"

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
      <title>AI-Controlled Crypto Supply</title>
      <!-- Fixed Chart.js include (removed extra quote) -->
      <script src="https://cdn.jsdelivr.net/npm/chart.js@2.9.4/dist/Chart.min.js"></script>
    </head>
    <body>
      <h1>AI-Controlled Crypto Supply</h1>
      <p>Total Supply: {{ supply }}</p>
      <canvas id="supplyChart" width="400" height="200"></canvas>

      <!-- Inline script with debug logging -->
      <script>
        console.log("⚙️ inline script loaded");
        fetch('/supply-data')
          .then(resp => {
            console.log("fetch /supply-data status:", resp.status);
            return resp.text();
          })
          .then(text => {
            console.log("Raw CSV text:", text);
            const rows = text.trim().split('\\n').slice(1);
            const labels = [], data = [];
            rows.forEach(row => {
              const [date, supply] = row.split(',');
              labels.push(date);
              data.push(Number(supply));
            });
            new Chart(document.getElementById('supplyChart'), {
              type: 'line',
              data: {
                labels: labels,
                datasets: [{
                  label: 'Total Supply',
                  data: data,
                  borderColor: 'blue',
                  tension: 0.1,
                  fill: false
                }]
              },
              options: {
                scales: {
                  y: {
                    beginAtZero: true
                  }
                }
              }
            });
          })
          .catch(err => console.error("fetch error:", err));
      </script>
    </body>
    </html>
    """, supply=supply)

if __name__ == "__main__":
    # Print out all registered routes to confirm /supply-data is active
    print("URL map:", app.url_map)
    app.run(debug=True)
