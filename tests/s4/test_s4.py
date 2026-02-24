from fastapi.testclient import TestClient


class TestS4Student:

    def test_download_endpoint(self, client: TestClient) -> None:
        with client as client:
            response = client.post("/api/s4/aircraft/download?file_limit=2")
            assert not response.is_error, "Error at S4 download endpoint"

    def test_prepare_endpoint(self, client: TestClient) -> None:
        with client as client:
            response = client.post("/api/s4/aircraft/prepare")
            assert not response.is_error, "Error at S4 prepare endpoint"


class TestS4Integration:

    def test_s1_after_s4(self, client: TestClient) -> None:
        with client as client:
            # download from s4
            r1 = client.post("/api/s4/aircraft/download?file_limit=5")
            assert not r1.is_error, "S4 download failed"

            # prepare from s4
            r2 = client.post("/api/s4/aircraft/prepare")
            assert not r2.is_error, "S4 prepare failed"

            # now s1 must work
            r3 = client.get("/api/s1/aircraft")
            assert not r3.is_error, "S1 aircraft endpoint failed after S4"

            data = r3.json()
            assert isinstance(data, list), "Aircraft result is not a list"
            assert len(data) > 0, "Aircraft list is empty"

            for field in ["icao", "registration", "type"]:
                assert field in data[0], f"Missing '{field}' field."