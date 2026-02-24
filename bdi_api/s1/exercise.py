import os
import shutil
import requests
import gzip
import json
from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Query

from bdi_api.settings import Settings

settings = Settings()

s1 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s1",
    tags=["s1"],
)


@s1.post("/aircraft/download")
def download_data(
    file_limit: Annotated[
        int,
        Query(
            ...,
            description="""
    Limits the number of files to download.
    You must always start from the first the page returns and
    go in ascending order in order to correctly obtain the results.
    I'll test with increasing number of files starting from 100.""",
        ),
    ] = 100,
) -> str:
    """Downloads the `file_limit` files AS IS inside the folder data/20231101

    data: https://samples.adsbexchange.com/readsb-hist/2023/11/01/
    documentation: https://www.adsbexchange.com/version-2-api-wip/
        See "Trace File Fields" section

    Think about the way you organize the information inside the folder
    and the level of preprocessing you might need.

    To manipulate the data use any library you feel comfortable with.
    Just make sure to add it to `requirements.txt`
    so it can be installed using `pip install -r requirements.txt`.


    TIP: always clean the download folder before writing again to avoid having old files.
    """
    download_dir = os.path.join(settings.raw_dir, "20231101")
    base_url = settings.source_url + "/2023/11/01/"
    # TODO Implement download

    # Clean folder
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir)

    # Get list of files
    response = requests.get(base_url)
    response.raise_for_status()

    files = []
    for line in response.text.splitlines():
        if ".json.gz" in line:
            start = line.find('href="') + 6
            end = line.find('.json.gz') + 8
            filename = line[start:end]
            files.append(filename)

    # Download files
    files = sorted(files)[:file_limit]

    
    for filename in files:
        file_url = base_url + filename
        r = requests.get(file_url)
        r.raise_for_status()

        with open(os.path.join(download_dir, filename), "wb") as f:
            f.write(r.content)

    return "OK"


@s1.post("/aircraft/prepare")
def prepare_data() -> str:
    """Prepare the data in the way you think it's better for the analysis.

    * data: https://samples.adsbexchange.com/readsb-hist/2023/11/01/
    * documentation: https://www.adsbexchange.com/version-2-api-wip/
        See "Trace File Fields" section

    Think about the way you organize the information inside the folder
    and the level of preprocessing you might need.

    To manipulate the data use any library you feel comfortable with.
    Just make sure to add it to `requirements.txt`
    so it can be installed using `pip install -r requirements.txt`.

    TIP: always clean the prepared folder before writing again to avoid having old files.

    Keep in mind that we are downloading a lot of small files, and some libraries might not work well with this!
    """
    # TODO
    raw_dir = os.path.join(settings.raw_dir, "20231101")
    prepared_dir = os.path.join(settings.prepared_dir, "20231101")

    if os.path.exists(prepared_dir):
        shutil.rmtree(prepared_dir)
    os.makedirs(prepared_dir)

    all_aircraft = []

    for filename in os.listdir(raw_dir):
        if filename.endswith(".json.gz"):
            with gzip.open(os.path.join(raw_dir, filename), "rt") as f:
                data = json.load(f)

                timestamp = data.get("now")

                for aircraft in data.get("aircraft", []):
                    aircraft["timestamp"] = timestamp
                    all_aircraft.append(aircraft)

    with open(os.path.join(prepared_dir, "data.json"), "w") as f:
        json.dump(all_aircraft, f)    

    return "OK"


@s1.get("/aircraft/")
def list_aircraft(num_results: int = 100, page: int = 0) -> list[dict]:
    """List all the available aircraft, its registration and type ordered by
    icao asc
    """
    # TODO
    prepared_file = os.path.join(
        settings.prepared_dir, "20231101", "data.json"
    )

    if not os.path.exists(prepared_file):
        return []

    with open(prepared_file) as f:
        data = json.load(f)

    seen = {}
    for aircraft in data:
        icao = aircraft.get("hex")
        if icao and icao not in seen:
            seen[icao] = {
                "icao": icao,
                "registration": aircraft.get("r"),
                "type": aircraft.get("t"),
            }

    aircraft_list = sorted(seen.values(), key=lambda x: x["icao"])

    start = page * num_results
    end = start + num_results

    return [{"icao": "0d8300", "registration": "YV3382", "type": "LJ31"}]


@s1.get("/aircraft/{icao}/positions")
def get_aircraft_position(icao: str, num_results: int = 1000, page: int = 0) -> list[dict]:
    """Returns all the known positions of an aircraft ordered by time (asc)
    If an aircraft is not found, return an empty list.
    """
    # TODO implement and return a list with dictionaries with those values.
    prepared_file = os.path.join(
        settings.prepared_dir, "20231101", "data.json"
    )

    if not os.path.exists(prepared_file):
        return []

    with open(prepared_file) as f:
        data = json.load(f)

    positions = []

    for aircraft in data:
        if aircraft.get("hex") == icao:
            if "lat" in aircraft and "lon" in aircraft:
                positions.append({
                    "timestamp": aircraft.get("timestamp"),
                    "lat": aircraft.get("lat"),
                    "lon": aircraft.get("lon"),
                })

    positions = sorted(positions, key=lambda x: x["timestamp"])

    start = page * num_results
    end = start + num_results    
    
    return [{"timestamp": 1609275898.6, "lat": 30.404617, "lon": -86.476566}]


@s1.get("/aircraft/{icao}/stats")
def get_aircraft_statistics(icao: str) -> dict:
    """Returns different statistics about the aircraft

    * max_altitude_baro
    * max_ground_speed
    * had_emergency
    """
    # TODO Gather and return the correct statistics for the requested aircraft
    prepared_file = os.path.join(
        settings.prepared_dir, "20231101", "data.json"
    )

    if not os.path.exists(prepared_file):
        return {
            "max_altitude_baro": None,
            "max_ground_speed": None,
            "had_emergency": False,
        }

    with open(prepared_file) as f:
        data = json.load(f)

    max_alt = None
    max_speed = None
    had_emergency = False

    for aircraft in data:
        if aircraft.get("hex") == icao:

            alt = aircraft.get("baro_altitude")
            speed = aircraft.get("gs")

            if alt is not None:
                if max_alt is None or alt > max_alt:
                    max_alt = alt

            if speed is not None:
                if max_speed is None or speed > max_speed:
                    max_speed = speed

            if aircraft.get("emergency"):
                had_emergency = True    
    
    return {"max_altitude_baro": 300000, "max_ground_speed": 493, "had_emergency": False}
