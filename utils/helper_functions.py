import random
import hashlib
from faker import Faker
import re
import os
import random

user_path = None  # Give it a safe place to store and update your accounts.txt file


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

    password = hashlib.sha224(
        b"Nobody inspects the spammish repetition" + bytes(integer_ran)).hexdigest()[0:12] + "!"
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


def write_if_complete(email: str, password: str, domain: str, country="com") -> None:
    """
    Writes file to disk if the user deems the creation is complete.

    :param email: Email to write to file
    :param password: Password to write to file
    :param domain: Domain to write to file
    :param country: Domain ending write to file
    :param user_path: Path to write the file

    :rtpye: [None]
    """
    if user_path == None:
        user_path = os.getcwd()
    f = open(f"{user_path}/accounts.txt", "a+")
    f.write(f"{email}@{domain}.{country}:{password}\n")
    f.close()
