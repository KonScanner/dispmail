from xml.dom import ValidationErr
from selenium import webdriver
from time import sleep
import logging


class SleepConfig:
    sleep_amount = 0.1


class FindTypes:
    XPATH = "xpath"
    CSS = "css"
    CLASS_NAME = "class_name"


class Config:
    """
    The config class is used to set the browser options.

    :param headless: Creates a headless session if True. Default is True.
    """

    def __init__(self, headless: bool = True) -> None:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4183.83 Safari/537.36"
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.headless = True
        self.options.add_argument(f"user-agent={user_agent}")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--ignore-certificate-errors")
        self.options.add_argument("--allow-running-insecure-content")
        self.options.add_argument("--disable-extensions")
        self.options.add_argument("--proxy-server='direct://'")
        self.options.add_argument("--proxy-bypass-list=*")
        self.options.add_argument("--start-maximized")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--no-sandbox")
        self.sleep_amount = 0.1

    @staticmethod
    def sleeper(func):
        def inner(*args, **kwargs):
            result = func(*args, **kwargs)
            sleep(SleepConfig.sleep_amount)
            return result

        return inner

    @staticmethod
    def force_find(
        driver, element_str: str, search_type: str, sleep_amount=None, max_attempts: int = 10
    ):
        attempts = 0
        while attempts < max_attempts:
            try:
                return find_type(driver=driver, element_str=element_str, search_type=search_type)
            except Exception as e:
                logging.debug(f"Forcing to find failed with exception {e}")
                sleep_amount = sleep_amount if sleep_amount else SleepConfig.sleep_amount
                sleep(sleep_amount)

    @staticmethod
    def force_click(element, sleep_amount=None):
        """
        Clicks something until it works

        :param element: The element to click on
        :param sleep_time: How many time to wait between clicks
        """
        while True:
            try:
                element.click()
                return
            except Exception as e:
                logging.debug(f"Forcing to click failed with exception {e}")
                sleep_amount = sleep_amount if sleep_amount else SleepConfig.sleep_amount
                sleep(sleep_amount)

    @staticmethod
    def debug_html(element):
        """
        Provides full outterHTML of element, for debugging

        :param element: The element to extract the outterHTML from
        """
        if element:
            logging.info(element.get_attribute("outerHTML"))


def find_type(driver, element_str: str, search_type: str):
    if search_type.lower() == FindTypes.XPATH:
        return driver.find_element_by_xpath(element_str)
    elif search_type.lower() == FindTypes.CSS:
        return driver.find_element_by_css_selector(element_str)
    elif search_type.lower() == FindTypes.CLASS_NAME:
        return driver.find_element_by_class_name(element_str)
    else:
        raise ValueError(f"Search type is not supported {search_type=}")
