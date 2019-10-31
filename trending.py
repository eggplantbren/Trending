import matplotlib.pyplot as plt
import numpy as np
import numpy.random as rng


num_claims = 10
num_epochs = 50     # Let's assume epochs are 6 hours
scale_length = 4.0  # Exponential scale length is a day

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



# Transformed trajectories
# First take log10 of total_amount + 10, then make mean zero, then norm
# The plus 10 is so something can't trend if its total_amount is tiny
ys_transformed = np.log10(ys + 10.0)
for i in range(num_claims):
    ys_transformed[i, :] -= np.mean(ys_transformed[i, :])
    ys_transformed[i, :] /= np.sqrt(np.sum(ys_transformed[i, :]**2))



# Dot product trajectories with some stuff
# E.g., dot product of a trajectory with vec0=(0, 0, 0, ..., 1) just gives
# current total amount.

vec0 = np.zeros(num_epochs)
vec0[-1] = 1.0

# Exponential kernel, normalised to unity norm
exp_kernel = np.exp((np.arange(0, num_epochs, dtype="float64") - num_epochs)/scale_length)
exp_kernel /= np.sqrt(np.sum(exp_kernel**2))
vec1 = exp_kernel

# This is surely a matrix multiplication
dots0 = np.empty(num_claims)
dots1 = np.empty(num_claims)
for i in range(num_claims):
    dots0[i] = np.dot(ys[i, :], vec0)
    dots1[i] = np.dot(ys_transformed[i, :], vec1)

# I think dots1 is now a good measure of local (relative to self) trending.
# Now multiply (softened) current total amount back in
scalar = dots0**0.1*dots1

# Compute ranks...lower is better
ranks = np.empty(num_claims, dtype="int64")
for i in range(num_claims):
    ranks[i] = np.sum(scalar > scalar[i])

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

