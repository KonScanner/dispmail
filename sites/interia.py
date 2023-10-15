from utils.Config import Config, SleepConfig
from selenium import webdriver
import time as t
from utils.helper_functions import (
    credential_creator,
    birthday_creator,
    write_if_complete,
    safe_split,
)
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import logging

logging.basicConfig(level=logging.INFO)


class Interia(Config):

    """
    This function is used to register a new email on the Interia website.
    """

    def __init__(self):
        Config.__init__(self)
        SleepConfig.sleep_amount = 0.15
        self.driver = webdriver.Chrome(
            ChromeDriverManager().install(), options=Config(headless=False).options
        )
        self.failed_inputs = 0
        self.driver.maximize_window()
        self.e = None
        (fullname, email, pwd) = credential_creator(fullname=False)
        self.first, self.last = safe_split(fullname)
        self.day, self.month, self.year = birthday_creator()
        self.username = email
        self.password = pwd
        self.actions = ActionChains(self.driver)

    @staticmethod
    def sleeper(func):
        def inner(*args, **kwargs):
            result = func(*args, **kwargs)
            t.sleep(SleepConfig.sleep_amount)
            return result

        return inner

    @sleeper
    def __deal_with_cookies(self):
        cookies = self.driver.find_element_by_xpath("/html/body/div[3]/div[2]/button[3]")
        self.force_click(cookies)

    @sleeper
    def __deal_with_name(self):
        name = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[1]/input"
        )
        name.send_keys(self.first)

    @sleeper
    def __deal_with_surname(self):
        surname = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[2]/input"
        )
        surname.send_keys(self.last)

    @sleeper
    def __deal_with_username(self):
        username = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[5]/div[1]/input"
        )
        username.send_keys(self.username)

    @sleeper
    def __deal_with_day(self):
        day = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[3]/div[1]/input"
        )
        day.send_keys(self.day)

    @sleeper
    def __deal_with_month(self):
        dropdown = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[3]/div[2]"
        )
        self.force_click(dropdown)
        options = self.driver.find_element_by_class_name("account-select__options")
        first_item = options.find_element_by_class_name("account-select__options__item")
        self.force_click(first_item)

    @sleeper
    def __deal_with_year(self):
        year = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[3]/div[3]/input"
        )
        year.send_keys(self.year)

    @sleeper
    def __deal_with_pass1(self):
        pass_1 = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[6]/div/input"
        )
        pass_1.send_keys(self.password)

    @sleeper
    def __deal_with_pass2(self):
        pass_2 = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[7]/div/input"
        )
        pass_2.send_keys(self.password)

    def __deal_with_passwords(self):
        self.__deal_with_pass1()
        self.__deal_with_pass2()

    @sleeper
    def __deal_with_gender(self):
        dropdown = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[1]/div[4]/div[1]"
        )
        self.force_click(dropdown)
        options = self.driver.find_element_by_class_name("account-select__options")
        first_item = options.find_element_by_class_name("account-select__options__item")
        self.force_click(first_item)

    @sleeper
    def __remove_gambling_ads(self):
        gambling_ads = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[2]/div[1]/div[2]/div[4]/label"
        )
        self.force_click(gambling_ads)

    @sleeper
    def __accept_bad_conditions(self):
        conditions = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[2]/div[1]/div[1]/label/div/div"
        )
        self.force_click(conditions)
        self.__remove_gambling_ads()

    @sleeper
    def __finalize_account_creation(self):
        create_account = self.driver.find_element_by_xpath(
            "/html/body/div[1]/div/div/div/div/div[2]/div/form/div[2]/button"
        )
        self.force_click(create_account)
        t.sleep(2)

    @sleeper
    def __account_created(self):
        logging.warning("Has the account been created?")
        s = input("[y/N]: ").lower()
        if s == "y":
            write_if_complete(
                email=self.username,
                password=self.password,
                domain="interia",
                country="pl",
            )
        elif s == "n":
            self.failed_inputs += 1
            logging.error("Account was not successfully created, please try again.")
        else:
            logging.error("The answer provided is not y or n! PLEASE INSERT CORRECT ANSWER...")
            if self.failed_inputs < 3:
                self.__account_created()
            else:
                raise ValueError("The answer provided was not y or n!!!")

    def _create(self):
        """
        Creates the email.
        """
        self.driver.get("https://konto-pocztowe.interia.pl/#/nowe-konto/darmowe")
        t.sleep(0.55)
        self.__deal_with_cookies()
        self.__deal_with_name()
        self.__deal_with_surname()
        self.__deal_with_username()
        self.__deal_with_day()
        self.__deal_with_month()
        self.__deal_with_year()
        self.__deal_with_passwords()
        self.__deal_with_gender()
        self.__accept_bad_conditions()
        self.__finalize_account_creation()
        self.__account_created()
        self.driver.quit()
