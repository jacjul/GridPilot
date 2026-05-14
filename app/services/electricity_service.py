import pandas as pd
import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import update, select, and_
from typing import Any
from datetime import datetime, timezone

from app.schemas.electricity import ElectricityCreateform, MarketZone
from app.schemas.user import UserMe
from app.models.price_electricity import ElectricityPrice, DynamicPricePoints


class ElectricityService():
    def _assert_user_data_is_correct(self, formdata: ElectricityCreateform):
        if formdata.price_typ == "fixed" and formdata.fixed_price is None:
            raise HTTPException(status_code=422, detail="When price_typ is fixed a price is needed")
        if formdata.price_typ == "dynamic_EPEX" and formdata.fixed_price is not None:
            raise HTTPException(status_code=422, detail="When price_typ is dynamic EPEX the fixed price wont be used")

        if formdata.fixed_price is not None and formdata.fixed_price < 0:
            raise HTTPException(status_code=422, detail="Price has to be higher 0")

    def _prepare_for_db_add(self, formdata, user_id: int) -> dict[str, Any]:
        if formdata.name is None:
            if formdata.price_typ == "fixed":
                name = f"fixed {str(formdata.fixed_price)}"
            else:
                if formdata.market_zone:
                    name = f"dynamic_EPEX {formdata.market_zone}"
                else:
                    name = "dynamic_EPEX DE-LU"
        else:
            name = formdata.name

        market_zone = None
        if formdata.price_typ == "dynamic_EPEX":
            market_zone = formdata.market_zone if formdata.market_zone is not None else MarketZone.DE_LU

        data = formdata.model_dump(exclude={"name", "market_zone"}, exclude_unset=True, exclude_none=True)
        if formdata.price_typ == "dynamic_EPEX":
            data.update({"name": name, "market_zone": market_zone, "owner_id": user_id})
        else:
            data.update({"name": name, "owner_id": user_id})
        return data

    async def _set_old_price_inactive(self, user_id, db):
        await db.execute(update(ElectricityPrice).where(ElectricityPrice.owner_id == user_id).values(is_active=False))
        await db.flush()

    async def create_electricity_tarif(self, formdata: ElectricityCreateform, user: UserMe, db: AsyncSession):
        self._assert_user_data_is_correct(formdata)

        data_to_upload = self._prepare_for_db_add(formdata, user.id)

        await self._set_old_price_inactive(user.id, db=db)

        try:
            new_price = ElectricityPrice(**data_to_upload, is_active=True, updated_at=datetime.now(timezone.utc))
            db.add(new_price)
            await db.commit()
            await db.refresh(new_price)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Tariff conflict")
        except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error when writing to DB")
        return {"message": "success", "new_price_id": new_price.id}

    def _resolve_window(self, start_time=None, end_time=None):
        now = datetime.now(timezone.utc)
        start_dt = start_time or now
        end_dt = end_time or (start_dt + pd.Timedelta(days=2))

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        if end_dt <= start_dt:
            raise HTTPException(status_code=422, detail="Invalid cause end time smaller then start time")

        return start_dt, end_dt

    async def _load_cached_points(self, market_zone, db, start_time, end_time):
        stmt = (
            select(DynamicPricePoints)
            .where(
                and_(
                    DynamicPricePoints.market_zone == market_zone,
                    DynamicPricePoints.timestamp >= start_time,
                    DynamicPricePoints.timestamp <= end_time,
                )
            )
            .order_by(DynamicPricePoints.timestamp)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def _fetch_EPEX_data(self, market_zone, db, start_time, end_time):
        cached_points = await self._load_cached_points(market_zone, db, start_time, end_time)

        existing_dates = {point.timestamp.date() for point in cached_points}
        requested_dates = [date_item.date() for date_item in pd.date_range(start_time.date(), end_time.date(), freq="D")]
        missing_dates = [date_item for date_item in requested_dates if date_item not in existing_dates]

        if missing_dates:
            missing_dates.sort()
            missing_ranges = []
            range_start = missing_dates[0]
            previous_date = missing_dates[0]

            for current_date in missing_dates[1:]:
                if (current_date - previous_date).days == 1:
                    previous_date = current_date
                    continue
                missing_ranges.append((range_start, previous_date))
                range_start = current_date
                previous_date = current_date
            missing_ranges.append((range_start, previous_date))

            market_zone_code = market_zone.value if isinstance(market_zone, MarketZone) else str(market_zone)

            async with httpx.AsyncClient() as client:
                for range_start_date, range_end_date in missing_ranges:
                    base_url = (
                        "https://api.energy-charts.info/price"
                        f"?bzn={market_zone_code}&start={range_start_date.strftime('%Y-%m-%d')}"
                        f"&end={range_end_date.strftime('%Y-%m-%d')}"
                    )
                    response = await client.get(base_url)
                    if response.status_code != 200:
                        raise HTTPException(status_code=503, detail="API calling error")

                    result = response.json()
                    seconds = result.get("unix_seconds")
                    prices = result.get("price")
                    if not isinstance(seconds, list) or not isinstance(prices, list):
                        raise HTTPException(status_code=502, detail="Invalid EPEX response format")
                    if len(seconds) != len(prices):
                        raise HTTPException(status_code=502, detail="EPEX data length mismatch")

                    datetimes = pd.to_datetime(seconds, unit="s", utc=True).to_pydatetime().tolist()
                    for dt, point_price in zip(datetimes, prices):
                        await db.merge(
                            DynamicPricePoints(
                                market_zone=market_zone,
                                timestamp=dt,
                                price=point_price,
                            )
                        )

            await db.commit()
            cached_points = await self._load_cached_points(market_zone, db, start_time, end_time)

        datetimes = [point.timestamp for point in cached_points]
        prices = [point.price for point in cached_points]
        return datetimes, prices

    async def get_current_DynamicPricePoints(self, user: UserMe, db: AsyncSession):

        result = await db.execute(select(ElectricityPrice)
                                  .where(and_(ElectricityPrice.owner_id == user.id,
                                              ElectricityPrice.price_typ == "dynamic_EPEX")))
        elec_dynamic = result.scalar_one_or_none()

        if not elec_dynamic:
            raise HTTPException(status_code=404, detail="There is no dynamic Tarif")

        start_time, end_time = self._resolve_window()
        datetimes, price = await self._fetch_EPEX_data(elec_dynamic.market_zone, db, start_time, end_time)
        return {"timestamps": datetimes, "price": price}
