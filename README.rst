====================================================
`DispMail <https://konscanner.github.io/dispmail/>`_
====================================================


Disposable emails. Sign up for stuff without giving your personal information away.

.. contents::

About
-----

This project was created with a single-use purpose in mind. That being anonymity. Specifically when it comes to signing up for events/newsletters or trial accounts for things that one might like to use **without** having to provide their real email address, or having to go through the process of using their phone number to create a new email.

This is done by leveraging the power of the `Selenium <https://www.selenium.dev/downloads/>`_ webdriver and email providers such as  `TutaNota <https://tutanota.com/>`_ and `Interia <https://poczta.interia.pl/logowanie/?b=-70#iwa_source=sg_ikona>`_ that do not require using a mobile number or a secondary email to authenticate the newly generated email.

Installation
------------

Manual Install

- Install `requirements.txt`

- `Selenium <https://www.selenium.dev/downloads/>`_ webdriver
	
- `ChromeWebDriver <https://chromedriver.chromium.org/downloads>`_  browser (or `Gecko <https://github.com/mozilla/geckodriver/releases>`_ if you prefer)
