import sys
from cmd import Cmd

from Moyens.Recherche import Recherche
from Moyens.RechercheImmo import RechercheImmo
from Travailleurs.Immoweb import Immoweb
from pprint import pprint


class MaConsole(Cmd):
    intro = "Bienvenue dans la recherche"

    def do_recherche_immo(self, params):
        """Entrer arguments dans l'ordre 1)Pays 2)Type (immobilier...) 3)Code postal 4)Achat/location   """
        # parametres = params.split()
        # if len(parametres) != 3:
        #     print("Il faut trois arguments")
        #     return
        code_postal, ville = params.split()
        recherche_immo = RechercheImmo(code_postal, ville)
        resultats_immoweb = Immoweb().obtiens_resultats(recherche_immo)
        # pprint(vars([r for r in resultats_immoweb]))

    def do_recherche_immo_url(self, params):
        recherche = Recherche()
        recherche.url = params
        resultats_immoweb = Immoweb().obtiens_resultats(recherche)


if __name__ == '__main__':
    ma_console = MaConsole()
    ma_console.prompt = '> '
    MaConsole().cmdloop()
