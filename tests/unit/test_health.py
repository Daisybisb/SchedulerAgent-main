import SchedulerAgent_function.function_app as fa

def test_health_response():
    class DummyReq:
        pass
    resp = fa.health(DummyReq())
    assert resp.status_code == 200
    assert resp.mimetype == "application/json"
    assert resp.get_body().decode() == '{"status":"ok"}'
