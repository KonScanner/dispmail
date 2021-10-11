import sys
from sites.tutanota import TutaAccounts
from sites.interia import Interia


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
