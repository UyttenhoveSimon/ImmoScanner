from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import selenium.webdriver.common.by
from Means.ResearchResult import ResearchResult
import logging


class Worker:
    def __init__(self):
        # options = Options()
        # if logging.root.level > logging.DEBUG:
            # options.headless = True
        options = Options()
        options.binary_location = "/usr/bin/brave"
        self.driver = webdriver.Chrome(options= options,executable_path='/usr/local/bin/chromedriver') #options=options
        self.driver.set_page_load_timeout(60)
        self.research_result = [ResearchResult()]
        self.domain_name = ""
