import logging
import os
import sys

import selenium.webdriver.common.by
from Means.ResearchResult import ResearchResult
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class Worker:
    _webdriver_url = ""
    _webdriver_session_id = ""

    def get_webdriver_url(self):
        return type(self)._webdriver_url

    def set_webdriver_url(self, val):
        type(self)._webdriver_url = val

    webdriver_url = property(get_webdriver_url, set_webdriver_url)

    def get_webdriver_session_id(self):
        return type(self)._webdriver_session_id

    def set_webdriver_session_id(self, val):
        type(self)._webdriver_session_id = val

    webdriver_session_id = property(get_webdriver_session_id, set_webdriver_session_id)

    def __init__(self):

        self.research_result = [ResearchResult()]
        self.domain_name = ""
        self.options = Options()

        if logging.root.level > logging.DEBUG:
            self.options.headless = True

    def start(self):
        if sys.platform.startswith("win32"):
            self.options.binary_location = "C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
            # Tried to have only one browser opened via class properties, not working
            # chromedriver.exe is within the path
            # if self.webdriver_session_id != "":
            #     self.driver = webdriver.Remote(
            #         command_executor=self.webdriver_url, desired_capabilities={}
            #     )
            #     self.driver.session_id = self.webdriver_session_id
            # else:
            #     self.driver = webdriver.Chrome(options=options)
            #     self.webdriver_url = self.driver.command_executor._url
            #     self.webdriver_session_id = self.driver.session_id

            self.driver = webdriver.Chrome(options=self.options)
            self.driver.set_page_load_timeout(60)

        elif sys.platform.startswith("linux"):
            self.options.binary_location = "/usr/bin/brave"

            # if self.webdriver_session_id != "":
            #     self.driver = webdriver.Remote(
            #         command_executor=self.webdriver_url, desired_capabilities={}
            #     )
            #     self.driver.session_id = self.webdriver_session_id
            # else:
            #     self.driver = webdriver.Chrome(
            #         options=options, executable_path="/usr/local/bin/chromedriver"
            #     )
            #     self.webdriver_url = self.driver.command_executor._url
            #     self.webdriver_session_id = self.driver.session_id

            self.driver = webdriver.Chrome(
                options=self.options, executable_path="/usr/local/bin/chromedriver"
            )
            self.driver.set_page_load_timeout(60)
