import html
import json
import numpy as np
import shlex
import subprocess
import sqlite3
import time

# Decay parameter
K = 0.9951980443443538

def soften(delta):
    """
    Softening function applies to LBC changes.
    """
    if delta >= 0.0:
        return delta**0.3

    # If delta is negative
    mag = np.abs(delta)
    return -(mag**0.3)


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



def format_line(i, the_dict, result):
    """
    Write one line of the table into a string
    """
    s = ""

    s += "<td>{rank}</td>".format(rank=the_dict["ranks"][i])
    s += "<td>{score}</td>".format(score=the_dict["final_scores"][i])

    full_name = the_dict["vanity_names"][i] + "#" + the_dict["claim_ids"][i]
    claim = result[full_name]
    canonical_url = claim["canonical_url"]
    tv_url = "https://lbry.tv/" + canonical_url[7:]
    tv_url = tv_url.replace("#", ":")

    if claim["value_type"] == "channel":
        title = claim["name"]
    else:
        title = claim["value"]["title"]
    short_title = title[0:50]
    if len(short_title) < len(title):
        short_title += "..."


    link = "<a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">".format(url=html.escape(tv_url))\
                 + html.escape(short_title) + "</a>"
    s += "<td>" + link + "</td>"
    s += "<td class=\"canonical\">{url}</td>".format(url=canonical_url)
    return s


def do_epoch(data, epoch):
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
            WHERE tag.tag = "mature" OR tag.tag = "nsfw" OR
                  tag.tag = "porn" OR tag.tag = "xxx");
"""):


        claim_id = row[0]
        new_total_amount = row[2]/1E8
        try:
            old_total_amount = data[claim_id]["total_amount"]
            new_score = K*data[claim_id]["trending_score"]\
                            + soften(new_total_amount - old_total_amount)
        except:
            new_score = 0.0

        data[row[0]] = {"name": row[1], "total_amount": new_total_amount,
                                "trending_score": new_score}
        claim_ids.append(row[0])
        trendings.append(new_score)

    conn.close()

    # Extract top 1000
    indices = np.argsort(trendings)[::-1]
    claim_ids = np.array(claim_ids)[indices[0:1000]]
    trendings = np.array(trendings)[indices[0:1000]]

    the_dict = { "epoch": epoch, "ranks": [],  "claim_ids": [],
                    "vanity_names": [], "final_scores": [] }
    for i in range(len(claim_ids)):
        the_dict["ranks"].append(i+1)
        the_dict["claim_ids"].append(claim_ids[i])
        the_dict["vanity_names"].append(data[claim_ids[i]]["name"])
        the_dict["final_scores"].append(trendings[i])

    # Resolve the claims to get more info
    arg = "resolve -- "
    for i in range(len(claim_ids)):
        arg += the_dict["vanity_names"][i]
        arg += "#"
        arg += the_dict["claim_ids"][i]
        arg += " "
    arg = arg[0:-1]
    arg = shlex.quote(arg) # Escape special shell characters
    arg = arg[1:-1] # Remove ' ' put in by shlex.quote

    # Resolve the claims
    result = daemon_command(arg)

    # Write to JSON file
    # First add the extra data obtained from the resolve
    the_dict["thumbnail_urls"] = []
    the_dict["titles"] = []
    the_dict["canonical_urls"] = []
    the_dict["tv_urls"] = []
    the_dict["channels"] = []
    for i in range(len(claim_ids)):
        full_name = the_dict["vanity_names"][i] + "#" + the_dict["claim_ids"][i]
        claim = result[full_name]

        try:
            canonical_url = claim["canonical_url"]
            tv_url = canonical_url
        except:
            tv_url = "NA"
            canonical_url = "NA"

        the_dict["canonical_urls"].append(canonical_url)
        tv_url.replace("#", ":")
        tv_url.replace("lbry://", "https://lbry.tv/")
        tv_url = html.escape(tv_url)
        the_dict["tv_urls"].append(tv_url)

        if claim["canonical_url"].count("@") == 0:
            the_dict["channels"].append(None)
        else:
            temp = claim["canonical_url"]
            the_dict["channels"].append(temp[7:].split("/")[0])

        if claim["value_type"] == "channel":
            the_dict["titles"].append(claim["name"])
        else:
            the_dict["titles"].append(claim["value"]["title"])

        try:
            the_dict["thumbnail_urls"]\
                    .append(claim["value"]["thumbnail"]["url"])
        except:
            the_dict["thumbnail_urls"].append(None)



    # Also save to HTML file
    f = open("/keybase/public/brendonbrewer/trending.html", "w")
    f.write("""
<!DOCTYPE HTML>
<html>
<head>
  <meta http-equiv="refresh" content="120">
  <title>Brendon's trending list</title>
  <style>
    body {{ background-color: #333333;
           color: #DDDDDD; }}
    a    {{ color: #8888EE; }}
    td.canonical {{ font-family: monospace; font-size: 0.8em; }}
  </style>
</head>
<body>
  <h1>Experimental LBRY Trending List</h1>
  <hr>

  <p>
    Welcome to my experimental responsive LBRY trending list.
    I take no responsibility for the linked content. Proceed with caution
    when following links as they could be NSFW or otherwise dubious.
    This table updates itself every 5 minutes, and the page also
    auto-refreshes every two minutes so you don't have to do it manually.
  </p>

  <p>
    The "current epoch" number below counts the number of times the
    table has been updated to take into account recent events on the
    LBRY blockchain. Tips, supports, changes in the publisher's deposit, as
    well as the removal of tips and supports,
    will all affect the trending score shown here.
    If the epoch number is less than a few hundred, it means I recently
    restarted
    the program which generates this page, so the results might not be optimal.
  </p>

  <p>
    If you want to connect your LBRY app to
    a wallet server that implements a very similar
    algorithm, see <a href="https://open.lbry.com/@BrendonBrewer:3/wallet-server:1" target="_blank" rel="noopener noreferrer">here</a>.
  </p>

  <hr>
  <p style="font-size: 1.2em;">
    Current epoch: {epoch}<br>
  </p>

  <table>
    <col width="130">
    <tr style="font-weight: bold; font-size: 1.2em"> <td>Rank</td>  <td style="width: 12em;">Score</td>   <td>Title (links open on lbry.tv)</td> <td>Canonical URL</td> </tr>
 
""".format(epoch=epoch))

    for i in range(len(claim_ids)):
        f.write("<tr>")

        try:
            s = format_line(i, the_dict, result)
            f.write(s)
        except:
            f.write("<td>N/A</td> <td>N/A</td> <td>N/A</td> <td class=\"canonical\">N/A</td>")

        f.write("</tr>\n")
    f.write("""
</table>
</body>
</html>
""")

    f.close()



    # Save truncated dict to JSON
    f = open("/keybase/public/brendonbrewer/trending.json", "w")
    the_dict.pop("vanity_names")
    the_dict.pop("claim_ids")
    the_dict.pop("canonical_urls")
    the_dict.pop("final_scores")
    for key in the_dict.keys():
        if key != "epoch":
            the_dict[key] = the_dict[key][0:100]
    f.write(json.dumps(the_dict))
    f.close()



if __name__ == "__main__":

    # Dict from claim_id to measurements
    data = {}


    # Loop
    epoch = 0
    while True:

        # Get the start time
        start_time = time.time()

        do_epoch(data, epoch)
        duration = time.time() - start_time
        print("Done epoch {epoch}. It took {sec} seconds."\
                        .format(epoch=epoch, sec=duration))
        epoch += 1
        time.sleep(300.0 - duration)

