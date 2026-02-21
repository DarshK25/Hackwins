"""
Benchmark Intelligence Service
Provides industry-specific benchmarks for strategic comparisons
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    metric: str
    your_value: float
    industry_average: float
    variance_percent: float
    status: str  # "above", "below", "on_par"
    insight: str


class BenchmarkService:
    """
    Provides industry-specific benchmarks for MoneyOps strategic intelligence.
    Rule-based comparisons (no external API required).
    """

    BENCHMARKS: Dict[str, Dict[str, Any]] = {
        "IT & Software": {
            "cac": 1200,
            "ltv": 5000,
            "ltv_cac_ratio": 4.2,
            "gross_margin": 0.75,
            "churn_rate": 0.05,
            "revenue_growth_rate": 0.25,
            "operating_margin": 0.20,
            "days_sales_outstanding": 35,
            "collection_efficiency": 0.92,
        },
        "SaaS": {
            "cac": 1500,
            "ltv": 8000,
            "ltv_cac_ratio": 5.3,
            "gross_margin": 0.78,
            "churn_rate": 0.03,
            "revenue_growth_rate": 0.40,
            "operating_margin": 0.15,
            "days_sales_outstanding": 30,
            "collection_efficiency": 0.95,
        },
        "Retail": {
            "cac": 800,
            "ltv": 3000,
            "ltv_cac_ratio": 3.75,
            "gross_margin": 0.35,
            "churn_rate": 0.15,
            "revenue_growth_rate": 0.10,
            "operating_margin": 0.08,
            "days_sales_outstanding": 15,
            "collection_efficiency": 0.88,
        },
        "E-commerce": {
            "cac": 600,
            "ltv": 2500,
            "ltv_cac_ratio": 4.2,
            "gross_margin": 0.40,
            "churn_rate": 0.20,
            "revenue_growth_rate": 0.30,
            "operating_margin": 0.10,
            "days_sales_outstanding": 7,
            "collection_efficiency": 0.98,
        },
        "Manufacturing": {
            "cac": 3000,
            "ltv": 15000,
            "ltv_cac_ratio": 5.0,
            "gross_margin": 0.30,
            "churn_rate": 0.08,
            "revenue_growth_rate": 0.08,
            "operating_margin": 0.12,
            "days_sales_outstanding": 45,
            "collection_efficiency": 0.85,
        },
        "Consulting": {
            "cac": 2000,
            "ltv": 20000,
            "ltv_cac_ratio": 10.0,
            "gross_margin": 0.60,
            "churn_rate": 0.10,
            "revenue_growth_rate": 0.15,
            "operating_margin": 0.18,
            "days_sales_outstanding": 40,
            "collection_efficiency": 0.90,
        },
        "default": {
            "cac": 1500,
            "ltv": 6000,
            "ltv_cac_ratio": 4.0,
            "gross_margin": 0.50,
            "churn_rate": 0.10,
            "revenue_growth_rate": 0.15,
            "operating_margin": 0.12,
            "days_sales_outstanding": 35,
            "collection_efficiency": 0.90,
        },
    }

    METRIC_LABELS: Dict[str, str] = {
        "cac": "Customer Acquisition Cost (₹)",
        "ltv": "Lifetime Value (₹)",
        "ltv_cac_ratio": "LTV:CAC Ratio",
        "gross_margin": "Gross Margin (%)",
        "churn_rate": "Monthly Churn Rate (%)",
        "revenue_growth_rate": "Revenue Growth Rate (%)",
        "operating_margin": "Operating Margin (%)",
        "days_sales_outstanding": "Days Sales Outstanding",
        "collection_efficiency": "Collection Efficiency (%)",
    }

    def get_industry_benchmarks(self, industry: str) -> Dict[str, Any]:
        """Get all benchmarks for an industry"""
        return self.BENCHMARKS.get(industry, self.BENCHMARKS["default"])

    def compare_to_benchmark(
        self,
        metric: str,
        value: float,
        industry: str
    ) -> BenchmarkResult:
        """Compare a single metric to industry benchmark"""
        benchmarks = self.BENCHMARKS.get(industry, self.BENCHMARKS["default"])
        benchmark = benchmarks.get(metric, 0)

        if benchmark == 0:
            return BenchmarkResult(
                metric=metric,
                your_value=value,
                industry_average=0,
                variance_percent=0,
                status="unknown",
                insight="No benchmark data available for this metric"
            )

        variance = ((value - benchmark) / benchmark) * 100

        # For some metrics, lower is better (CAC, churn, DSO)
        lower_is_better = metric in ["cac", "churn_rate", "days_sales_outstanding"]

        if lower_is_better:
            status = "above" if variance < 0 else "below"  # below average CAC = good
        else:
            status = "above" if variance > 0 else "below"

        insight = self._generate_insight(metric, value, benchmark, variance, status)

        return BenchmarkResult(
            metric=self.METRIC_LABELS.get(metric, metric),
            your_value=value,
            industry_average=benchmark,
            variance_percent=round(float(variance), 1),  # type: ignore[call-overload]
            status=status,
            insight=insight
        )

    def compare_all_metrics(
        self,
        metrics: Dict[str, float],
        industry: str
    ) -> List[BenchmarkResult]:
        """Compare multiple metrics to benchmarks"""
        results = []
        for metric, value in metrics.items():
            if metric in self.BENCHMARKS.get(industry, self.BENCHMARKS["default"]):
                results.append(self.compare_to_benchmark(metric, value, industry))
        return results

    def _generate_insight(
        self,
        metric: str,
        value: float,
        benchmark: float,
        variance: float,
        status: str
    ) -> str:
        """Generate human-readable insight for benchmark comparison"""
        abs_variance = abs(variance)

        insights = {
            "cac": {
                "above": f"Your CAC is {abs_variance:.0f}% higher than industry. Consider optimizing marketing channels.",
                "below": f"Excellent! Your CAC is {abs_variance:.0f}% lower than industry average — cost-efficient acquisition."
            },
            "ltv": {
                "above": f"Strong LTV, {abs_variance:.0f}% above industry. Focus on retention to protect this.",
                "below": f"LTV is {abs_variance:.0f}% below industry. Look at upsell/cross-sell opportunities."
            },
            "gross_margin": {
                "above": f"Healthy gross margin, {abs_variance:.0f}% above industry peers.",
                "below": f"Gross margin {abs_variance:.0f}% below peers. Review pricing and COGS efficiency."
            },
            "churn_rate": {
                "above": f"Churn rate {abs_variance:.0f}% better than industry — strong retention.",
                "below": f"Churn is {abs_variance:.0f}% worse than peers. Prioritize customer success initiatives."
            },
            "revenue_growth_rate": {
                "above": f"Growing {abs_variance:.0f}% faster than industry peers.",
                "below": f"Growth {abs_variance:.0f}% slower than industry. Review go-to-market strategy."
            },
        }

        metric_insights = insights.get(metric, {})
        return metric_insights.get(status, f"Variance of {variance:.1f}% vs industry average")

    def generate_competitive_position(
        self,
        metrics: Dict[str, float],
        industry: str
    ) -> Dict[str, Any]:
        """Generate overall competitive position summary"""
        results = self.compare_all_metrics(metrics, industry)

        above_count = sum(1 for r in results if r.status == "above")
        below_count = sum(1 for r in results if r.status == "below")
        total = len(results)

        if total == 0:
            return {"position": "unknown", "score": 50, "summary": "Insufficient data"}

        position_score = (above_count / total) * 100

        if position_score >= 70:
            position = "market_leader"
            summary = "Your business outperforms most industry peers across key metrics."
        elif position_score >= 50:
            position = "competitive"
            summary = "Your business is competitive, with targeted improvements possible."
        elif position_score >= 30:
            position = "developing"
            summary = "Several metrics below industry average — strategic intervention needed."
        else:
            position = "lagging"
            summary = "Multiple metrics significantly below industry — urgent action required."

        return {
            "position": position,
            "score": round(position_score),
            "above_benchmark": above_count,
            "below_benchmark": below_count,
            "total_metrics": total,
            "summary": summary,
            "results": [
                {
                    "metric": r.metric,
                    "your_value": r.your_value,
                    "industry_average": r.industry_average,
                    "variance_percent": r.variance_percent,
                    "status": r.status,
                    "insight": r.insight
                }
                for r in results
            ]
        }


# Singleton
benchmark_service = BenchmarkService()
