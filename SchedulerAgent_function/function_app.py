# SchedulerAgent_function/function_app.py
import json
import logging
import os
from typing import TYPE_CHECKING

# 嘗試載入 azure.functions；若本地未安裝，提供 stub 以便單元測試與 Pylance 不報 app 未定義
try:
    import azure.functions as func  # 在 Azure 環境一定會有
except Exception:
    func = None  # type: ignore[assignment]

# 只在型別檢查時導入，避免執行期因缺套件報錯，同時讓 Pylance 有型別資訊
if TYPE_CHECKING:
    import azure.functions as azf

# 無論是否有 azure.functions，都確保 app 這個符號存在，避免「app 未定義」
if func is None:
    # 簡單的裝飾器 stub，讓本地（無 azure.functions）時不會出錯
    class _StubApp:
        def route(self, *args, **kwargs):
            def _decorator(fn):
                return fn
            return _decorator
    app = _StubApp()
else:
    app = func.FunctionApp()

# 匯入資料載入邏輯
from .services.data_loader import load_scheduler_data


# ---- 健康檢查端點（匿名） ----
if func is not None:
    @app.route(route="ping", auth_level=func.AuthLevel.ANONYMOUS)
    def ping(req: "azf.HttpRequest") -> "azf.HttpResponse":  # 引號內的型別只在型別檢查時生效
        return func.HttpResponse("OK", status_code=200)
else:
    # 本地無 azure.functions 的時候，給單元測試/本地快速呼叫一個替代實作
    def ping(req=None):
        return "OK"


# ---- 資料預覽端點（需 function key）----
# 回傳兩張表在「忽略第一欄」後的列數/欄數，快速驗證環境變數與 Blob 讀取
if func is not None:
    @app.route(route="preview", auth_level=func.AuthLevel.FUNCTION)
    def preview(req: "azf.HttpRequest") -> "azf.HttpResponse":
        try:
            rest_df, reliever_df = load_scheduler_data()  # 自動判別：有環境變數則讀 Blob；否則讀本地樣本
            payload = {
                "source": "blob"
                if all(os.getenv(k) for k in ("BLOB_CONN_STRING", "DATA_CONTAINER", "DATA_BLOB_PATH"))
                else "local-sample",
                "rest_day": {"rows": int(rest_df.shape[0]), "cols": int(rest_df.shape[1])},
                "reliever": {"rows": int(reliever_df.shape[0]), "cols": int(reliever_df.shape[1])},
            }
            return func.HttpResponse(json.dumps(payload), status_code=200, mimetype="application/json")
        except Exception as e:
            logging.exception("讀取資料失敗")
            return func.HttpResponse(str(e), status_code=500)
else:
    # 本地無 azure.functions 的時候，給單元測試/本地快速呼叫一個替代實作
    def preview(req=None):
        rest_df, reliever_df = load_scheduler_data()
        return {
            "source": "blob"
            if all(os.getenv(k) for k in ("BLOB_CONN_STRING", "DATA_CONTAINER", "DATA_BLOB_PATH"))
            else "local-sample",
            "rest_day": {"rows": int(rest_df.shape[0]), "cols": int(rest_df.shape[1])},
            "reliever": {"rows": int(reliever_df.shape[0]), "cols": int(reliever_df.shape[1])},
        }
