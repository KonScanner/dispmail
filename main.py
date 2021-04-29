from selenium import webdriver
import sys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import random
import time as t
from helper_functions import *


class Config:
    def __init__(self, headless: bool = True) -> None:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4183.83 Safari/537.36"
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.headless = True
        self.options.add_argument(f'user-agent={user_agent}')
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument('--ignore-certificate-errors')
        self.options.add_argument('--allow-running-insecure-content')
        self.options.add_argument("--disable-extensions")
        self.options.add_argument("--proxy-server='direct://'")
        self.options.add_argument("--proxy-bypass-list=*")
        self.options.add_argument("--start-maximized")
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--no-sandbox')


class TutaAccounts:
    def __init__(self):
        self.driver = webdriver.Chrome(options=Config(headless=False).options)
        self.driver.maximize_window()
        self.e = None
        (_, email, pwd) = credential_creator(fullname=False)
        self.username = email
        self.password = pwd

    def _try_click(self, x_path, css=False):
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

    def _create(self):
        self.driver.get("https://mail.tutanota.com/login")
        self._try_click('/html/body/div/div[3]/div[2]/div/div[3]/div/button')
        self._try_click(
            '/html/body/div/div[3]/div[2]/div/div[4]/div/div/div/button[1]')
        self._try_click(
            '/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div[2]/div[1]/div[1]/div[4]/button')
        self._try_click(
            '#modal > div:nth-child(2) > div > div > div > div:nth-child(2) > div:nth-child(1) > div > input[type=checkbox]', css=True)
        self._try_click(
            '#modal > div:nth-child(2) > div > div > div > div:nth-child(2) > div:nth-child(2) > div > input[type=checkbox]', css=True)
        t.sleep(0.15)
        self._try_click(
            '#modal > div:nth-child(2) > div > div > div > div.flex-center.dialog-buttons > button:nth-child(2)', css=True)
        t.sleep(0.55)
        # Pass in input
        self.driver.find_element_by_xpath(
            '/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[1]/div/div/div/div[1]/input').send_keys(self.username)
        t.sleep(0.05)
        self.driver.find_element_by_xpath(
            '/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[2]/div[1]/div[1]/div/div/div[1]/input[4]').send_keys(self.password)
        t.sleep(0.05)
        self.driver.find_element_by_xpath(
            '/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[2]/div[3]/div[1]/div/div/div/input').send_keys(self.password)
        t.sleep(0.15)
        self._try_click(
            '/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[3]/div/input')
        self._try_click(
            '/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[4]/div/input')
        t.sleep(4)
        self._try_click(
            '/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[5]/button')
        response = input("Was the account successfully created?")
        if response == "y":
            write_if_complete(email=self.username,
                              password=self.password, domain="tutanota")
            self.driver.quit()
        else:
            self.driver.quit()


class Interia:
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
        keytaps = "".join(
            [".key_down(Keys.DOWN)" for i in range(0, self.month)])
        eval(f"self.actions{keytaps}.send_keys(Keys.ENTER).perform()")

    def _select_clear(self):
        keytaps = "".join(
            [".key_down(Keys.BACKSPACE)" for i in range(0, 100)])  # Arbitrary length
        eval(f"self.actions{keytaps}.perform()")

    def _select_gender(self):
        keytaps = "".join(
            [".key_down(Keys.DOWN)" for i in range(0, random.randint(1, 2))])
        eval(f"self.actions{keytaps}.send_keys(Keys.ENTER).perform()")

    def _create(self):
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


if __name__ == "__main__":
    if sys.argv[1] == "tuta":
        init = TutaAccounts()
        init._create()
        print(
            f"Tutanota Account {init.username}@tutanota.com created!\nWith password: {init.password}")

    elif sys.argv[1] == "interia":
        init = Interia()
        init._create()
        print(
            f"Tutanota Account {init.username}@interia.pl created!\nWith password: {init.password}")

    else:
        raise ValueError(
            "sys.argv[1] can only be one of [\"tuta\",\"interia\"]")
