from httpx import AsyncClient


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_cors_allows_configured_origin(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_create_run_returns_queued_run(client: AsyncClient) -> None:
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


async def test_list_runs_includes_created_run(client: AsyncClient) -> None:
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


async def test_get_run_returns_detail_with_trials_and_results(client: AsyncClient) -> None:
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


async def test_get_run_404_for_unknown_id(client: AsyncClient) -> None:
    response = await client.get("/runs/does-not-exist")

    assert response.status_code == 404


async def test_get_result_404_before_any_result_recorded(client: AsyncClient) -> None:
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


async def test_get_report_404_before_any_report_generated(client: AsyncClient) -> None:
    payload = {
        "workload_name": "showcase-agent",
        "model_ref": "qwen2.5-7b-instruct",
        "sla_p95_latency_ms": 2000.0,
        "sla_accuracy_floor": 0.9,
    }
    created = await client.post("/runs", json=payload)
    run_id = created.json()["id"]

    response = await client.get(f"/runs/{run_id}/report")

    assert response.status_code == 404


async def test_list_results_includes_workload_identity_and_results(client: AsyncClient) -> None:
    from clusius_api.db.models import Result, Run, Workload

    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        workload = Workload(name="showcase-agent", model_ref="Qwen/Qwen2.5-0.5B-Instruct")
        session.add(workload)
        await session.flush()
        run = Run(
            workload_id=workload.id,
            status="completed",
            target_mode="target",
            sla_p95_latency_ms=1000.0,
            sla_accuracy_floor=0.9,
            search_budget_trials=4,
            selected_backend="llamacpp",
        )
        session.add(run)
        await session.flush()
        session.add(
            Result(run_id=run.id, kind="baseline_x86", result_json={"tokens_per_second": 30.0})
        )
        session.add(
            Result(run_id=run.id, kind="arm_winner", result_json={"tokens_per_second": 120.0})
        )
        await session.commit()
        run_id = run.id

    response = await client.get("/results")

    assert response.status_code == 200
    matching = [r for r in response.json() if r["id"] == run_id]
    assert len(matching) == 1
    entry = matching[0]
    assert entry["workload_name"] == "showcase-agent"
    assert entry["model_ref"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert entry["selected_backend"] == "llamacpp"
    assert {r["kind"] for r in entry["results"]} == {"baseline_x86", "arm_winner"}


async def test_list_results_excludes_non_completed_runs(client: AsyncClient) -> None:
    payload = {
        "workload_name": "showcase-agent",
        "model_ref": "qwen2.5-7b-instruct",
        "sla_p95_latency_ms": 2000.0,
        "sla_accuracy_floor": 0.9,
    }
    created = await client.post("/runs", json=payload)
    run_id = created.json()["id"]

    response = await client.get("/results")

    ids = [r["id"] for r in response.json()]
    assert run_id not in ids
