# SchedulerAgent-main
這是一個使用 Azure Function App 部署的 Python 專案，包含自動化測試與 GitHub Actions 部署流程。
│  requirements-dev.txt
# 根目錄：requirements-dev.txt（本機/CI 測試用）
-r SchedulerAgent_function/requirements.txt
pytest>=8.4
pytest-html>=4.1
SchedulerAgent-main/tests/data/SchedulerInfoData.sample.xlsx
├─.github
│ 	└─workflows
│			└─deploy.yml
name: Deploy SchedulerAgent Function App
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    env:
      AZURE_FUNCTIONAPP_NAME: SchedulerAgent              # ← 改成你的現有 Function App 名稱
      AZURE_FUNCTIONAPP_PACKAGE_PATH: SchedulerAgent_function
      PYTHON_VERSION: '3.11'
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-html
      - name: Run tests and generate HTML report
        env:
          PYTHONPATH: ${{ github.workspace }}
        run: |
          mkdir -p reports
          pytest --html=reports/test-report.html --self-contained-html
      - name: Upload pytest report artifact
        uses: actions/upload-artifact@v4
        with:
          name: pytest-html-report
          path: reports/test-report.html
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - name: Deploy to Azure Functions
        uses: Azure/functions-action@v1
        with:
          app-name: ${{ env.AZURE_FUNCTIONAPP_NAME }}
          package: ${{ env.AZURE_FUNCTIONAPP_PACKAGE_PATH }}
