import re

from Moyens.ResultatsRechercheImmo import ResultatsRechercheImmo
from Travailleurs.TravailleurImmo import TravailleurImmo
from Moyens.RechercheImmo import RechercheImmo
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from price_parser import Price


class Immoweb(TravailleurImmo):

    def a_la_soupe(self, url):
        self.driver.get(url)
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    def obtiens_resultats(self, recherche_immo: RechercheImmo):
        resultats_recherche_immo = []

        url = self.creation_url(recherche_immo)
        print(url)
        
        try:
            soup = self.a_la_soupe(url)
            nombre_pages = self.combien_pages(soup)

            for page in nombre_pages:
                url = self.creation_url(recherche_immo, page)
                soup = self.a_la_soupe(url)
                resultats_valeurs = soup.find_all("article", {"card card--result card--xl"} )
                       
                for resultat in resultats_valeurs:
                    resultats_recherche_immo.append(self.extraction_resultats(resultat))

        finally:
            self.driver.close()
            return resultats_recherche_immo

    def chopper_resultat_id(self, resultat):
        return resultat['id'].split('_')[1]

    def chopper_resultat_description(self, resultat):
        return resultat.contents[0].contents[8].text

    def chopper_resultat_lien(self, resultat):
        return resultat.contents[0].contents[2].contents[0]['href']

    def chopper_resultats_prix(self, resultat):
        prix = Price.fromstring(resultat.contents[0].contents[4].contents[0].contents[2].text.strip())
        return prix.amount, prix.currency
    
    def extraction_resultats(self, resultat):
        resultat_recherche_immo = ResultatsRechercheImmo()

        resultat_recherche_immo.id = self.chopper_resultat_id(resultat)
        print('id: ' + resultat_recherche_immo.id)
      
        resultat_recherche_immo.description = self.chopper_resultat_description(resultat)
        print('texte: ' + resultat_recherche_immo.description)

        resultat_recherche_immo.url = self.chopper_resultat_lien(resultat)
        print('lien: ' + resultat_recherche_immo.url)

        resultat_recherche_immo.prix, resultat_recherche_immo.monnaie = self.chopper_resultats_prix(resultat)
        print('prix: ' + str(resultat_recherche_immo.prix), 'monnaie: ' + resultat_recherche_immo.monnaie)

        return resultat_recherche_immo

    def creation_url(self, recherche_immo: RechercheImmo, page = 1):
        if recherche_immo.url is not "":
            return recherche_immo.url # TODO gestion url et multipages
        return f"https://www.immoweb.be/fr/recherche/{recherche_immo.type_bien}/{recherche_immo.louer_acheter}/{recherche_immo.ville}/{recherche_immo.code_postal}?countries=BE&page={page}"

    def combien_pages(self, soup):
        pagination = soup.find_all("a", {"pagination__link button button--text"}) 
        if pagination.count != 0:
            premiere_moitie = self.super_mouette_mouette(pagination)
            return int(premiere_moitie[-1].text.split('Page', 1)[1].strip())
        else:
            return 1

    def super_mouette_mouette(self, la_liste):
        moitie = len(la_liste) // 2
        return la_liste[:moitie]
