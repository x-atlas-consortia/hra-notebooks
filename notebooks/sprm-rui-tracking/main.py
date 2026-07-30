"""Checks CDE gallery HuBMAP datasets for RUI registration on their direct ancestor sample."""

install_requirements()

import pandas as pd
import requests
import subprocess
import sys
from pathlib import Path
from pprint import pprint
import os
import json

REQUIREMENTS_FILE = Path(__file__).parent / "requirements.txt"
CDE_GALLERY_DATASETS = "https://raw.githubusercontent.com/x-atlas-consortia/hra-spatial-omics-data/refs/heads/main/output-data/cde-gallery-datasets.json"
ENTITY_API_BASE_URL = "https://entity.api.hubmapconsortium.org/entities/"
OUPUT_DIR = "output"
OUTPUT_FILE_JSON = "cde_sprm_look_up.json"
OUTPUT_FILE_CSV = "cde_sprm_look_up.csv"


def install_requirements() -> None:
    """Install the packages listed in requirements.txt into the current interpreter."""
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)]
    )


def send_web_request(url: str) -> dict | None:
    """GET a URL and return the parsed JSON body, or None if the request failed."""
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()

    print(f"Failed calling {url} with status code: {response.status_code}")
    return None


def get_hubmap_ids(url: str) -> list[str]:
    """Fetch the CDE gallery dataset list and return the HuBMAP IDs of deepcell datasets."""
    cde_data = send_web_request(url)

    return [
        ".".join(item["slug"].split("_")[0:3])
        for item in cde_data
        if item["study"] == "hubmap-mirror-deepcell"
    ]


def find_sample_rui_status(entity_id: str) -> dict | None:
    """Walk up entity_id's direct-ancestor chain to the first Sample and return its RUI status and metadata."""
    response = send_web_request(ENTITY_API_BASE_URL + entity_id)
    if response is None:
        return None

    direct_ancestor = response["direct_ancestors"][0]

    if direct_ancestor["entity_type"] != "Sample":
        return find_sample_rui_status(direct_ancestor["hubmap_id"])

    ancestor_response = send_web_request(
        ENTITY_API_BASE_URL + direct_ancestor["hubmap_id"]
    )
    if ancestor_response is None:
        return None

    if ancestor_response.get("sample_category") == "section":
        section_ancestors = ancestor_response.get("direct_ancestors") or []
        section_ancestor = section_ancestors[0] if section_ancestors else None
        if (
            section_ancestor is not None
            and section_ancestor["entity_type"] == "Sample"
            and section_ancestor.get("sample_category") == "block"
        ):
            block_response = send_web_request(
                ENTITY_API_BASE_URL + section_ancestor["hubmap_id"]
            )
            if block_response is None:
                return None
            ancestor_response = block_response

    result = {
        "sample_is_rui_registered": "rui_location" in ancestor_response,
        "sample_created_by_user_displayname": ancestor_response[
            "created_by_user_displayname"
        ],
        "sample_created_by_user_email": ancestor_response["created_by_user_email"],
        "sample_entity_type": ancestor_response["entity_type"],
        "sample_hubmap_id": ancestor_response["hubmap_id"],
        "sample_uuid": ancestor_response["uuid"],
        "sample_category": ancestor_response["sample_category"],
    }
    return result


def get_metadata_from_api(hubmap_ids: list[str]) -> dict[str, dict | None]:
    """For each HuBMAP ID, walk up its ancestor chain to the first Sample and report RUI status."""
    look_up = {}

    for hubmap_id in hubmap_ids:

        print(
            f"Now sending request for {hubmap_id} with: {ENTITY_API_BASE_URL + hubmap_id}"
        )
        look_up[hubmap_id] = find_sample_rui_status(hubmap_id)

    return look_up


def save_to_table(look_up: dict[str, dict | None]) -> None:
    columns = [
        "dataset_id",
        "sample_is_rui_registered",
        "sample_created_by_user_displayname",
        "sample_created_by_user_email",
        "sample_entity_type",
        "sample_hubmap_id",
        "sample_uuid",
        "sample_category",
    ]

    rows = []
    for dataset_id, sample_data in look_up.items():
        sample_data = sample_data or {}
        rows.append(
            {
                "dataset_id": dataset_id,
                "sample_is_rui_registered": sample_data.get("sample_is_rui_registered"),
                "sample_created_by_user_displayname": sample_data.get(
                    "sample_created_by_user_displayname"
                ),
                "sample_created_by_user_email": sample_data.get(
                    "sample_created_by_user_email"
                ),
                "sample_entity_type": sample_data.get("sample_entity_type"),
                "sample_hubmap_id": sample_data.get("sample_hubmap_id"),
                "sample_uuid": sample_data.get("sample_uuid"),
                "sample_category": sample_data.get("sample_category"),
            }
        )

    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(f"{OUPUT_DIR}/{OUTPUT_FILE_CSV}", index=False)


def main() -> None:
    """Report RUI status for each SPRM HuBMAP dataset in the CDE Gallery."""
    hubmap_ids = get_hubmap_ids(CDE_GALLERY_DATASETS)
    look_up = get_metadata_from_api(hubmap_ids)
    os.makedirs(OUPUT_DIR, exist_ok=True)
    pprint(look_up)

    with open(f"{OUPUT_DIR}/{OUTPUT_FILE_JSON}", "w") as file:
        json.dump(look_up, file, indent=4)
    save_to_table(look_up)


if __name__ == "__main__":
    main()
