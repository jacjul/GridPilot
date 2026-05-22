from tests.route_contract_helpers import auth_headers, install_common_overrides


def test_optimization_route_contract(client, override_db_dependency):
    install_common_overrides()

    res = client.post(
        "/api/optimization/day_ahead?horizon_days=1&enforce_terminal_bess_soc=true",
        headers=auth_headers(),
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "ok"
