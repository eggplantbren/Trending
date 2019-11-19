import json
import numpy as np
import subprocess
import sqlite3

# Full path to the lbrynet binary
lbrynet_bin = "/opt/LBRY/resources/static/daemon/lbrynet"

def daemon_command(command, message="Calling lbrynet daemon..."):
    """
    Run a daemon command and return its output.
    """
    print(message, end="", flush=True)
    command = lbrynet_bin + " " + command
    parts = command.split(" ")
    output = subprocess.run(parts, capture_output=True)
    print("done.")
    return json.loads(output.stdout)


def get_block():
    """
    Get current block
    """
    result = daemon_command("status", message="Getting current block...")
    return result["wallet"]["blocks"]



# Floor parameter
C = 10.0

# Decay parameter
K = 0.99

# Power parameter
a = 0.05

def soften(x):
    """
    Softening function
    """
    return np.log10(x + C)

# Dict from claim_id to measurements
data = {}




# Loop
epoch = 0
while True:

    # Connection to claims.db
    # Open claims.db
    db_file = "/home/brewer/local/lbry-sdk/lbry/lbryum_data/claims.db"
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    # List of claim_id and trending
    claim_ids = []
    trendings = []

    # Make dict from claim_id to name, amount, and trending score
    for row in c.execute("SELECT claim_id, claim_name, amount FROM claim;"):
        claim_id = row[0]
        new_amount = row[2]/1E8
        try:
            old_amount = data[claim_id]["amount"]
            new_score = K*data[claim_id]["trending_score"] + soften(new_amount)\
                             - soften(old_amount)
        except:
            new_score = 0.01

        data[row[0]] = {"name": row[1], "amount": new_amount,
                                "trending_score": new_score}
        claim_ids.append(row[0])
        trendings.append(new_score*new_amount**a)

    conn.close()

    # Extract top 100
    indices = np.argsort(trendings)[::-1]
    claim_ids = np.array(claim_ids)[indices[0:100]]
    f = open("/keybase/public/brendonbrewer/trending.txt", "w")
    s = "Epoch " + str(epoch)
    print(s)
    f.write(s + "\n")
    for claim_id in claim_ids:
        s = "https://lbry.tv/" + data[claim_id]["name"] + ":" + claim_id
        print(s)
        f.write(s + "\n")
    print("")
    f.close()

    import time
    time.sleep(15*60)
    epoch += 1


