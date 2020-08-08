import statistics

class StatisticalInsights:

    def __init__(self, resultats_recherche):
        self.resultats_recherche = resultats_recherche
        self.prix_moyen = 0
        self.prix_mediane = 0

    def calculate_mean_price(self):
        self.prix_moyen = statistics.mean(resultat.prix for resultat in self.resultats_recherche)
        return self.prix_moyen

    def calculate_median_price(self):
        self.prix_mediane = statistics.median(resultat.prix for resultat in self.resultats_recherche)
        return self.prix_mediane            

