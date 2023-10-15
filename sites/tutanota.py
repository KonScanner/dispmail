from utils.Config import Config, SleepConfig
from selenium import webdriver
import time as t
from utils.helper_functions import credential_creator, write_if_complete
from webdriver_manager.chrome import ChromeDriverManager
import logging

logging.basicConfig(level=logging.INFO)


class TutaAccounts(Config):

    """
    This function is used to register a new email on the TutaNota website.
    """

    def __init__(self):
        Config.__init__(self)
        SleepConfig.sleep_amount = 0.15
        self.recovery = True
        self.driver = webdriver.Chrome(
            ChromeDriverManager().install(), options=Config(headless=False).options
        )
        self.failed_inputs = 0
        self.driver.maximize_window()
        (_, email, pwd) = credential_creator(fullname=False)
        self.username = email
        self.password = pwd

    @Config.sleeper
    def __account_created(self, recovery_key: str = ""):
        logging.warning("Has the account been created?")
        s = input("[y/N]: ").lower()
        if s == "y":
            t.sleep(3)
            if self.recovery:
                recovery_key = self.__save_recovery()
            write_if_complete(
                email=self.username,
                password=f"{self.password}:{recovery_key}",
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

    @Config.sleeper
    def __select_signup(self):
        signup = self.force_find(
            driver=self.driver,
            element_str="/html/body/div/div[3]/div[2]/div/div[1]/div[2]/button[1]/div/div",
            search_type="xpath",
        )
        self.force_click(signup)
        t.sleep(4)

    @Config.sleeper
    def __select_free_version(self):
        free_version = self.force_find(
            driver=self.driver,
            element_str="/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[3]/div[1]/div/div[1]/div[5]/button/div",
            search_type="xpath",
        )
        self.force_click(free_version)

    @Config.sleeper
    def __select_checkboxes(self):
        checkboxes = [
            self.driver.find_element_by_css_selector(
                "#modal > div:nth-child(2) > div > div > div > div:nth-child(2) > div:nth-child(1) >"
                " div > input[type=checkbox]"
            )
        ]
        checkboxes.append(
            self.driver.find_element_by_css_selector(
                "#modal > div:nth-child(2) > div > div > div > div:nth-child(2) > div:nth-child(2) >"
                " div > input[type=checkbox]"
            )
        )
        checkboxes.append(
            self.driver.find_element_by_css_selector(
                "#modal > div:nth-child(2) > div > div > div > div.flex-center.dialog-buttons >"
                " button:nth-child(2)"
            )
        )
        for item in checkboxes:
            self.force_click(item)
        t.sleep(3)

    @Config.sleeper
    def __deal_with_username(self):
        username = self.driver.find_element_by_css_selector(
            "#signup-account-dialog > div > div.text-field.rel.overflow-hidden.text.pt > div > div"
            " > div > div.flex-grow.rel > input"
        )
        username.send_keys(self.username)

    @Config.sleeper
    def __deal_with_password_1(self):
        pass_1 = self.driver.find_element_by_css_selector(
            "#signup-account-dialog > div > div:nth-child(2) > div:nth-child(1) > div > div > div >"
            " div.flex-grow.rel > input.input"
        )
        pass_1.send_keys(self.password)

    @Config.sleeper
    def __deal_with_password_2(self):
        pass_2 = self.driver.find_element_by_css_selector(
            "#signup-account-dialog > div > div:nth-child(2) > div:nth-child(2) > div > div > div > div.flex-grow.rel > input"
        )
        pass_2.send_keys(self.password)

    def __deal_with_passwords(self):
        self.__deal_with_password_1()
        self.__deal_with_password_2()

    @Config.sleeper
    def __deal_with_final_checkboxes(self):
        checkboxes = [
            self.driver.find_element_by_xpath(
                "/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[3]/div/input"
            )
        ]
        checkboxes.append(
            self.driver.find_element_by_xpath(
                "/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[4]/div/input"
            )
        )
        for item in checkboxes:
            self.force_click(item)

    def __finalize_account_creation(self):
        create_account = self.driver.find_element_by_xpath(
            "/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[2]/div/div[5]/button/div"
        )
        self.force_click(create_account)

    def __save_recovery(self):
        return (
            self.driver.find_element_by_xpath(
                "/html/body/div/div[2]/div/div/div/div/div/div[2]/div/div/div[3]/div[2]"
            )
            .text.strip("")
            .replace("\n", "")
        )

    def _create(self):
        """
        Creates the email.
        """
        self.driver.get("https://mail.tutanota.com/login")
        t.sleep(1)
        self.__select_signup()
        self.__select_free_version()
        self.__select_checkboxes()
        self.__deal_with_username()
        self.__deal_with_passwords()
        self.__deal_with_final_checkboxes()
        self.__finalize_account_creation()
        self.__account_created()
        self.driver.quit()
