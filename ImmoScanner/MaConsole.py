import sys
from cmd import Cmd

from Moyens.Recherche import Recherche
from Moyens.RechercheImmo import RechercheImmo
from Travailleurs.Immoweb import Immoweb
from pprint import pprint
import logging
from Intellectuels.SavantesStatistiques import SavantesStatistiques


class MaConsole(Cmd):
    intro = "Bienvenue dans la recherche"
    logging.basicConfig(level=logging.DEBUG)

    def do_recherche_immo(self, params):
        """Entrer arguments dans l'ordre 1)Pays 2)Type (immobilier...) 3)Code postal 4)Achat/location   """
        # parametres = params.split()
        # if len(parametres) != 3:
        #     print("Il faut trois arguments")
        #     return
        code_postal, ville = params.split()
        recherche_immo_vente = RechercheImmo(code_postal, ville) # valider les entrees + faire recherche code postal ou nom ville
        resultats_immoweb_vente = Immoweb().obtiens_resultats(recherche_immo_vente)

        les_bonnes_stats_vente = SavantesStatistiques(resultats_immoweb_vente)
        prix_moyen_vente = les_bonnes_stats_vente.calculer_prix_moyen()
        prix_median_vente = les_bonnes_stats_vente.calculer_prix_median()

        recherche_immo_location = RechercheImmo(code_postal, ville) # valider les entrees + faire recherche code postal ou nom ville
        recherche_immo_location.louer_acheter = "a-louer" # TODO : penser comment orchestrer avec un autre site web qui recherche avec louer dans url 
        resultats_immoweb_location = Immoweb().obtiens_resultats(recherche_immo_location)

        les_bonnes_stats_location = SavantesStatistiques(resultats_immoweb_location)
        prix_moyen_location = les_bonnes_stats_location.calculer_prix_moyen()
        prix_median_location = les_bonnes_stats_location.calculer_prix_median()

        rendement_locatif_brut_median = ((prix_median_location * 12) / prix_median_vente) * 100
        logging.info(f'Rendement locatif brut median {rendement_locatif_brut_median}')
                     
    def do_recherche_immo_url(self, params):
        recherche = Recherche()
        recherche.url = params
        resultats_immoweb = Immoweb().obtiens_resultats(recherche)


if __name__ == '__main__':
    ma_console = MaConsole()
    ma_console.prompt = '> '
    MaConsole().cmdloop()
