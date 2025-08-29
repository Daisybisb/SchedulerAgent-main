import requests
import os

def test_cloud_health():
    app_name = os.environ.get("AZURE_FUNCTIONAPP_NAME")
    url = f"https://{app_name}.azurewebsites.net/api/health"
    resp = requests.get(url)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
