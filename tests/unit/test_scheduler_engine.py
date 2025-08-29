import pandas as pd
import unittest
from SchedulerAgent_function.services.scheduler_engine import clean_rest_data, apply_preferences

class TestSchedulerEngine(unittest.TestCase):

    def test_clean_rest_data(self):
        data = {
            "隊員": ["Alice", None, "Charlie"],
            "日期": ["2024-08-01", "invalid_date", None],
            "偏好": ["熟練度高", "資歷深", "熟練度高"]
        }
        df = pd.DataFrame(data)
        cleaned_df = clean_rest_data(df)

        self.assertEqual(len(cleaned_df), 1)
        self.assertEqual(cleaned_df.iloc[0]["隊員"], "Alice")

    def test_apply_preferences(self):
        data = {
            "隊員": ["Alice", "Bob", "Charlie"],
            "偏好": ["熟練度高", "資歷深", "熟練度高"]
        }
        df = pd.DataFrame(data)
        preferences = {"熟練度高": 5, "資歷深": 3}
        result_df = apply_preferences(df, preferences)

        top_person = result_df.iloc[0]["隊員"]
        self.assertIn(top_person, ["Alice", "Charlie"])

        scores = result_df["分數"].tolist()
        self.assertIn(5, scores)
        self.assertIn(3, scores)

if __name__ == "__main__":
    unittest.main()
