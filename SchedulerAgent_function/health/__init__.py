import azure.functions as func
import json
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    # 取得版本號，可於 Azure Portal 設定 APP_VERSION 變數
    version = os.environ.get("APP_VERSION", "1.0.0")
    # 回傳健康狀態與服務資訊
    return func.HttpResponse(
        json.dumps({
            "status": "ok",
            "service": "SchedulerAgent",
            "version": version
        }, ensure_ascii=False),
        status_code=200,
        mimetype="application/json"
    )
