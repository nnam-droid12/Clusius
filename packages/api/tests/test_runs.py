async def test_health(client) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_run_returns_queued_run(client) -> None:
    payload = {
        "workload_name": "showcase-agent",
        "model_ref": "qwen2.5-7b-instruct",
        "sla_p95_latency_ms": 2000.0,
        "sla_accuracy_floor": 0.9,
    }

    response = await client.post("/runs", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] in {"queued", "analyze", "done", "failed"}
    assert body["target_mode"] == "target"
    assert "id" in body


async def test_list_runs_includes_created_run(client) -> None:
    payload = {
        "workload_name": "showcase-agent",
        "model_ref": "qwen2.5-7b-instruct",
        "sla_p95_latency_ms": 2000.0,
        "sla_accuracy_floor": 0.9,
    }
    created = await client.post("/runs", json=payload)
    run_id = created.json()["id"]

    response = await client.get("/runs")

    assert response.status_code == 200
    ids = [r["id"] for r in response.json()]
    assert run_id in ids


async def test_get_run_returns_detail_with_trials_and_results(client) -> None:
    payload = {
        "workload_name": "showcase-agent",
        "model_ref": "qwen2.5-7b-instruct",
        "sla_p95_latency_ms": 2000.0,
        "sla_accuracy_floor": 0.9,
    }
    created = await client.post("/runs", json=payload)
    run_id = created.json()["id"]

    response = await client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == run_id
    assert body["trials"] == []


async def test_get_run_404_for_unknown_id(client) -> None:
    response = await client.get("/runs/does-not-exist")

    assert response.status_code == 404


async def test_get_result_404_before_any_result_recorded(client) -> None:
    payload = {
        "workload_name": "showcase-agent",
        "model_ref": "qwen2.5-7b-instruct",
        "sla_p95_latency_ms": 2000.0,
        "sla_accuracy_floor": 0.9,
    }
    created = await client.post("/runs", json=payload)
    run_id = created.json()["id"]

    response = await client.get(f"/runs/{run_id}/result.json")

    assert response.status_code == 404
