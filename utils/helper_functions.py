import random
import hashlib
from faker import Faker
import os

USER_PATH = os.getcwd()  # Give it a safe place to store and update your accounts.txt file


def credential_creator(fullname=False):
    """
    Creates a random email and password.

    :param fullname: Return full name of person Defaults to False.
    :return: fullname, email, password
    :rtype: str, str, str
    """
    integer_ran = random.randint(0, 100000)
    fullname = Faker().name()
    email = fullname.replace(" ", "") + str(integer_ran)

    password = (
        hashlib.sha256(b"Nobody inspects the spammish repetition" + bytes(integer_ran)).hexdigest()[
            :12
        ]
        + "!"
    )

    return (fullname, email, password)


def birthday_creator():
    """
    Creates a random birthday for the user.

    :return: Returns birthday in dd, mm, yyyy format
    :rtype: str
    """
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(1950, 2002)
    return day, month, year


def write_if_complete(
    email: str, password: str, domain: str, country="com", user_path: str = USER_PATH
) -> None:
    """
    Writes file to disk if the user deems the creation is complete.

    :param email: Email to write to file
    :param password: Password to write to file
    :param domain: Domain to write to file
    :param country: Domain ending write to file
    :param user_path: Path to write the file

    :rtpye: [None]
    """
    user_path = os.getcwd() if user_path is None else USER_PATH
    with open(f"{user_path}/accounts.txt", "a+") as f:
        f.write(f"{email}@{domain}.{country}:{password}\n")
