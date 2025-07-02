# What the file does:
# - Fetch the present week's metrics from SQL database as summed values for each data type stored in a variable for each of them
# - Fetches the last week's metrics from SQL database as summed values for each data type stored in a variable for just the holders
# - Once the data is fetched, for the volume variable. Is gonna be divided by the total supply, then multiplied by 100 stored in a variable called v_t. For the holders variable,
# is the total number of holders in the present week - total number of holders in the last week, then divided by the total number of holders in the last week stored in a variable called h_t.
# And for the unique_senders and active_wallets variables, is unique_senders / active wallets stored in a variable called c_t. have these variables inside a function called demand_index.
# - The function demand_index is gonna have these variables as an equation D = w_v(v_t) + w_h(h_t) + w_c(c_t), where w_v is 0.5, w_h is 0.3 and w_c is 0.2 standing for the weights of each
# variable. 
# - The function demand_index is gonna return the value of D, which is the demand index. 
# - Then there will be a function called adaptive_threshold that will take the demand index and return a threshold value based on the demand index. 
# - The function is gonna take the demand index, and 'msct' which is set to be 0.5. Then inside the function, is gonna do this type of calculation: msct(1 + ga(D - msct)) where msct is 0.5 and ga is 0.2. 
# - Then the function will return the threshold value as set to be a new value of msct.
# - Then there will be a heat gap which takes the values of the demand index and the threshold value subtracting the demand index from the threshold value and returns a value called g_t
# - And finally, there will be a percent rule which takes gt and k which is set to be 0.6. and the calculation is gonna be f() = k * gt / msct where k is 0.6 and msct is whatever the value that comes out of the adaptive_threshold function.


import sqlite3
import os
from dotenv import load_dotenv
import json 
import sys

# Load environment variables from the repository root so that this module works
# regardless of where it's executed from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(REPO_ROOT, "necessities.env")
load_dotenv(ENV_PATH)

# Database path. Allow overriding via environment variable for flexibility.
DB_PATH = os.getenv("DB_PATH", "token_metrics.db")

# Path to persist the msct value between runs
MSCT_STATE_PATH = os.path.join(REPO_ROOT, "msct_state.json")


def load_msct(path: str, default: float = 0.5) -> float:
    """Load the saved msct value from ``path`` or return ``default``."""
    try:
        with open(path) as f:
            data = json.load(f)
            return float(data.get("msct", default))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return default
    
def save_msct(path: str, value: float) -> None:
    """Persist ``value`` to ``path`` in JSON format."""
    with open(path, "w") as f:
        json.dump({"msct": value}, f)

# Dynamic msct loaded from persistent storage
msct = load_msct(MSCT_STATE_PATH)

def demand_index(db_path, circulating_supply):
    circulating_supply_tokens = circulating_supply / 1e18
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Fetch present week sums
    cur.execute("""
        SELECT SUM(volume), SUM(unique_senders), SUM(active_wallets)
        FROM daily_metrics
        WHERE day BETWEEN date('now', '-6 days') AND date('now');
    """)
    v_sum, u_sum, a_sum = cur.fetchone()
    v_sum = float(v_sum or 0)
    u_sum = int(u_sum or 0)
    a_sum = int(a_sum or 0)

    cur.execute("""
        SELECT holder_count 
        FROM daily_metrics
        ORDER BY day DESC
        LIMIT 1;
    """)
    h_this = cur.fetchone()
    h_this = int(h_this[0]) if h_this else 0

    # Fetch last week holders sum
    cur.execute("""
        SELECT holder_count
        FROM daily_metrics
        WHERE day = date('now', '-7 days')
        LIMIT 1; 
    """)
    row = cur.fetchone()
    h_prev = int(row[0]) if row and row[0] is not None else None

    # If no previous week or not enough volume, do not adjust
    if v_sum <= 125000.0 or h_prev == None:
        conn.close()
        return None

    v_t = (v_sum / circulating_supply_tokens) * 100
    h_t = (h_this - h_prev) / h_prev if h_prev else 0.0
    c_t = (u_sum / a_sum) if a_sum else 0.0

    w_v, w_h, w_c = 0.5, 0.3, 0.2
    demand = (w_v * v_t) + (w_h * h_t) + (w_c * c_t)
    conn.close()

    return demand

def adaptive_threshold(demand, msct, ga=0.2):
    """Adaptive threshold calculation. The value that gets returned is the new msct."""
    new_value = msct * (1 + ga * (demand - msct))
    msct = new_value

    return msct 

def heat_gap(demand, threshold):
    """Heat gap calculation."""
    g_t = demand - threshold

    return g_t

def percent_rule(g_t, msct, k=0.6, pmax=0.05):
    """Percent rule calculation."""
    # raw = k * g_t / msct if msct else 0
    # return max(-pmax, min(raw, pmax))
    return k * g_t / msct if msct else 0 

if __name__ == "__main__":
    circulating_supply = 100000 # Enter a demo value of the circulating supply
    if circulating_supply is None:
        raise ValueError("Enter the circulating supply value.")

    the_demand = demand_index(DB_PATH, circulating_supply)
    if the_demand is None:
        print("No change to supply")
        sys.exit(1)
    msct = adaptive_threshold(the_demand, msct)
    save_msct(MSCT_STATE_PATH, msct)
    threshold = msct
    g_t = heat_gap(the_demand, threshold)
    percent = percent_rule(g_t, threshold)

    print(f"Demand Index: {the_demand}")
    print(f"Threshold: {threshold}")
    print(f"Heat Gap (g_t): {g_t}")
    print(f"Percent Rule: {percent}")
