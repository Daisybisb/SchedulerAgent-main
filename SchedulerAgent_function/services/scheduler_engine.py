import pandas as pd

def clean_rest_data(df):
    """
    清理休假資料，移除缺漏值並轉換日期格式。
    """
    df = df.dropna(subset=['隊員', '日期'])
    df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
    df = df.dropna(subset=['日期'])
    return df

def score_row(row, preferences):
    """
    根據偏好關鍵字計算分數。
    """
    score = 0
    for key, weight in preferences.items():
        if key in str(row.get('偏好', '')):
            score += weight
    return score

def apply_preferences(df, preferences):
    """
    套用偏好條件並依分數排序。
    """
    df['分數'] = df.apply(lambda row: score_row(row, preferences), axis=1)
    return df.sort_values(by='分數', ascending=False)
