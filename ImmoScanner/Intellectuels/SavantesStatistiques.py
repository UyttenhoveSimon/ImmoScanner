import statistics

class SavantesStatistiques:

    def __init__(self, resultats_recherche):
        self.resultats_recherche = resultats_recherche
        self.prix_moyen = 0
        self.prix_mediane = 0

    def calculer_prix_moyen(self):
        self.prix_moyen = statistics.mean(resultat.prix for resultat in self.resultats_recherche)
        return self.prix_moyen

    def calculer_prix_median(self):
        self.prix_mediane = statistics.median(resultat.prix for resultat in self.resultats_recherche)
        return self.prix_mediane            

