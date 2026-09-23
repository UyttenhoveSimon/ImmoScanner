import statistics


class StatisticalInsights:
    def __init__(self, research_results=()):
        self.research_results = list(research_results)
        self.price_average = 0
        self.price_median = 0

    def prices(self):
        return [float(result.price) for result in self.research_results if result.price]

    def calculate_mean_price(self):
        prices = self.prices()
        self.price_average = statistics.mean(prices) if prices else 0
        return self.price_average

    def calculate_median_price(self):
        prices = self.prices()
        self.price_median = statistics.median(prices) if prices else 0
        return self.price_median

    def price_per_square_meter_median(self):
        ratios = [
            result.price_per_square_meter
            for result in self.research_results
            if result.price_per_square_meter
        ]
        return statistics.median(ratios) if ratios else 0

    @staticmethod
    def gross_yield(monthly_rent, selling_price):
        """Gross rental yield, in percent, from a monthly rent and a sale price."""
        if not selling_price:
            return 0
        return ((monthly_rent * 12) / selling_price) * 100
