import matplotlib.pyplot as plt
import numpy as np
import numpy.random as rng

# Simulation parameters
num_claims = 100     # How many claims to simulate
num_epochs = 168    # Let's assume epochs are one hour

# Floor parameter
c = 10.0

# Decay parameter
K = 0.97

# Power parameter
a = 0.05


def soften(x):
    """
    Softening function
    """
    return np.log10(x + c)



def update_claim(claim, new_total_amount):
    """
    Update a claim in place, given its new total amount.
    """

    # Change in relative value
    delta = soften(new_total_amount) - soften(claim["total_amount"])
    claim["total_amount"] = new_total_amount

    # Decays towards zero unless kicked
    claim["trending_local"] = K*claim["trending_local"] + delta

    # Total amount counts, softly
    claim["trending_score"] = (new_total_amount**a)*claim["trending_local"]


def simulate_claims():
    """
    Simulate some claims and return a 2D array
    along with final trending_score for each claim.
    """

    # Total value of each claim at each epoch
    xs = np.zeros((num_claims, num_epochs))

    # Generate trajectories
    for i in range(num_claims):
        xs[i, 0] = 2.0 + 3.0*rng.randn()
        prob = 0.2*rng.rand()
        for j in range(1, num_epochs):
            xs[i, j] = xs[i, j-1]
            if rng.rand() <= prob:
                xs[i, j] += 0.05 + 0.3*rng.randn()
        xs[i, :] = np.exp(xs[i, :])

#    # Add trend
#    for i in range(num_claims):
#        slope = 0.05 + 0.05*rng.randn()
#        for j in range(0, num_epochs): # Yeah yeah loops
#            xs[i, j] = np.abs(xs[i, j] + slope*j)

    # Change overall scale of the values
    for i in range(num_claims):
        xs[i, :] *= np.exp(rng.randn())

    # Compute trending scores
    trending_scores = np.zeros(num_claims)
    for i in range(num_claims):
    
        # Initial state of the claim
        claim = { "total_amount":   0.0,
                  "trending_local": 0.0,
                  "trending_score": 0.0 }

        # Roll through time updating the claim
        # and updating the trending score
        for j in range(num_epochs):
            update_claim(claim, xs[i, j])
        trending_scores[i] = claim["trending_score"]

    return [ xs, trending_scores ]


if __name__ == "__main__":

#    claim = { "total_amount":   10.0,
#              "trending_local": 0.0,
#              "trending_score": 0.0 }

#    for i in range(100):
#        if i == 50:
#            update_claim(claim, 1.0)
#        else:
#            update_claim(claim, claim["total_amount"])
#        print(i+1, claim)

    # Simulate some claims. 2D array here, one row per claim
    xs, trending_scores = simulate_claims()
    print(trending_scores)

    # Compute ranks...lower is better. Yeah, I could have done some fancy
    # argsort or whatever but it doesn't matter
    ranks = np.empty(num_claims, dtype="int64")
    for i in range(num_claims):
        ranks[i] = np.sum(trending_scores > trending_scores[i])



    # Plot trajectories, highlighting the trending ones
    for i in range(num_claims):
        alpha, linewidth, label = 0.2, 1.0, None
        if ranks[i] == 0:
            alpha, linewidth, label = 1.0, 3.0, trending_scores[i]
        elif ranks[i] < 2:
            alpha, linewidth, label = 0.5, 2.0, trending_scores[i]

        plt.semilogy(np.arange(0, num_epochs)/24, xs[i, :],
                    "-", alpha=alpha, linewidth=linewidth,
                    label=label)

    plt.xlabel("Time (days)")
    plt.ylabel("total_amount")
    plt.legend(loc="upper left")
    plt.show()


