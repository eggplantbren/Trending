import matplotlib.pyplot as plt
import numpy as np
import numpy.random as rng

# Simulation parameters
num_claims = 10     # How many claims to simulate
num_epochs = 50     # Let's assume epochs are 6 hours


# Trending algorithm parameters
scale_length = 4.0  # Exponential scale length of trending in epochs. 4 = 1 day.
lbc_power = 0.1     # Strength of effect of total LBC bid. Between 0 and 1 please


# Some vectors for dot producting with trajectories
# E.g., dot product of a trajectory with vec0=(0, 0, 0, ..., 1) just gives
# current total amount.

vec0 = np.zeros(num_epochs)
vec0[-1] = 1.0

# Exponential kernel, normalised to unity norm
# Dot producting with this gives a trending measure
exp_kernel = np.exp((np.arange(0, num_epochs, dtype="float64") - num_epochs)\
                        /scale_length)
exp_kernel /= np.sqrt(np.sum(exp_kernel**2))
vec1 = exp_kernel

def goodness(ys):
    """
    This is the function that takes a trajectory of total_amount in LBC
    and returns a measure of "recent goodness" - i.e., my trending algorithm
    sorts based on the result of this function.
    Input: ys, a numpy array of total LBC amount measured over many epochs
    """
    
    # Transform trajectories
    # First take log10 of total_amount + 10, then make mean zero, then norm
    # The plus 10 is so something can't trend if its total_amount is tiny
    ys_transformed = np.log10(ys + 10.0)
    ys_transformed -= np.mean(ys_transformed)
    ys_transformed /= np.sqrt(np.sum(ys_transformed**2))

    # Two dot products (one is really just current total amount)
    dot0 = np.dot(ys, vec0)
    dot1 = np.dot(ys_transformed, vec1)

    # I think dot1 is now a good measure of local (relative to self) trending.
    # Now multiply (softened) current total amount back in
    return (dot0**lbc_power)*dot1




def simulate_claims():
    """
    Simulate some claims and return a 2D array
    """

    # Some simulation parameters
    alpha = 0.99
    beta = np.sqrt(1.0 - alpha**2)

    # Total value of each claim at each epoch
    ys = np.zeros((num_claims, num_epochs))

    # Generate ln(y) from an AR(1) with trend
    for i in range(num_claims):
        ys[i, 0] = rng.randn()
        for j in range(1, num_epochs):
            ys[i, j] = alpha*ys[i, j-1] + beta*rng.randn()
    ys = np.exp(ys)

    # Add slopes
    for i in range(num_claims):
        slope = 0.05 + 0.05*rng.randn()
        for j in range(0, num_epochs): # Yeah yeah loops
            ys[i, j] = np.abs(ys[i, j] + slope*j)

    return ys






if __name__ == "__main__":
    # Simulate some claims. 2D array here, one row per claim
    ys = simulate_claims()

    # Measure their goodnesses
    scalars = np.empty(num_claims)
    for i in range(num_claims):
        scalars[i] = goodness(ys[i, :])


    # Compute ranks...lower is better. Yeah, I could have done some fancy
    # argsort or whatever but it doesn't matter
    ranks = np.empty(num_claims, dtype="int64")
    for i in range(num_claims):
        ranks[i] = np.sum(scalars > scalars[i])



    # Plot trajectories, highlighting the trending ones
    for i in range(num_claims):
        alpha, linewidth, label = 0.2, 1.0, None
        if ranks[i] == 0:
            alpha, linewidth, label = 1.0, 3.0, "Most trending"
        elif ranks[i] < 2:
            alpha, linewidth, label = 0.5, 2.0, "Second most trending"

        plt.plot(np.arange(0, num_epochs)/4, ys[i, :],
                    "-", alpha=alpha, linewidth=linewidth,
                    label=label)

    plt.xlabel("Time (days)")
    plt.ylabel("log10(total_amount + 10 LBC)")
    plt.legend(loc="upper left")
    plt.show()

