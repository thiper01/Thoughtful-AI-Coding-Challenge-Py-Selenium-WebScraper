import csv
import os
import re
import time
from datetime import datetime, timedelta

from RPA.Browser.Selenium import Selenium
from SeleniumLibrary.errors import ElementNotFound

lib = Selenium()
searchPhrase = "test"
category = ""
retrieveMonths = 0
if retrieveMonths == 0:
    retrieveMonths = 1

currentDate = datetime.today()
newsDateRange = currentDate - timedelta(weeks=(retrieveMonths)*4)


def clean_output(path, batch):
    try:
        files = os.listdir(path)
        for file in files:
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path) and int(re.search(r"\d*(?=.png$)", file_path).group()) > 10*batch:
                os.remove(file_path)
        print("All files deleted successfully.")
    except OSError:
        print("Error occurred while deleting files.")


lib.auto_close = False
output_path = "/mnt/e/Documentos/GitHub/Thoughtful-AI-Coding-Challenge/output"
lib.set_screenshot_directory(output_path)
lib.open_available_browser("https://www.latimes.com/",
                           options="page_load_strategy='eager'")
lib.set_selenium_implicit_wait(timedelta(seconds=5))
print(lib.get_selenium_implicit_wait())
lib.wait_and_click_button("data:element:search-button")
lib.wait_until_element_is_visible("name:q")
lib.input_text("name:q", searchPhrase+"\n")
lib.wait_until_element_is_visible("class:select-input")
lib.select_from_list_by_value("class:select-input", "1")
time.sleep(1)
lib.wait_until_page_contains_element("class:promo-wrapper", limit=10)
batch = 1
inTimeRange = True
while inTimeRange:
    while True:
        resultList = lib.get_webelements("class:promo-wrapper")
        try:
            for i in resultList:
                title = lib.get_text(
                    lib.get_webelement("class:promo-title", i))
                description = lib.get_text(
                    lib.get_webelement("class:promo-description", i))
                date = datetime.strptime(lib.get_text(
                    lib.get_webelement("class:promo-timestamp", i)), "%b. %d, %Y")
                if date < newsDateRange:
                    inTimeRange = False
                    break
                if lib.is_element_enabled("name:metering-bottompanel"):
                    shadowroot = lib.get_webelement(
                        "name:metering-bottompanel", shadow=True)
                    closeAd = lib.get_webelement(
                        "class:met-flyout-close", shadowroot)
                    lib.click_element(closeAd)
                try:
                    picture_filename = lib.capture_element_screenshot(
                        lib.get_webelement("class:promo-media", i))
                except ElementNotFound:
                    continue
        except Exception as a:
            print(a)
            clean_output(output_path, batch)
            continue

        else:
            batch += 1
            break
    if inTimeRange:
        while True:
            try:
                lib.click_element_when_visible(
                    "class:search-results-module-next-page")
            except:
                shadowroot = lib.get_webelement(
                    "name:metering-bottompanel", shadow=True)
                closeAd = lib.get_webelement(
                    "class:met-flyout-close", shadowroot)
                lib.click_element(closeAd)
                continue
            else:
                break
