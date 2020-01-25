import re

from Moyens.ResultatsRechercheImmo import ResultatsRechercheImmo
from Travailleurs.TravailleurImmo import TravailleurImmo
from Moyens.RechercheImmo import RechercheImmo
from selenium.webdriver.firefox.options import Options


class Immoweb(TravailleurImmo):

    def obtiens_resultats(self, recherche_immo: RechercheImmo):

        url = self.create_url(recherche_immo)
        print(url)

        self.driver.get(url)
        self.driver.implicitly_wait(5)

        resultats_recherche_immo = []

        resultats_page_web = self.driver.find_elements("main-content")

        try:
                resultats_recherche_immo.append(self.extraction_resultats(resultats_page_web))

        finally:
            self.driver.close()
            return resultats_recherche_immo

    def extraction_resultats(self, resultats_page_web):

        resultat_recherche_immo = ResultatsRechercheImmo()
        for result in resultats_page_web:

            resultat_recherche_immo.id = result.get_attribute('id')
            print('id: ' + resultat_recherche_immo.id)

            resultat_recherche_immo.description = result.find_element_by_tag_name('a').text
            print('texte: ' + resultat_recherche_immo.description)

            resultat_recherche_immo.url = result.find_element_by_tag_name('a').get_attribute('href')
            print('lien:' + resultat_recherche_immo.url)
            # print('prix:' + result.find_element_by_class_name('xl-price rangePrice')) il faut chercher plus loin (XPATH?) ou parser le texte descriptif

            m = re.search(r'(\d+\.\d+)', resultat_recherche_immo.description)
            if m is not None:
                resultat_recherche_immo.prix = m.group(0)
                print('prix:' + resultat_recherche_immo.prix)

            print('titre:' + result.find_element_by_tag_name('div').get_attribute('title'))

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