├─docs
│		└─deploy-pipeline.md
# Deploy Pipeline（SchedulerAgent）
本文檔說明從 GitHub 到 Azure Functions 的自動打包與部署流程，並包含三種視角的圖示（Mermaid）。
## 1) Flowchart
```mermaid
flowchart TD
    A[開發者 push/PR 到 main] --> B[GitHub Actions 觸發 workflow: deploy.yml]
    B --> C[Checkout repository]
    C --> D[Setup Python 3.11]
    D --> E[Install dependencies<br/>pip install -r requirements.txt<br/>pip install pytest pytest-html]
    E --> F[Run tests<br/>PYTHONPATH=${{ github.workspace }} pytest --html=reports/test-report.html]
    F -->|測試通過| G[Upload pytest report artifact]
    F -->|測試失敗| Z1[Job 失敗，通知/審查]:::bad
    G --> H[Azure Login (azure/login@v1)<br/>使用 secrets.AZURE_CREDENTIALS]
    H --> I[Package: SchedulerAgent_function<br/>(由 Azure/functions-action 內部打包為 release.zip)]
    I --> J[Deploy to Azure Functions<br/>Azure/functions-action@v1]
    J --> K[Azure Zip Deploy (Kudu)<br/>將 release.zip 上傳到儲存體容器: github-actions-deploy / scm-releases]
    K --> L[Zip 解壓至 /site/wwwroot]
    L --> M[Function Host 重啟與冷啟（Warmup）]
    M --> N[就緒: 端點可用 (/ping, /preview)]
    N --> O[可選: 手動或自動驗證呼叫 API]
    classDef bad fill:#ffe5e5,stroke:#ff6b6b,color:#b00020;
├─SchedulerAgent_function
│   	│  function_app.py
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
│ 	│  requirements.txt
# SchedulerAgent_function/requirements.txt（替代建議）
azure-functions~=1.21
pandas~=2.2     # 若 2.1 專案相容，也可寫 ~=2.1（依你目前碼用到的 API）
openpyxl~=3.1
azure-storage-blob~=12.20
# 若有其他套件需求，請在此補充
│   	│  __init__.py
(空白檔案)
│   	└─services
│			└─data_loader.py
# SchedulerAgent_function/services/data_loader.py
from __future__ import annotations
import os
from io import BytesIO
from typing import Dict, Tuple
import pandas as pd
SHEET_NAMES = ("RestDayApplication", "RelieverRestDayApplication")
class DataSourceError(RuntimeError):
    pass
def _read_excel_from_local(sample_path: str) -> Dict[str, pd.DataFrame]:
    if not os.path.exists(sample_path):
        raise DataSourceError(f"本地樣本檔不存在：{sample_path}")
    xls = pd.ExcelFile(sample_path)
    result = {}
    for sheet in SHEET_NAMES:
        if sheet not in xls.sheet_names:
            raise DataSourceError(f"缺少工作表：{sheet}（檔案：{sample_path}）")
        df = pd.read_excel(xls, sheet_name=sheet)
        # 忽略第一欄（僅用於區分崗位，可省略）
        if df.shape[1] < 2:
            raise DataSourceError(f"工作表 {sheet} 欄位不足，忽略第一欄後無可用資料")
        result[sheet] = df.iloc[:, 1:].copy()
    return result
def _read_excel_from_blob(conn_str: str, container: str, blob_path: str) -> Dict[str, pd.DataFrame]:
    try:
        from azure.storage.blob import BlobServiceClient  # 延遲載入，避免本地測試硬相依
    except Exception as e:
        raise DataSourceError(
            "未安裝 azure-storage-blob，或環境不支援。請在 requirements.txt 加入 azure-storage-blob 並重新部署。"
        ) from e
    try:
        service = BlobServiceClient.from_connection_string(conn_str)
        client = service.get_blob_client(container=container, blob=blob_path)
        stream = BytesIO(client.download_blob().readall())
    except Exception as e:
        raise DataSourceError(f"下載 Blob 失敗：container={container}, path={blob_path}. {e}") from e
    xls = pd.ExcelFile(stream)
    result = {}
    for sheet in SHEET_NAMES:
        if sheet not in xls.sheet_names:
            raise DataSourceError(f"雲端檔案缺少工作表：{sheet}（blob：{blob_path}）")
        df = pd.read_excel(xls, sheet_name=sheet)
        if df.shape[1] < 2:
            raise DataSourceError(f"工作表 {sheet} 欄位不足，忽略第一欄後無可用資料（blob：{blob_path}）")
        result[sheet] = df.iloc[:, 1:].copy()
    return result
def load_scheduler_data(
    prefer_blob: bool | None = None,
    local_sample_path: str | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    回傳 (rest_day_df, reliever_rest_day_df)
    判斷來源順序：
    1) 若 prefer_blob=True 或（未指定且偵測到環境變數）→ 讀取 Azure Blob
    2) 否則 → 讀取本地樣本 tests/data/SchedulerInfoData.sample.xlsx
    """
    # 預設樣本位置
    default_sample = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "tests", "data", "SchedulerInfoData.sample.xlsx")
    )
    sample_path = local_sample_path or default_sample
    blob_conn_str = os.getenv("BLOB_CONN_STRING")
    blob_container = os.getenv("DATA_CONTAINER")
    blob_path = os.getenv("DATA_BLOB_PATH")
    # 是否啟用 Blob
    use_blob = False
    if prefer_blob is True:
        use_blob = True
    elif prefer_blob is None:
        use_blob = bool(blob_conn_str and blob_container and blob_path)
    if use_blob:
        data = _read_excel_from_blob(blob_conn_str, blob_container, blob_path)
    else:
        data = _read_excel_from_local(sample_path)
    rest = data[SHEET_NAMES[0]]
    reliever = data[SHEET_NAMES[1]]
    return rest, reliever
└─tests
│  test_data_loader.py
# tests/test_data_loader.py
import os
import pytest
# 確保可匯入專案模組
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from SchedulerAgent_function.services.data_loader import load_scheduler_data, DataSourceError
def test_local_sample_can_be_loaded_and_first_column_ignored():
    # 預設走本地樣本（因為未設定 Blob 環境變數）
    rest_df, reliever_df = load_scheduler_data(prefer_blob=False)
    assert rest_df is not None and not rest_df.empty
    assert reliever_df is not None and not reliever_df.empty
    # 兩個表忽略第一欄後仍應有欄位
    assert rest_df.shape[1] >= 1
    assert reliever_df.shape[1] >= 1
@pytest.mark.skipif(
    not (os.getenv("BLOB_CONN_STRING") and os.getenv("DATA_CONTAINER") and os.getenv("DATA_BLOB_PATH")),
    reason="未設定 Blob 環境變數，略過雲端資料讀取測試",
)
def test_blob_can_be_loaded_when_env_set():
    rest_df, reliever_df = load_scheduler_data(prefer_blob=True)
    assert rest_df is not None and not rest_df.empty
    assert reliever_df is not None and not reliever_df.empty
│  test_function_app.py
# tests/test_function_app.py
import os
import sys
# 將專案根目錄加入 Python 路徑
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from importlib import import_module
def test_can_import_function_app():
    pkg = import_module("SchedulerAgent_function")
    assert hasattr(pkg, "function_app"), "SchedulerAgent_function 應該要有 function_app 屬性"
    from SchedulerAgent_function import function_app
    assert function_app is not None
└─data
└─SchedulerInfoData.sample.xlsx

## 📁 專案結構
- 根目錄包含 `.gitignore`, `LICENSE`, `README.md`, `requirements-dev.txt`
- `.github/workflows/deploy.yml`：GitHub Actions 自動部署流程
- `docs/deploy-pipeline.md`：部署流程說明與 Mermaid 圖示
- `SchedulerAgent_function/`：Azure Function App 主程式與資料載入邏輯
- `tests/`：單元測試與本地樣本資料

## 🚀 部署流程
使用 GitHub Actions 自動部署至 Azure Functions，包含：
- 安裝依賴與執行測試
- 產出 HTML 測試報告並上傳
- 登入 Azure 並部署 Function App

## 🧪 測試機制
- 使用 `pytest` 與 `pytest-html` 執行測試並產出報告
- 測試涵蓋本地與 Azure Blob 資料來源的載入邏輯
- 支援本地快速測試與雲端環境驗證
