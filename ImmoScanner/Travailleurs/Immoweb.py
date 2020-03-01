import re

from Moyens.ResultatsRechercheImmo import ResultatsRechercheImmo
from Travailleurs.TravailleurImmo import TravailleurImmo
from Moyens.RechercheImmo import RechercheImmo
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from price_parser import Price
import logging


class Immoweb(TravailleurImmo):

    def remplir_champs_manquants(self, recherche_immo: RechercheImmo):
        if recherche_immo.louer_acheter is None:
            recherche_immo.louer_acheter = "a-vendre"

        if recherche_immo.type_bien is None:
            recherche_immo.type_bien = "maison"

        if recherche_immo.pays is None:
            recherche_immo.pays = "Belgique"

    def a_la_soupe(self, url):
        self.driver.get(url) # TODO : parfois echoue avec dns error, à gerer
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    def obtiens_resultats(self, recherche_immo: RechercheImmo):
        resultats_recherche_immo = []

        self.remplir_champs_manquants(recherche_immo)

        url = self.creation_url(recherche_immo)
        logging.info(url)
        
        try:
            soup = self.a_la_soupe(url)
            nombre_pages = self.combien_pages(soup)

            for page in range(1, nombre_pages + 1):
                url = self.creation_url(recherche_immo, page)
                soup = self.a_la_soupe(url)
                resultats_valeurs = soup.find_all("article", {"card card--result card--xl"} )

                if not resultats_valeurs:
                    resultats_valeurs = soup.find_all("article", {"card card--result card--large"} )
                       
                for resultat in resultats_valeurs:
                    resultats_recherche_immo.append(self.extraction_resultats(resultat))

        finally:
            self.driver.close()
            return resultats_recherche_immo

    def chopper_resultat_id(self, resultat):
        return resultat['id'].split('_')[1]

    def chopper_resultat_description(self, resultat):
        if hasattr(resultat.contents[0].contents[8], 'text'):
            return resultat.contents[0].contents[8].text
        else:
            return ""

    def chopper_resultat_lien(self, resultat):
        return resultat.contents[0].contents[2].contents[0]['href']

    def chopper_resultats_prix(self, resultat):
        prix = Price.fromstring(resultat.contents[0].contents[4].contents[0].contents[2].text.strip())
        return prix.amount, prix.currency
    
    def extraction_resultats(self, resultat):
        resultat_recherche_immo = ResultatsRechercheImmo()

        resultat_recherche_immo.id = self.chopper_resultat_id(resultat)
        logging.debug('id: ' + resultat_recherche_immo.id)
      
        resultat_recherche_immo.description = self.chopper_resultat_description(resultat)
        logging.debug('texte: ' + resultat_recherche_immo.description)

        resultat_recherche_immo.url = self.chopper_resultat_lien(resultat)
        logging.debug('lien: ' + resultat_recherche_immo.url)

        resultat_recherche_immo.prix, resultat_recherche_immo.monnaie = self.chopper_resultats_prix(resultat)
        logging.debug('prix: ' + str(resultat_recherche_immo.prix), 'monnaie: ' + resultat_recherche_immo.monnaie)

        return resultat_recherche_immo

    def creation_url(self, recherche_immo: RechercheImmo, page = 1):
        if page != 1:
            return f"https://www.immoweb.be/fr/recherche/{recherche_immo.type_bien}/{recherche_immo.louer_acheter}/{recherche_immo.ville}/{recherche_immo.code_postal}?countries=BE&page={page}"

        if recherche_immo.url is not "":
            return recherche_immo.url # TODO Ajouter fonction pour chopper les parametres de l'url

        return f"https://www.immoweb.be/fr/recherche/{recherche_immo.type_bien}/{recherche_immo.louer_acheter}/{recherche_immo.ville}/{recherche_immo.code_postal}?countries=BE&page={page}"

    def combien_pages(self, soup):
        pagination = soup.find_all("a", {"pagination__link button button--text"}) 
        if not len(pagination) == 0:
            premiere_moitie = self.super_mouette_mouette(pagination) # pagination presente deux fois sur la page
            return int(premiere_moitie[-1].text.split('Page', 1)[1].strip())
        else:
            return 1

    def super_mouette_mouette(self, la_liste):
        moitie = len(la_liste) // 2
        return la_liste[:moitie]
