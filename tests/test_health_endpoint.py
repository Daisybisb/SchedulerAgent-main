import os
import requests

# 這裡自動組合健康檢查端點網址
ENDPOINTS = [
    f"https://{os.environ.get('AZURE_FUNCTIONAPP_NAME')}.azurewebsites.net/api/health"
]

def test_health(url):
    try:
        resp = requests.get(url, timeout=10)
        assert resp.status_code == 200, f"狀態碼錯誤：{resp.status_code}"
        data = resp.json()
        assert data.get("status") == "ok", f"status 欄位錯誤：{data.get('status')}"
        assert data.get("service") == "SchedulerAgent", f"service 欄位錯誤：{data.get('service')}"
        print(f"[PASS] {url} 健康檢查通過，版本：{data.get('version')}")
    except Exception as e:
        print(f"[FAIL] {url} 測試失敗：{e}")

if __name__ == "__main__":
    for url in ENDPOINTS:
        test_health(url)
