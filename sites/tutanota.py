from utils.Config import Config
from selenium import webdriver
import time as t
from utils.helper_functions import credential_creator, write_if_complete
from webdriver_manager.chrome import ChromeDriverManager
import logging

logging.basicConfig(level=logging.INFO)


class TutaAccounts:

    """
    This function is used to register a new email on the TutaNota website.
    """

    def __init__(self):
        self.driver = webdriver.Chrome(
            ChromeDriverManager().install(), options=Config(headless=False).options
        )
        self.driver.maximize_window()
        self.e = None
        (_, email, pwd) = credential_creator(fullname=False)
        self.username = email
        self.password = pwd

    def _try_click(self, x_path, css=False, prompt=""):
        """
        Tries to click on the element with a timer (dirty solution).

        :param x_path: x_path of element
        :param css: True if css element path, False if x_path. Default: False
        """
        if prompt != "":
            logging.info(f"[ACTION]: {prompt}")
        state = True
        for _ in range(6):
            if state:
                try:
                    if not css:
                        self.driver.find_element_by_xpath(x_path).click()
                    else:
                        self.driver.find_element_by_css_selector(x_path).click()
                        t.sleep(1)
                    state = False
                    print(state)
                except Exception as e:
                    self.e = e
                    t.sleep(1.5)
        logging.error(f"Failed to click with exception {self.e}")

    def _create(self):
        """
        Creates the email.
        """
        # Load site
        self.driver.get("https://mail.tutanota.com/login")

        # Click Sign-up
        self._try_click(
            "/html/body/div/div[3]/div[2]/div/div[1]/div[2]/button[1]/div/div",
            prompt="Click Sign-up",
        )

        # Free version
        self._try_click(
            "/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[3]/div[1]/div/div[1]/div[5]/button/div"
        )

        # Checkboxes
        self._try_click(
            "#modal > div:nth-child(2) > div > div > div > div:nth-child(2) > div:nth-child(1) >"
            " div > input[type=checkbox]",
            css=True,
        )
        self._try_click(
            "#modal > div:nth-child(2) > div > div > div > div:nth-child(2) > div:nth-child(2) >"
            " div > input[type=checkbox]",
            css=True,
        )
        t.sleep(0.15)
        self._try_click(
            "#modal > div:nth-child(2) > div > div > div > div.flex-center.dialog-buttons >"
            " button:nth-child(2)",
            css=True,
        )
        t.sleep(0.55)
        # Pass in input

        # Pass in username
        self.driver.find_element_by_css_selector(
            "#signup-account-dialog > div > div.text-field.rel.overflow-hidden.text.pt > div > div"
            " > div > div.flex-grow.rel > input"
        ).send_keys(self.username)
        t.sleep(0.15)

        # Pass in password
        self.driver.find_element_by_css_selector(
            "#signup-account-dialog > div > div:nth-child(2) > div:nth-child(1) > div > div > div >"
            " div.flex-grow.rel > input.input"
        ).send_keys(self.password)
        t.sleep(0.15)

        # Pass in repeat password
        self.driver.find_element_by_css_selector(
            "#signup-account-dialog > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div.flex-grow.rel > input"
        ).send_keys(self.password)
        t.sleep(0.15)
        self._try_click(
            "/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[3]/div/input"
        )
        self._try_click(
            "/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[4]/div/input"
        )
        t.sleep(4)
        self._try_click(
            "/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[5]/button"
        )
        response = input("Was the account successfully created? [y/n] ")

        if response.lower() == "y":
            write_if_complete(email=self.username, password=self.password, domain="tutanota")
        self.driver.quit()
