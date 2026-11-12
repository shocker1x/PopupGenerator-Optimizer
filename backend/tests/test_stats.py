import unittest

from app.services.stats import compare_variants


class BayesianStatsTests(unittest.TestCase):
    def test_small_samples_never_recommend_a_winner(self):
        result = compare_variants(
            [
                {"version_id": "a", "label": "A", "impressions": 30, "submissions": 8},
                {"version_id": "b", "label": "B", "impressions": 30, "submissions": 1},
                {"version_id": "c", "label": "C", "impressions": 30, "submissions": 2},
            ],
            campaign_id="campaign-1",
            default_version_id="a",
            simulations=4_000,
        )

        self.assertEqual(result["decision"], "not_enough_data")
        self.assertIsNone(result["winner_version_id"])

    def test_clear_winner_with_minimum_samples_is_recommended(self):
        result = compare_variants(
            [
                {"version_id": "a", "label": "A", "impressions": 1_000, "submissions": 20},
                {"version_id": "b", "label": "B", "impressions": 1_000, "submissions": 100},
                {"version_id": "c", "label": "C", "impressions": 1_000, "submissions": 30},
            ],
            campaign_id="campaign-2",
            default_version_id="a",
            simulations=8_000,
        )

        self.assertEqual(result["decision"], "winner")
        self.assertEqual(result["winner_version_id"], "b")
        self.assertGreaterEqual(result["winner_probability"], 0.95)
        self.assertGreater(result["expected_lift_percent"], 0)
        self.assertLess(
            result["versions"][1]["credible_interval_90"][0],
            result["versions"][1]["credible_interval_90"][1],
        )

    def test_sufficient_but_similar_samples_report_no_clear_winner(self):
        result = compare_variants(
            [
                {"version_id": "a", "label": "A", "impressions": 2_000, "submissions": 100},
                {"version_id": "b", "label": "B", "impressions": 2_000, "submissions": 102},
                {"version_id": "c", "label": "C", "impressions": 2_000, "submissions": 98},
            ],
            campaign_id="campaign-close-results",
            default_version_id="a",
            simulations=8_000,
        )
        self.assertEqual(result["decision"], "no_clear_winner")
        self.assertIsNone(result["winner_version_id"])

    def test_results_are_deterministic_for_same_campaign_data(self):
        variants = [
            {"version_id": "a", "label": "A", "impressions": 400, "submissions": 12},
            {"version_id": "b", "label": "B", "impressions": 400, "submissions": 24},
        ]
        first = compare_variants(variants, "campaign-3", "a", simulations=3_000)
        second = compare_variants(variants, "campaign-3", "a", simulations=3_000)
        self.assertEqual(first, second)

    def test_invalid_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            compare_variants(
                [{"version_id": "a", "label": "A", "impressions": 2, "submissions": 3}],
                campaign_id="campaign-4",
                default_version_id="a",
            )


if __name__ == "__main__":
    unittest.main()