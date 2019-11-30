import json
import numpy as np
import subprocess
import sqlite3
import time

# Decay parameter
K = 0.9975961328836203

def soften(delta):
    """
    Softening function applies to LBC changes.
    Softens strongly on positive changes and weakly on negative ones.
    """
    if delta >= 0.0:
        return delta**0.25

    # If delta is negative
    mag = np.abs(delta)
    return -(mag**0.5)



if __name__ == "__main__":

    # Dict from claim_id to measurements
    data = {}




    # Loop
    epoch = 0
    while True:

        # Get the start time
        start_time = time.time()

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
                new_score = 1.0E-6

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
      <style>
        body {{ background-color: #333333;
               color: #DDDDDD; }}
        a    {{ color: #8888EE; }}
      </style>
    </head>
    <body>
      <p>
        Welcome to my experimental responsive LBRY trending list.
        I take no responsibility for the linked content. Proceed with caution,
        it could be NSFW or (rarely) illegal where you live.
        This table updates itself about every 5-6 minutes, and the page also
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
        I am also working to try to incorporate a similar algorithm (albeit
        updated less frequently, for technical reasons)
        into LBRY itself, to see how it compares to the current trending algorithm.
      </p>

      <p>
        Current epoch: {epoch}<br>
      </p>

      <table>
        <col width="130">
        <tr style="font-weight: bold">  <td>Rank</td>   <td>Claim Name</td>  <td>Score</td> </tr>
     
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

        duration = time.time() - start_time
        time.sleep(300.0 - duration)

