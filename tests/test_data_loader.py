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
