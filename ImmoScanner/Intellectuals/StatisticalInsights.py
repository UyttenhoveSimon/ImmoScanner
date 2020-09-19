import statistics


class StatisticalInsights:
    def __init__(self, research_results=""):
        self.research_results = research_results
        self.price_average = 0
        self.price_median = 0

    def calculate_mean_price(self):
        self.price_average = statistics.mean(
            resultat.price for resultat in self.research_results
        )
        return self.price_average

    def calculate_median_price(self):
        self.price_median = statistics.median(
            resultat.price for resultat in self.research_results
        )
        return self.price_median

    def calculate_gross_yield_median(self, price_median_to_rent, price_median_to_sell):
        return ((price_median_to_rent * 12) / price_median_to_sell) * 100
