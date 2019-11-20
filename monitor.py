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
C = 100.0

# Decay parameter
K = 0.997

# Power parameter
a = 0.05

def soften(x):
    """
    Softening function
    """
    return np.sqrt(x + C)

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

    # Make dict from claim_id to name, total_amount, and trending score
    for row in c.execute("""
SELECT claim_id, claim_name, (amount + support_amount) total_amount FROM claim
    WHERE claim_hash NOT IN
        (SELECT claim.claim_hash
            FROM claim INNER JOIN tag ON tag.claim_hash = claim.claim_hash
                                            AND tag.tag = "mature");
"""):


        claim_id = row[0]
        new_total_amount = row[2]/1E8
        try:
            old_total_amount = data[claim_id]["total_amount"]
            new_score = K*data[claim_id]["trending_score"] + soften(new_total_amount)\
                             - soften(old_total_amount)
        except:
            new_score = 0.01

        data[row[0]] = {"name": row[1], "total_amount": new_total_amount,
                                "trending_score": new_score}
        claim_ids.append(row[0])
        trendings.append(new_score*new_total_amount**a)

    conn.close()

    # Extract top 100
    indices = np.argsort(trendings)[::-1]
    claim_ids = np.array(claim_ids)[indices[0:100]]
    trendings = np.array(trendings)[indices[0:100]]

    the_dict = { "epoch": epoch, "ranks": [],  "claim_ids": [],
                    "vanity_names": [], "final_scores": [] }
    for i in range(len(claim_ids)):
        the_dict["ranks"].append(i+1)
        the_dict["claim_ids"].append(claim_ids[i])
        the_dict["vanity_names"].append(data[claim_ids[i]]["name"])
        the_dict["final_scores"].append(trendings[i])

    f = open("/home/brewer/Projects/LBRYnomics/trending.json", "w")
    f.write(json.dumps(the_dict))
    f.close()


    # Also save to HTML file
    f = open("/keybase/public/brendonbrewer/trending.html", "w")
    f.write("""
<!DOCTYPE HTML>
<html>
<head>
  <meta http-equiv="refresh" content="120">
  <title>Brendon's trending list</title>
</head>
<body>
  <p>
  I take no responsibility for the linked content. Proceed with extreme caution,
  it could be NSFW or even (rarely) illegal where you live!
  </p>

  <p>
    If the epoch number is less than a few hundred, it means I recently restarted
    the program, and the results might not be optimal.
  </p>

  <p>
    Current epoch: {epoch}<br>
  </p>

  <table>
    <tr style="font-weight: bold">  <td>Rank</td>   <td>Vanity Name</td>  <td>Score</td> </tr>
 
""".format(epoch=epoch))

    for i in range(len(claim_ids)):
        f.write("<tr>")
        f.write("<td>{rank}</td>".format(rank=the_dict["ranks"][i]))
        url = "https://lbry.tv/{vanity}:{claim_id}"\
                .format(vanity=the_dict["vanity_names"][i],
                        claim_id=the_dict["claim_ids"][i])
        link = "<a href=\"{url}\" target=\"_blank\">".format(url=url)\
                     + the_dict["vanity_names"][i] + "</a>"
        f.write("<td>" + str(link) + "</td>")
        f.write("<td>{score}</td>".format(score=the_dict["final_scores"][i]))
        f.write("</tr>\n")
    f.write("""
</table>
</body>
</html>
""")

    f.close()


    print("Done epoch {epoch}.".format(epoch=epoch))
    epoch += 1
    import time
    time.sleep(5*60)



