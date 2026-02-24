import io
import json
import gzip
import re
import os
import requests
import boto3
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, status
from fastapi.params import Query

from bdi_api.settings import Settings

settings = Settings()

s4 = APIRouter(
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Something is wrong with the request"},
    },
    prefix="/api/s4",
    tags=["s4"],
)

@s4.post("/aircraft/download")
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
    """Same as s1 but store to an aws s3 bucket taken from settings
    and inside the path `raw/day=20231101/`

    NOTE: you can change that value via the environment variable `BDI_S3_BUCKET`
    """
    base_url = settings.source_url + "/2023/11/01/"
    s3_bucket = settings.s3_bucket
    s3_prefix_path = "raw/day=20231101/"
    # TODO

    s3 = boto3.client("s3", region_name= "us-east-1")

    response = requests.get(base_url)
    response.raise_for_status()

    files = re.findall(r'href="(.*?\.json\.gz)"', response.text)
    files = files[:file_limit]

    for filename in files:
        file_url = base_url + filename
        file_response = requests.get(file_url)
        file_response.raise_for_status()

        key = f"raw/day=20231101/{filename}"

        s3.put_object(
            Bucket=s3_bucket,
            Key=key,
            Body=io.BytesIO(file_response.content),
        )

    return "OK"

@s4.post("/aircraft/prepare")
def prepare_data() -> str:
    """Obtain the data from AWS s3 and store it in the local `prepared` directory
    as done in s1.

    All the `/api/s1/aircraft/` endpoints should work as usual
    """
    # TODO
    s3_bucket = settings.s3_bucket
    s3_prefix_path = "raw/day=20231101/"
    base_url = settings.source_url + "/2023/11/01/"
    response = requests.get(base_url)
    response.raise_for_status()

    files = re.findall(r'href="(.*?\.json\.gz)"', response.text)

    aircraft_data = []

    for filename in files:
        key = f"{s3_prefix_path}{filename}"

        s3_object = s3.get_object(
            Bucket=s3_bucket,
            Key=key,
        )

        with gzip.GzipFile(fileobj=io.BytesIO(s3_object["Body"].read())) as gz:
            content = json.loads(gz.read().decode("utf-8"))
            aircraft_data.extend(content.get("aircraft", []))

    return "OK"