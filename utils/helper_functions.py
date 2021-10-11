import random
import hashlib
from faker import Faker
import re
import os
import random

user_path = None  # Give it a safe place to store and update your accounts.txt file


def credential_creator(fullname=False):
    integer_ran = random.randint(0, 100000)
    fullname = Faker().name()
    email = fullname.replace(" ", "") + str(integer_ran)

    pwd = hashlib.sha224(
        b"Nobody inspects the spammish repetition" + bytes(integer_ran)).hexdigest()[0:12] + "!"
    return (fullname, email, pwd)


def birthday_creator():
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(1950, 2002)
    return day, month, year


def write_if_complete(email: str, password: str, domain: str, country="com"):
    if user_path == None:
        user_path = os.getcwd()
    f = open(f"{user_path}/accounts.txt", "a+")
    f.write(f"{email}@{domain}.{country}:{password}\n")
    f.close()
