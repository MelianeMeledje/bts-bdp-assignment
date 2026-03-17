from fastapi import APIRouter, status
from pydantic import BaseModel
import pandas as pd
import json
from pathlib import Path

from bdi_api.settings import Settings

settings = Settings()

s8 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s8",
    tags=["s8"],
)


class AircraftReturn(BaseModel):
    icao: str
    registration: str | None
    type: str | None
    owner: str | None
    manufacturer: str | None
    model: str | None


class AircraftCO2Return(BaseModel):
    icao: str
    hours_flown: float
    co2: float | None


# Path to silver layer Parquet file
SILVER_PATH = Path("/tmp/silver/aircraft_enriched.parquet")
FUEL_CONSUMPTION_PATH = Path("/tmp/aircraft_type_fuel_consumption_rates.json")


@s8.get("/aircraft/")
def list_aircraft(num_results: int = 100, page: int = 0) -> list[AircraftReturn]:
    """List all aircraft with enriched data, ordered by ICAO ascending.

    The data should come from the silver layer (processed by the Airflow DAG).
    Paginated with `num_results` per page and `page` number (0-indexed).
    """

    if not SILVER_PATH.exists():
        return []
    
    # TODO: Read enriched aircraft data from your storage (S3 silver, database, or local)
    df = pd.read_parquet(SILVER_PATH)

    # TODO: Order by ICAO ascending
    df = df.sort_values("icao")

    # TODO: Apply pagination using num_results and page
    start = page * num_results
    end = start + num_results
    df_page = df.iloc[start:end]

    result = [
        AircraftReturn(
            icao=row["icao"],
            registration=row.get("registration"),
            type=row.get("type"),
            owner=row.get("owner"),
            manufacturer=row.get("manufacturer"),
            model=row.get("model"),
        )
        for _, row in df_page.iterrows()
    ]
    return result


@s8.get("/aircraft/{icao}/co2")
def get_aircraft_co2(icao: str, day: str) -> AircraftCO2Return:
    """Calculate CO2 emissions for a given aircraft on a specific day.

    Computation:
    - Each row in the tracking data represents a 5-second observation
    - hours_flown = (number_of_observations * 5) / 3600
    - Look up `galph` (gallons per hour) from fuel consumption rates using the aircraft's ICAO type
    - fuel_used_kg = hours_flown * galph * 3.04
    - co2_tons = (fuel_used_kg * 3.15) / 907.185
    - If fuel consumption rate is not available for this aircraft type, return None for co2
    """
    # TODO: Count observations for this ICAO on the given day
    df = pd.read_parquet(SILVER_PATH)
    df_aircraft = df[(df["icao"] == icao) & (df["day"] == day)]
    num_observations = len(df_aircraft)

    # TODO: Calculate hours_flown
    hours_flown = (num_observations * 5) / 3600

    # TODO: Look up fuel consumption rate by aircraft type
    if not FUEL_CONSUMPTION_PATH.exists():
        fuel_rates = {}
    else:
        with open(FUEL_CONSUMPTION_PATH) as f:
            fuel_rates = json.load(f)

    aircraft_type = df_aircraft["type"].iloc[0] if not df_aircraft.empty else None
    galph = fuel_rates.get(aircraft_type) if aircraft_type else None

    # TODO: Calculate CO2 emissions
    if galph is None:
        co2_tons = None
    else:
        fuel_used_kg = hours_flown * galph * 3.04
        co2_tons = (fuel_used_kg * 3.15) / 907.185

    return AircraftCO2Return(
        icao=icao,
        hours_flown=hours_flown,
        co2=co2_tons,
    )
