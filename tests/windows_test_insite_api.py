"""
Tests methods related to class InsiteAPI
"""

import csv
import logging
import os
import sys
from pathlib import Path

import pytest
import requests
import requests_mock

from src.insiteapi.aou_package import AouPackage
from src.insiteapi.insite_api import InSiteAPI


def test_insite_api(
    logger, real_aou_package, fake_json_I, fake_json_II, fake_data_directory
) -> None:

    def on_data_completion(progress: bool | int | str) -> None:
        if isinstance(progress, bool):
            logger.info("Authorization complete.")
        elif isinstance(progress, int):
            logger.info(f"progress: {progress} % complete")
        elif isinstance(progress, str):
            logger.info(progress)

    api_obj: InSiteAPI = InSiteAPI(
        aou_package=real_aou_package,
        log=logger,
        report_fn=on_data_completion,
    )
    assert isinstance(api_obj, InSiteAPI)

    fake_url_I: str = (
        real_aou_package.endpoint
        + "?_sort=lastModified&_includeTotal=TRUE&_count=1000&awardee="
        + real_aou_package.awardee
    )

    # To test "link" extraction & processing, fake a SECOND URL...
    fake_url_II: str = (
        "https://fake.url?_sort=lastModified&_includeTotal=TRUE&_count=1000&awardee="
        + real_aou_package.awardee
    )

    # ...wrap into the expected dict structure...
    next_url: dict = {"relation": "next", "url": fake_url_II}

    # ...and tuck this dict into the FIRST json package.
    fake_json_I["link"] = [next_url]

    # Create a mock web API service.
    with requests_mock.Mocker() as m:
        # Register a mocked service that defines TWO URLs.
        # The API Package used to instantiate the InSiteAPI object will point the object
        # to the first URL, which will return the first JSON package, containing a link to the SECOND URL,
        # which returns the second JSON package, which HAS no link & therefore stops the processing.
        m.register_uri(method="GET", url=fake_url_I, json=fake_json_I, status_code=200)
        m.register_uri(
            method="GET", url=fake_url_II, json=fake_json_II, status_code=200
        )

        api_obj.run()

    api_obj.output_data(fake_data_directory)
    assert os.path.exists(fake_data_directory)

    for file in os.listdir(fake_data_directory):
        full_file_path: str = os.path.join(fake_data_directory, file)
        data: list[dict] = []

        with open(full_file_path, encoding="utf-8") as f:
            data = list(csv.DictReader(f))

        assert len(data) == 2
        this_org: dict = data[0]
        assert isinstance(this_org, dict)
        assert "organization" in this_org


def test_insite_api_malformed_json(
    logger, real_aou_package, fake_json, fake_data_directory
) -> None:
    def on_auth_completion(progress: bool | int | str) -> None:
        if isinstance(progress, bool):
            logger.info("Authorization complete.")
        elif isinstance(progress, int):
            logger.info(f"progress: {progress} % complete")
        elif isinstance(progress, str):
            logger.info(progress)

    api_obj: InSiteAPI = InSiteAPI(
        aou_package=real_aou_package,
        log=logger,
        report_fn=on_auth_completion,
    )
    assert isinstance(api_obj, InSiteAPI)

    fake_url: str = (
        real_aou_package.endpoint
        + "?_sort=lastModified&_includeTotal=TRUE&_count=1000&awardee="
        + real_aou_package.awardee
    )
    # Remove 'resourceType' from json dict.
    del fake_json["resourceType"]

    with requests_mock.Mocker() as m:
        m.register_uri(method="GET", url=fake_url, json=fake_json, status_code=200)

        with pytest.raises(RuntimeError):
            api_obj.run()


def test_insite_api_no_report_fn(
    logger, real_aou_package, fake_json_no_total, fake_data_directory
) -> None:

    api_obj: InSiteAPI = InSiteAPI(
        aou_package=real_aou_package,
        log=logger,
    )
    assert isinstance(api_obj, InSiteAPI)

    fake_url: str = (
        real_aou_package.endpoint
        + "?_sort=lastModified&_includeTotal=TRUE&_count=1000&awardee="
        + real_aou_package.awardee
    )

    with requests_mock.Mocker() as m:
        m.register_uri(
            method="GET", url=fake_url, json=fake_json_no_total, status_code=200
        )
        api_obj.run()

    api_obj.output_data(fake_data_directory)
    assert os.path.exists(fake_data_directory)

    for file in os.listdir(fake_data_directory):
        full_file_path: str = os.path.join(fake_data_directory, file)
        data: list[dict] = []

        with open(full_file_path, encoding="utf-8") as f:
            data = list(csv.DictReader(f))

        assert len(data) == 1
        this_org: dict = data[0]
        assert isinstance(this_org, dict)
        assert "organization" in this_org


