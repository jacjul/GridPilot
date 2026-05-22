from tests.route_contract_helpers import auth_headers, install_common_overrides


def test_pv_routes_contract(client, override_db_dependency):
    install_common_overrides()

    res_post = client.post(
        "/api/pv",
        headers=auth_headers(),
        json={
            "place": "Berlin",
            "declination": 30.0,
            "azimuth": 180.0,
            "kw_peak": 9.5,
            "einspeiseverguetung": 0.08,
        },
    )
    assert res_post.status_code == 200

    res_list = client.get("/api/pv", headers=auth_headers())
    assert res_list.status_code == 200
    assert isinstance(res_list.json(), list)

    res_get = client.get("/api/pv/1", headers=auth_headers())
    assert res_get.status_code == 200

    res_patch = client.patch(
        "/api/pv/1",
        headers=auth_headers(),
        json={"declination": 35.0},
    )
    assert res_patch.status_code == 200

    res_delete = client.delete("/api/pv/1", headers=auth_headers())
    assert res_delete.status_code == 200

    res_forecast_all = client.post("/api/forecastPV/", headers=auth_headers())
    assert res_forecast_all.status_code == 200

    res_forecast_single = client.post("/api/forecastPV/1", headers=auth_headers())
    assert res_forecast_single.status_code == 200
