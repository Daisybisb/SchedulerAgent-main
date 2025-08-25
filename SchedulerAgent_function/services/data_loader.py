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
