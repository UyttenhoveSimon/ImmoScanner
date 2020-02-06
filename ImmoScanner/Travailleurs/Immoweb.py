import re

from Moyens.ResultatsRechercheImmo import ResultatsRechercheImmo
from Travailleurs.TravailleurImmo import TravailleurImmo
from Moyens.RechercheImmo import RechercheImmo
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


class Immoweb(TravailleurImmo):

    def obtiens_resultats(self, recherche_immo: RechercheImmo):
        resultats_recherche_immo = []

        url = self.create_url(recherche_immo)
        print(url)

        self.driver.get(url)
        html = self.driver.page_source

        try:
            resultats_recherche_immo.append(self.extraction_resultats(html))

        finally:
            self.driver.close()
            return resultats_recherche_immo

    def extraction_resultats(self, html):

        resultat_recherche_immo = ResultatsRechercheImmo()

        soup = BeautifulSoup(html, 'html.parser')
        results_core = soup.find_all("div", {"card--result__body"})
        results_media = soup.find_all("div", {"card--result__media"})

        for result in results_core:

            resultat_recherche_immo.id = soup.find("span", re.compile("card__information card--result__information card__information--property").text)
            print('id: ' + resultat_recherche_immo.id)

            resultat_recherche_immo.description = result.get_attribute('card__description card--result__description')
            print('texte: ' + resultat_recherche_immo.description)

            resultat_recherche_immo.url = result.find_element_by_tag_name('a').get_attribute('href')
            print('lien:' + resultat_recherche_immo.url)

            # spans = result.
            # print('prix:' + result.find_element_by_class_name('xl-price rangePrice')) il faut chercher plus loin (XPATH?) ou parser le texte descriptif

            #m = re.search(r'(\d+\.\d+)', resultat_recherche_immo.description)
            #if m is not None:
            #    resultat_recherche_immo.prix = m.group(0)
            #    print('prix:' + resultat_recherche_immo.prix)

           
        return resultat_recherche_immo


    def create_url(self, recherche_immo: RechercheImmo):

        if recherche_immo.url is not "":
            return recherche_immo.url
        # https://www.immoweb.be/fr/recherche/maison/a-vendre/waterloo/1410
        return f"https://www.immoweb.be/fr/recherche/{r_immo.type_bien}/{r_immo.louer_acheter}/{r_immo.ville}/{r_immo.code_postal}?page="

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