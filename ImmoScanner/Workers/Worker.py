from selenium import webdriver
import selenium.webdriver.common.by
from selenium.webdriver.firefox.options import Options
from Means.ResearchResult import ResearchResult
import logging


class Worker:

    def __init__(self):
        options = Options()
        if logging.root.level > logging.DEBUG:
            options.headless = True

        self.driver = webdriver.Firefox(options=options)
        self.driver.set_page_load_timeout(60)
        self.ResearchResult = [ResearchResult()]

    def get_results(self, research):
        self.research = research
        return [self.ResearchResult]
