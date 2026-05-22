from tests.route_contract_helpers import auth_headers, install_common_overrides


def test_battery_routes_contract(client, override_db_dependency):
    install_common_overrides()

    res_post = client.post(
        "/api/bess",
        headers=auth_headers(),
        json={"name": "B1", "kw_peak_charge": 5.0, "kwh": 10.0},
    )
    assert res_post.status_code == 200

    res_list = client.get("/api/bess", headers=auth_headers())
    assert res_list.status_code == 200

    res_get = client.get("/api/bess/1", headers=auth_headers())
    assert res_get.status_code == 200

    res_patch = client.patch("/api/bess/1", headers=auth_headers(), json={"kwh": 12.0})
    assert res_patch.status_code == 200

    res_delete = client.delete("/api/bess/1", headers=auth_headers())
    assert res_delete.status_code == 200
