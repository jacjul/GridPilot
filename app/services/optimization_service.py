from pulp import *
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload 

from app.schemas.user import UserMe
from app.models.user import User
from app.services.electricity_service import ElectricityService
from app.services.photovoltaik_service import PVForecastService
class OptimizationService():

    async def _load_current_user(self, user_id:int, db:AsyncSession):

        stmt = select(User).options(
            selectinload(User.electric_vehicle_owned),
            selectinload(User.battery_owned), 
            selectinload(User.photovoltaik_owned),
            selectinload(User.electricity_owned)
        ).where(User.id == user_id)

        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if  user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user

    def _build_optimizer_input(self, current_user: User) -> dict[str, Any]:
        # Convert ORM objects to plain structures so the optimizer can work with pure data.
         
        return {
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "lastname": current_user.lastname,
                "username": current_user.username,
            },
            "photovoltaik": [
                {
                    "id": pv.id,
                    "latitude": pv.latitude,
                    "longitude": pv.longitude,
                    "declination": pv.declination,
                    "azimuth": pv.azimuth,
                    "kw_peak": pv.kw_peak,
                }
                for pv in current_user.photovoltaik_owned
            ],
            "electric_vehicles": [
                {
                    "id": ev.id,
                    "ev_name": ev.ev_name,
                    "kw_peak_loading": ev.kw_peak_loading,
                    "kwh_battery": ev.kwh_battery,
                }
                for ev in current_user.electric_vehicle_owned
            ],
            "batteries": [
                {
                    "id": battery.id,
                    "name": battery.name,
                    "kw_peak_charge": battery.kw_peak_charge,
                    "kw_peak_discharge": battery.kw_peak_discharge,
                    "kwh": battery.kwh,
                }
                for battery in current_user.battery_owned
            ],
            "electricity_prices": [
                 {
                    "name": price.name,
                    "price_typ": price.price_typ,
                    "fixed_price": price.fixed_price,
                    "is_active" : price.is_active,
                    "market_zone": price.market_zone
                }
                for price in current_user.electricity_owned
            ],
        }

    async def run_day_ahead(self, user:UserMe,db:AsyncSession):
        current_user = await self._load_current_user(user_id = user.id, db=db)

        optimizer_input = self._build_optimizer_input(current_user)
        user_data = optimizer_input.get("user", {})
        photovoltaik = optimizer_input.get("photovoltaik", [])
        electric_vehicles = optimizer_input.get("electric_vehicles", [])
        batteries = optimizer_input.get("batteries", [])
        electricity_prices = optimizer_input.get("electricity_prices", [])

        has_pv: bool = bool(photovoltaik)
        has_bess: bool = bool(batteries)
        has_ev: bool = bool(electric_vehicles)
        has_electricity: bool = bool(electricity_prices)

        if not has_electricity:
            raise HTTPException(status_code=404, detail="an electricity tarif is necessary")
        
        steps = 96
        hours = range(steps)

        ## electricity fixed
        active_electricity = next((tariff for tariff in electricity_prices if tariff.get("is_active") is True),None)

        if active_electricity is None:
            raise HTTPException(status_code=400, detail="No active electricity tariff found")
        
        if active_electricity["price_typ"] =="fixed" and active_electricity["fixed_price"] != None:
            price = [active_electricity["fixed_price"] ] *steps

        # electricity dynamic
        if active_electricity["price_typ"] == "dynamic_EPEX":
            electricity_service = ElectricityService()
            # this gets the timestamps from the latest 15 min block 
            dict_electricity = await electricity_service.get_current_DynamicPricePoints(user, db)
            timestamps = dict_electricity.get("timestamps")
            prices = dict_electricity.get("price")

        #battery
        if has_bess:
            kw_peak_charge = 0
            kw_peak_discharge = 0
            kwh = 0
            for bess in batteries:
                kw_peak_charge += bess.kw_peak_charge
                kw_peak_discharge =bess.kw_peak_discharge
                kwh = bess.kwh
            SOC_initial= SOC_final = 0.4 * kwh

        if has_ev:
            # here i have to add blocking times later on 
            # for now all ev just treated as 
            kw_peak_loading = 0 
            kwh_battery  = 0 
            for ev in electric_vehicles:
                kw_peak_loading +=ev.kw_peak_loading
                kwh_battery += ev.kwh_battery

            SOC_initial = kwh_battery *0.3 # um 0 Uhr
            SOC_end = kwh_battery * 0.8 # um 7 Uhr 

        if has_pv: 
            pv_service = PVForecastService()
            forecasts = await pv_service.get_forecast_for_pvs(db=db,pv_owner_id = user.id, target_days=None)







       

    
        

































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

