import re

from Moyens.ResultatsRechercheImmo import ResultatsRechercheImmo
from Travailleurs.TravailleurImmo import TravailleurImmo
from Moyens.RechercheImmo import RechercheImmo
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from price_parser import Price


class Immoweb(TravailleurImmo):

    def obtiens_resultats(self, recherche_immo: RechercheImmo):
        resultats_recherche_immo = []

        url = self.create_url(recherche_immo)
        print(url)

        self.driver.get(url)
        html = self.driver.page_source

        try:

            soup = BeautifulSoup(html, 'html.parser')
            resultats_valeurs = soup.find_all("article", {"card card--result card--xl"} ) #results_core = soup.find_all("li", {"search-results__item"})
            # results_media = soup.find_all("li", {"card--result__body"}) # soup.find_all("div", {"card--result__media"})

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


    def create_url(self, recherche_immo: RechercheImmo):

        if recherche_immo.url is not "":
            return recherche_immo.url
        # https://www.immoweb.be/fr/recherche/maison/a-vendre/waterloo/1410
        return f"https://www.immoweb.be/fr/recherche/{r_immo.type_bien}/{r_immo.louer_acheter}/{r_immo.ville}/{r_immo.code_postal}?countries=BE&page="

    def page_suivante(self, driver, url, nbre_pages):

        page_suivante = False
        url_test = url
        url_test[:-1]
        url_test += nbre_pages
        try:
            self.driver.get(url_test)
            driver.find_element_by_class_name('navig-arrow-right')
            page_suivante = True

        except:
            page_suivante = False

        return page_suivante

    def combien_pages(self, driver, url):

        nbre_pages = 1
        while self.page_suivante(driver, url, nbre_pages):
            nbre_pages += 1

        return nbre_pages