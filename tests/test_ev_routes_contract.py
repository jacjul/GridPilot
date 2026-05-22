from tests.route_contract_helpers import auth_headers, install_common_overrides


def test_ev_routes_contract(client, override_db_dependency):
    install_common_overrides()

    res_post = client.post(
        "/api/ev",
        headers=auth_headers(),
        json={"ev_name": "Model X", "kw_peak_loading": 11.0, "kwh_battery": 60.0},
    )
    assert res_post.status_code == 200

    res_list = client.get("/api/ev", headers=auth_headers())
    assert res_list.status_code == 200

    res_get = client.get("/api/ev/1", headers=auth_headers())
    assert res_get.status_code == 200

    res_patch = client.patch(
        "/api/ev/1",
        headers=auth_headers(),
        json={"ev_name": "Model Y"},
    )
    assert res_patch.status_code == 200

    res_delete = client.delete("/api/ev/1", headers=auth_headers())
    assert res_delete.status_code == 200

    downtime_create = {
        "ev_id": 1,
        "weekdays_mask": 31,
        "start_time": "08:00:00",
        "end_time": "10:00:00",
        "tz_name": "Europe/Berlin",
    }
    res_downtime_post = client.post(
        "/api/ev/1/downtime-rules",
        headers=auth_headers(),
        json=downtime_create,
    )
    assert res_downtime_post.status_code == 200

    res_downtime_get = client.get("/api/ev/1/downtime-rules", headers=auth_headers())
    assert res_downtime_get.status_code == 200
    assert isinstance(res_downtime_get.json(), list)

    res_downtime_patch = client.patch(
        "/api/ev/1/downtime-rules/10",
        headers=auth_headers(),
        json={
            "weekdays_mask": 63,
            "start_time": "09:00:00",
            "end_time": "11:00:00",
            "tz_name": "Europe/Berlin",
        },
    )
    assert res_downtime_patch.status_code == 200

    res_downtime_delete = client.delete("/api/ev/1/downtime-rules/10", headers=auth_headers())
    assert res_downtime_delete.status_code == 200


def test_ev_downtime_path_payload_mismatch_returns_400(client, override_db_dependency):
    install_common_overrides()

    res = client.post(
        "/api/ev/1/downtime-rules",
        headers=auth_headers(),
        json={
            "ev_id": 2,
            "weekdays_mask": 31,
            "start_time": "08:00:00",
            "end_time": "10:00:00",
            "tz_name": "Europe/Berlin",
        },
    )
    assert res.status_code == 400
