import logging
import sys

from Means.ResearchResult import ResearchResult
from playwright.sync_api import sync_playwright


class Worker:
    def __init__(self):
        self.research_result = [ResearchResult()]
        self.domain_name = ""
        self.browser = None
        self.context = None
        self.page = None

    def start(self):
        with sync_playwright() as p:
            browser_type = p.chromium
            if sys.platform.startswith("win32"):
                executable_path = "C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
                self.browser = browser_type.launch(
                    executable_path=executable_path,
                    headless=logging.root.level > logging.DEBUG,
                )
            else:
                self.browser = browser_type.launch(
                    headless=logging.root.level > logging.DEBUG
                )

            self.context = self.browser.new_context()
            self.page = self.context.new_page()

    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()

    def navigate(self, url):
        self.page.goto(url)

    def find_element(self, selector):
        return self.page.query_selector(selector)

    def find_elements(self, selector):
        return self.page.query_selector_all(selector)

    def get_text(self, selector):
        element = self.find_element(selector)
        return element.inner_text() if element else None

    def click(self, selector):
        self.page.click(selector)

    def fill(self, selector, value):
        self.page.fill(selector, value)
