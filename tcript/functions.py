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

# Load environment variables from the repository root so that this module works
# regardless of where it's executed from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(REPO_ROOT, "necessities.env")
load_dotenv(ENV_PATH)

# Database path. Allow overriding via environment variable for flexibility.
DB_PATH = os.getenv("DB_PATH", "token_metrics.db")

# Total supply of the token. This can be provided through an environment
# variable so the functions can operate with the correct value without editing
# the code.
TOTAL_SUPPLY = 1000000

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

def demand_index(db_path, total_supply):
    """
    Calculate demand index D for the present week using the rules described.
    Returns: D, v_t, h_t, c_t, present/last week holders, threshold, heat gap, percent rule
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Fetch present week sums
    cur.execute("""
        SELECT SUM(volume), SUM(holder_count), SUM(unique_senders), SUM(active_wallets)
        FROM daily_metrics
        WHERE day BETWEEN date('now', '-6 days') AND date('now');
    """)
    v_sum, h_sum, u_sum, a_sum = cur.fetchone()
    v_sum = int(v_sum or 0)
    h_sum = int(h_sum or 0)
    u_sum = int(u_sum or 0)
    a_sum = int(a_sum or 0)

    # Fetch last week holders sum
    cur.execute("""
        SELECT SUM(holder_count)
        FROM daily_metrics
        WHERE day BETWEEN date('now', '-13 days') AND date('now', '-7 days'); 
    """)
    h_last = cur.fetchone()[0]
    h_last = int(h_last or 1)  # avoid div by zero

    # v_t: volume/total_supply*100
    v_t = (v_sum / total_supply) * 100
    # h_t: (present holders - last week holders) / last week holders
    h_t = (h_sum - h_last) / h_last if h_last else 0.0
    # c_t: unique_senders / active_wallets
    c_t = (u_sum / a_sum) if a_sum else 0.0

    # Demand index D
    w_v, w_h, w_c = 0.5, 0.3, 0.2
    demand = w_v * v_t + w_h * h_t + w_c * c_t
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

def percent_rule(g_t, msct, k=0.6):
    """Percent rule calculation."""
    return k * g_t / msct if msct else 0

if __name__ == "__main__":
    the_demand = demand_index(DB_PATH, TOTAL_SUPPLY)
    msct = adaptive_threshold(the_demand, msct)
    save_msct(MSCT_STATE_PATH, msct)
    threshold = msct
    g_t = heat_gap(the_demand, threshold)
    percent = percent_rule(g_t, threshold)

    print(f"Demand Index: {the_demand}")
    print(f"Threshold: {threshold}")
    print(f"Heat Gap (g_t): {g_t}")
    print(f"Percent Rule: {percent}")
