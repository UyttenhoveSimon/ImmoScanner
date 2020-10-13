from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import selenium.webdriver.common.by
from Means.ResearchResult import ResearchResult
import logging
import os
import sys


class Worker:
    def __init__(self):
        options = Options()
        # if logging.root.level > logging.DEBUG:
        # options.headless = True

        if sys.platform.startswith("win32"):
            options.binary_location = "C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
            self.driver = webdriver.Chrome(options=options)

        elif sys.platform.startswith("linux"):
            options.binary_location = "/usr/bin/brave"
            self.driver = webdriver.Chrome(
                options=options, executable_path="/usr/local/bin/chromedriver"
            )

        self.driver.set_page_load_timeout(60)
        self.research_result = [ResearchResult()]
        self.domain_name = ""
