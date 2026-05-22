from tests.route_contract_helpers import auth_headers, install_common_overrides


def test_electricity_routes_contract(client, override_db_dependency):
    install_common_overrides()

    res_post = client.post(
        "/api/electricity",
        headers=auth_headers(),
        json={"price_typ": "fixed", "fixed_price": 0.3, "name": "main"},
    )
    assert res_post.status_code == 200

    res_list = client.get("/api/electricity", headers=auth_headers())
    assert res_list.status_code == 200
    assert isinstance(res_list.json(), list)

    res_get = client.get("/api/electricity/1", headers=auth_headers())
    assert res_get.status_code == 200

    res_patch = client.patch(
        "/api/electricity/1",
        headers=auth_headers(),
        json={"name": "updated", "is_active": True},
    )
    assert res_patch.status_code == 200

    res_delete = client.delete("/api/electricity/1", headers=auth_headers())
    assert res_delete.status_code == 200
