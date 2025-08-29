import azure.functions as func
import pandas as pd
import json
import io
from azure.storage.blob import BlobServiceClient
from SchedulerAgent_function.services.scheduler_engine import clean_rest_data, apply_preferences

# 匿名授權的 FunctionApp 初始化
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Blob 儲存設定（請填入正確的連線字串）
import os
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "scheduler"
BLOB_NAME = "SchedulerInfoData.sample.xlsx"

# 輔助函式：從位元組讀取 Excel
def load_excel_from_bytes(file_bytes):
    return pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')

# 輔助函式：從本地測試檔案讀取 Excel
def load_local_excel():
    return pd.read_excel('tests/data/SchedulerInfoData.sample.xlsx', engine='openpyxl')

# 輔助函式：從 Azure Blob 儲存讀取 Excel
def load_excel_from_blob():
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=BLOB_NAME)
    blob_data = blob_client.download_blob().readall()
    return load_excel_from_bytes(blob_data)

# /api/health 端點
@app.function_name(name="health")
@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse('{"status":"ok"}', status_code=200, mimetype="application/json")

# /api/schedule 端點，支援 GET 與 POST 請求
@app.function_name(name="schedule")
@app.route(route="schedule", methods=["GET", "POST"])
def schedule(req: func.HttpRequest) -> func.HttpResponse:
    try:
        preferences = {"熟練度高": 5, "資歷深": 3}
        source = req.params.get("source", "local")

        if req.method == "POST":
            file = req.files.get("file")
            if not file:
                return func.HttpResponse(
                    json.dumps({"error": "請提供 Excel 檔案作為 'file' 欄位上傳"}, ensure_ascii=False),
                    mimetype="application/json",
                    status_code=400
                )
            df = load_excel_from_bytes(file.read())
        elif source == "blob":
            df = load_excel_from_blob()
        else:
            df = load_local_excel()

        df = clean_rest_data(df)
        result_df = apply_preferences(df, preferences)

        return func.HttpResponse(
            result_df.to_json(orient="records", force_ascii=False),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500
        )