def test_insite_api_other_errors(
    logger, real_aou_package, fake_json, fake_data_directory
) -> None:
    def on_auth_completion(progress: bool | int | str) -> None:
        if isinstance(progress, bool):
            logger.info("Authorization complete.")
        elif isinstance(progress, int):
            logger.info(f"progress: {progress} % complete")
        elif isinstance(progress, str):
            logger.info(progress)

    api_obj: InSiteAPI = InSiteAPI(
        aou_package=real_aou_package,
        log=logger,
        report_fn=on_auth_completion,
    )
    assert isinstance(api_obj, InSiteAPI)

    fake_url: str = (
        real_aou_package.endpoint
        + "?_sort=lastModified&_includeTotal=TRUE&_count=1000&awardee="
        + real_aou_package.awardee
    )

    with requests_mock.Mocker() as m:
        # Pretend we NEVER get a 200 and ensure API throws RuntimeError.
        m.register_uri(method="GET", url=fake_url, json=fake_json, status_code=400)

        with pytest.raises(RuntimeError):
            api_obj.run()


def test_insite_api_stop(logger, real_aou_package, fake_json) -> None:
    def on_auth_completion(progress: bool | int | str) -> None:
        if isinstance(progress, bool):
            logger.info("Authorization complete.")
        elif isinstance(progress, int):
            logger.info(f"progress: {progress} % complete")
            logger.debug("Invoking 'stop' method.")
            api_obj.stop()
        elif isinstance(progress, str):
            logger.info(progress)

    api_obj: InSiteAPI = InSiteAPI(
        aou_package=real_aou_package,
        log=logger,
        report_fn=on_auth_completion,
    )
    assert isinstance(api_obj, InSiteAPI)

    fake_url: str = (
        real_aou_package.endpoint
        + "?_sort=lastModified&_includeTotal=TRUE&_count=1000&awardee="
        + real_aou_package.awardee
    )

    # Wrap the fake URL into the expected dict...
    next_url: dict = {"relation": "next", "url": fake_url}

    # ...and tuck this dict into the JSON package.
    fake_json["link"] = [next_url]

    # Create a mock web API service.
    with requests_mock.Mocker() as m:
        # Register a mocked service.
        # Theory is that the API Package used to instantiate the InSiteAPI object will point the object
        # to the fake URL, which will return the fake JSON package, containing A LINK TO THE SAME URL,
        # which will cause an infinite loop--until we invoke the stop() method as part of the on_auth_completion callback.
        m.register_uri(method="GET", url=fake_url, json=fake_json, status_code=200)

        api_obj.run()


def test_insite_api_timeouts(
    logger, real_aou_package, fake_json, fake_data_directory
) -> None:
    def on_auth_completion(progress: bool | int | str) -> None:
        if isinstance(progress, bool):
            logger.info("Authorization complete.")
        elif isinstance(progress, int):
            logger.info(f"progress: {progress} % complete")
        elif isinstance(progress, str):
            logger.info(progress)

    api_obj: InSiteAPI = InSiteAPI(
        aou_package=real_aou_package,
        log=logger,
        report_fn=on_auth_completion,
    )
    assert isinstance(api_obj, InSiteAPI)

    fake_url: str = (
        real_aou_package.endpoint
        + "?_sort=lastModified&_includeTotal=TRUE&_count=1000&awardee="
        + real_aou_package.awardee
    )

    # Simulate that we get a 500 error, then a 200 on retry.
    logger.debug("Simulating status code 500, then 200.")
    with requests_mock.Mocker() as m:
        m.register_uri(
            method="GET",
            url=fake_url,
            response_list=[
                {"status_code": 500},
                {"json": fake_json, "status_code": 200},
            ],
        )
        api_obj.run()

    # Simulate we NEVER get a 200--forcing a RuntimeError after multiple attempts.
    logger.debug("Simulating status code 500 forever.")
    with requests_mock.Mocker() as m:
        m.register_uri(method="GET", url=fake_url, json=fake_json, status_code=500)

        with pytest.raises(RuntimeError):
            api_obj.run()

    # Simulate receiving an exception during request.
    logger.debug("Simulating exception during request.")
    with requests_mock.Mocker() as m:
        m.register_uri(
            method="GET", url=fake_url, exc=requests.exceptions.ConnectionError
        )

        with pytest.raises(RuntimeError):
            api_obj.run()

    # Simulate receiving an exception during RETRY.
    logger.debug("Simulating exception during retry.")
    with requests_mock.Mocker() as m:
        m.register_uri(
            method="GET",
            url=fake_url,
            response_list=[
                {"status_code": 500},
                {"exc": requests.exceptions.ConnectionError},
            ],
        )

        with pytest.raises(RuntimeError):
            api_obj.run()


