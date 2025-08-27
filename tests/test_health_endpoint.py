import requests

# 請將此處網址改為您的本機或雲端 Function App 端點
ENDPOINTS = [
    "https://scheduleragent.azurewebsites.net/api/health",  # 本機測試
    # "https://<您的-function-app>.azurewebsites.net/api/health",  # 雲端測試，請取消註解並填入實際網址
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
