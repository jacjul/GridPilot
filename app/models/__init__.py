"""Import all model modules so SQLAlchemy registers mappers on import.

This module is intentionally simple: importing `app.models` will execute
the submodule imports below and ensure cross-model relationships can be
resolved when mappers are configured (useful for worker processes).
"""
from . import user
from . import price_electricity
from . import photovoltaik
from . import PV_forecast
from . import electric_vehicle
from . import battery
from . import token
from . import optimization

__all__ = [
    "user",
    "price_electricity",
    "photovoltaik",
    "PV_forecast",
    "electric_vehicle",
    "battery",
    "token",
    "optimization",
]
from .user import User
from .price_electricity import ElectricityPrice, DynamicPricePoints, MarketZone
from .photovoltaik import Photovoltaik
from .electric_vehicle import ElectricVehicle
from .battery import Battery
from .token import Token 