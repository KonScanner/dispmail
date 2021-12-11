from utils.Config import Config
from selenium import webdriver
import time as t
import random
from utils.helper_functions import *
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class Interia:

    """
    This function is used to register a new email on the Interia website.
    """

    def __init__(self):
        self.driver = webdriver.Chrome(options=Config(headless=False).options)
        self.driver.maximize_window()
        self.e = None
        (fullname, email, pwd) = credential_creator(fullname=False)
        self.first, self.last = fullname.split(" ")
        self.day, self.month, self.year = birthday_creator()
        self.username = email
        self.password = pwd
        self.actions = ActionChains(self.driver)

    def _try_click(self, x_path, css=False):
        """
        Tries to click on the element with a timer (dirty solution).

        :param x_path: x_path of element
        :param css: True if css element path, False if x_path. Default: False
        """
        state = True
        for i in range(0, 6):
            if state:
                try:
                    if not css:
                        self.driver.find_element_by_xpath(x_path).click()
                    else:
                        self.driver.find_element_by_css_selector(
                            x_path).click()
                        t.sleep(1)
                    state = False
                    print(state)
                except Exception as e:
                    self.e = e
                    t.sleep(1.5)
            else:
                continue
        print(self.e)

    def _select_month(self):
        """
        Selects the month element and populates it.
        """
        keytaps = "".join(
            [".key_down(Keys.DOWN)" for i in range(0, self.month)])
        eval(f"self.actions{keytaps}.send_keys(Keys.ENTER).perform()")

    def _select_clear(self):
        """
        Selects the clear element.
        """
        keytaps = "".join(
            [".key_down(Keys.BACKSPACE)" for i in range(0, 100)])  # Arbitrary length
        eval(f"self.actions{keytaps}.perform()")

    def _select_gender(self):
        """
        Selects the gender of the email.
        """
        keytaps = "".join(
            [".key_down(Keys.DOWN)" for i in range(0, random.randint(1, 2))])
        eval(f"self.actions{keytaps}.send_keys(Keys.ENTER).perform()")

    def _create(self):
        """
        Creates the email.
        """
        self.driver.get(
            "https://konto-pocztowe.interia.pl/#/nowe-konto/darmowe")
        t.sleep(0.55)
        self._try_click("/html/body/div[3]/div[2]/button[3]")
        # Pass in input

        self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[1]/input").send_keys(self.first)
        t.sleep(0.3)
        self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[2]/input").send_keys(self.last)
        t.sleep(0.3)
        # Day of birth
        self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[3]/div[1]/input").send_keys(self.day)
        t.sleep(0.3)
        # Day of month
        self._try_click(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[3]/div[2]/div[2]")
        self._select_month()
        t.sleep(0.3)
        # Day of Year
        self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[3]/div[3]/input").send_keys(self.year)
        t.sleep(0.3)
        self._try_click(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[4]/div[2]")
        self._select_gender()
        username_tag = "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[5]/div[1]/input"
        self.driver.find_element_by_xpath(
            username_tag).click()
        self._select_clear()
        t.sleep(0.3)
        self.driver.find_element_by_xpath(
            username_tag).send_keys(self.username)
        t.sleep(0.3)

        self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[6]/div/input").send_keys(self.password)
        t.sleep(0.3)

        self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[7]/div/input").send_keys(self.password)
        t.sleep(0.3)
        self._try_click(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[2]/div[1]/div[1]/label")
        t.sleep(0.3)
        t.sleep(5)
        self.driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

        # Create account btn
        self._try_click(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[2]/button")
        t.sleep(0.55)
        self._try_click(
            "/html/body/div[2]/div[3]/div/div[2]/div[1]")
        self._try_click(
            "/html/body/div[2]/section[3]/div[1]/div[1]/section/ul/li/div[2]/div[1]/div[1]/span")
        self._try_click(
            "/html/body/div[2]/section[4]/div/div/div[1]/div/div/span/div")
        self._try_click("/html/body/div[2]/section[4]/div/div/div[2]/div/a[2]")
        print("Was the account successfully created?")
        response = input()
        if response == "y":
            write_if_complete(email=self.username,
                              password=self.password, domain="interia", country="pl")
            self.driver.quit()
        else:
            self.driver.quit()