if __name__ == "__main__":
    # Set up logger for use with test methods.
    right_here: str = os.path.dirname(__file__)

    if not "tests" in right_here:
        right_here = str(Path(right_here) / "tests")

    log_filename: str = str(Path(right_here) / "testing.log")

    my_logger: logging.Logger = logging.getLogger(log_filename)

    # Logging to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_format = logging.Formatter(
        "%(module)s - %(levelname)s - %(funcName)s - %(message)s"
    )
    console_handler.setFormatter(console_format)
    my_logger.addHandler(console_handler)

    # Logging to a file
    logfile_format = logging.Formatter(
        fmt="%(asctime)s - %(module)s - %(levelname)s - %(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logfile_handler = logging.FileHandler(log_filename)
    logfile_handler.setFormatter(logfile_format)
    my_logger.addHandler(logfile_handler)
    my_logger.setLevel(logging.DEBUG)

    # Copy a real config file.
    config_file_real: str = str(Path(os.path.dirname(__file__)) / "config_real.ini")

    if not os.path.exists(config_file_real):
        pytest.fail(f"Missing real config file '{config_file_real}'")

    ap: AouPackage = AouPackage(log=my_logger, config_file=config_file_real)

    fj: dict = {
        "resourceType": "Bundle",
        "total": 4,
        "entry": [
            {
                "resource": {
                    "organization": "FakeUniversity",
                    "patientName": "Ima Patient",
                    "city": "San Diego",
                    "state": "CA",
                }
            },
            {
                "resource": {
                    "organization": "FakeUniversity",
                    "patientName": "Youda Patient",
                    "city": "Silver City",
                    "state": "CA",
                }
            },
            {
                "resource": {
                    "organization": "",
                    "patientName": "Ahma Patient",
                    "city": "UNSET",
                    "state": "CA",
                }
            },
            {
                "resource": {
                    "organization": "",
                    "patientName": "Alma Patient",
                    "city": "Salmon City",
                    "state": "CA",
                }
            },
        ],
    }

    fdd: str = str(Path(right_here) / "test_data")
    fjI: dict = {
        "resourceType": "Bundle",
        "total": 2,
        "entry": [
            {
                "resource": {
                    "organization": "FakeUniversity",
                    "patientName": "Ima Patient",
                    "city": "San Diego",
                    "state": "CA",
                }
            },
            {
                "resource": {
                    "organization": "FakeUniversity",
                    "patientName": "Youda Patient",
                    "city": "Silver City",
                    "state": "CA",
                }
            },
        ],
    }
    fjII: dict = {
        "resourceType": "Bundle",
        "total": 2,
        "entry": [
            {
                "resource": {
                    "organization": "",
                    "patientName": "Ahma Patient",
                    "city": "UNSET",
                    "state": "CA",
                }
            },
            {
                "resource": {
                    "organization": "",
                    "patientName": "Alma Patient",
                    "city": "Salmon City",
                    "state": "CA",
                }
            },
        ],
    }
    fjnt: dict = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "organization": "FakeUniversity",
                    "patientName": "Ima Patient",
                    "city": "San Diego",
                    "state": "CA",
                }
            },
            {
                "resource": {
                    "patientName": "Whooda Patient",
                    "city": "Silverado",
                    "state": "CA",
                }
            },
        ],
    }

    my_logger.info("*** test_insite_api ***")
    test_insite_api(
        logger=my_logger,
        real_aou_package=ap,
        fake_json_I=fjI,
        fake_json_II=fjII,
        fake_data_directory=fdd,
    )

    my_logger.info("*** test_insite_api_malformed_json ***")
    test_insite_api_malformed_json(
        logger=my_logger, real_aou_package=ap, fake_json=fj, fake_data_directory=fdd
    )

    my_logger.info("*** test_insite_api_no_report_fn ***")
    test_insite_api_no_report_fn(
        logger=my_logger,
        real_aou_package=ap,
        fake_json_no_total=fjnt,
        fake_data_directory=fdd,
    )

    my_logger.info("*** test_insite_api_pther_errors ***")
    test_insite_api_other_errors(
        logger=my_logger, real_aou_package=ap, fake_json=fj, fake_data_directory=fdd
    )

    my_logger.info("*** test_insite_api_stop ***")
    test_insite_api_stop(logger=my_logger, real_aou_package=ap, fake_json=fj)

    my_logger.info("*** test_insite_api_timeouts ***")
    test_insite_api_timeouts(
        logger=my_logger, real_aou_package=ap, fake_json=fj, fake_data_directory=fdd
    )
