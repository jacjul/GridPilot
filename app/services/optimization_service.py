from pulp import *

hours= range(6)
prices = [10, 12, 30, 50, 20, 10]
demand = [4, 4, 4, 4, 4, 4]

battery_capacity = 6
max_charge = 2
max_discharge = 2
initial_soc = 0

model = LpProblem("Minimize_Cost_BESS", LpMinimize)

BESS_charge = LpVariable.dicts("BESS_charge",hours, lowBound=0 )
BESS_discharge = LpVariable.dicts("BESS_discharge", hours, lowBound=0)
grid = LpVariable.dicts("grid", hours, lowBound=0)
soc = LpVariable.dicts("soc", hours, lowBound=0)
# Optimization 

model += lpSum(prices[h]*grid[h] for h in hours)

# Constraints 

for h in hours:

    model += (grid[h]+BESS_discharge[h]==BESS_charge[h]+demand[h])

    model += BESS_charge[h] < max_charge
    model += BESS_discharge[h] < max_discharge

    if h ==0:
        
        model += (soc[h] == initial_soc + BESS_charge[h] -BESS_discharge[h]) 
    else: 
        model += (soc[h] == soc[h-1]+ BESS_charge[h]- BESS_discharge[h])

    model += (soc[h] <=battery_capacity)

model.solve()

