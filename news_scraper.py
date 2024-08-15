import csv
import logging
import os
import re
import time
from datetime import datetime, timedelta

from RPA.Browser.Selenium import Selenium
from SeleniumLibrary.errors import ElementNotFound

# Set up logging
logging.basicConfig(
    filename='news_scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class CSVHandler:
    def __init__(self, csv_path):
        self.csv_path = csv_path

    def write_data(self, data):
        try:
            with open(self.csv_path, "a", newline='') as file:
                writer = csv.writer(file)
                writer.writerows(data)
            logging.info(f"Data successfully written to {self.csv_path}.")
        except Exception as e:
            logging.error(f"Failed to write data to CSV: {e}")


class Cleaner:
    def __init__(self, output_path):
        self.output_path = output_path

    def clean_output(self, batch):
        try:
            files = os.listdir(self.output_path)
            for file in files:
                file_path = os.path.join(self.output_path, file)
                regex_result = re.search(r"\d*(?=.png$)", file_path)
                if regex_result:
                    file_number = int(regex_result.group())
                    if os.path.isfile(file_path) and file_number > 10 * (batch - 1):
                        os.remove(file_path)
            logging.info(f"All files from batch {batch} deleted successfully.")
        except OSError as e:
            logging.error(f"Error occurred while deleting files: {e}")


class NewsScraper:
    def __init__(self, search_phrase, retrieve_months, category="", output_path="output"):
        self.search_phrase = search_phrase
        self.retrieve_months = retrieve_months if retrieve_months > 0 else 1
        self.category = category
        self.output_path = output_path
        self.lib = Selenium()
        self.csv_data = []

    def setup_browser(self):
        try:
            self.lib.auto_close = False
            self.lib.set_screenshot_directory(self.output_path)
            self.lib.open_available_browser(
                "https://www.latimes.com", options="page_load_strategy='eager'")
            logging.info("Browser setup complete.")
        except Exception as e:
            logging.error(f"Error setting up browser: {e}")

    def search_news(self):
        try:
            self.lib.wait_and_click_button("data:element:search-button")
            self.lib.input_text_when_element_is_visible(
                "name:q", self.search_phrase + "\n")
            logging.info(f"Search initiated for phrase: {self.search_phrase}")
            time.sleep(1)

            if self.category:
                self.lib.wait_until_element_is_visible(
                    "class:search-filter >> class:button")
                self.lib.click_button_when_visible(
                    "class:search-filter >> class:button")
                logging.info(f"Category filter applied: {self.category}")
                while True:
                    try:

                        categories = self.lib.get_webelements(
                            "data:name:Topics >> tag:label")
                        for i in categories:
                            if self.lib.does_element_contain(i, self.category, ignore_case=True):
                                checkbox = self.lib.get_webelement(
                                    "class:checkbox-input-element", i)
                                self.lib.click_element(checkbox)
                                break
                        time.sleep(1)
                    except Exception as e:
                        logging.error(f"Error applying category filter: {e}")
                        continue
                    else:
                        break

            self.lib.wait_until_element_is_visible("class:select-input")
            self.lib.select_from_list_by_value("class:select-input", "1")
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error during search: {e}")

    def scrape_news(self):
        current_date = datetime.today()
        news_date_range = current_date - \
            timedelta(weeks=self.retrieve_months * 4)
        batch = 1
        in_time_range = True

        while in_time_range:
            while True:
                try:
                    self.lib.wait_until_page_contains_element(
                        "class:promo-wrapper")
                    result_list = self.lib.get_webelements(
                        "class:promo-wrapper")

                    for i in result_list:
                        title = self.lib.get_text(
                            self.lib.get_webelement("class:promo-title", i))
                        description = self.lib.get_text(
                            self.lib.get_webelement("class:promo-description", i))
                        date = self.get_article_date(i, current_date)

                        if date <= news_date_range:
                            in_time_range = False
                            break

                        picture_filename = self.capture_screenshot(i)
                        search_phrase_occurrence = self.count_search_phrase_occurrences(
                            title, description)
                        contains_money = self.detect_money(title, description)

                        self.csv_data.append(
                            [title, date, description, picture_filename, search_phrase_occurrence, contains_money])

                except Exception as e:
                    logging.error(f"Error processing result: {e}")
                    Cleaner(self.output_path).clean_output(batch)
                    self.clean_bad_data(batch)
                    logging.info("Trying again...")
                    continue
                else:
                    CSVHandler(self.get_csv_path()).write_data(self.csv_data)
                    logging.info(f"Batch {batch} processed and saved.")
                    batch += 1
                    break

            if in_time_range and not self.go_to_next_page():
                break

    def get_article_date(self, article_element, current_date):
        try:
            date_string = self.lib.get_text(self.lib.get_webelement(
                "class:promo-timestamp", article_element)).replace(".", "").replace(",", "")
            if len(re.search("[A-z]*", date_string).group()) > 3:
                return datetime.strptime(date_string, "%B %d %Y")
            else:
                return datetime.strptime(date_string, "%b %d %Y")
        except ValueError:
            logging.warning(
                f"Invalid date format, using current date as fallback.")
            return current_date

    def capture_screenshot(self, article_element):
        try:
            if self.detect_ad():
                self.close_ad()
            return self.lib.capture_element_screenshot(self.lib.get_webelement("class:promo-media", article_element))
        except ElementNotFound:
            logging.warning("Screenshot capture failed, element not found.")
            return ""

    def count_search_phrase_occurrences(self, title, description):
        word_bag = "; ".join([title, description])
        return word_bag.count(self.search_phrase)

    def detect_money(self, title, description):
        word_bag = "; ".join([title, description])
        return re.search(r"\$\d+(,\d{3})*(\.\d{1,2})?|(\d+\s?(dollars|USD))", word_bag) is not None

    def clean_bad_data(self, batch):
        while len(self.csv_data) > 10 * (batch - 1):
            self.csv_data.pop()

    def go_to_next_page(self):
        while True:
            try:
                next_page = self.lib.get_webelement(
                    "class:search-results-module-next-page")
                try:
                    self.lib.get_webelement("tag:a", next_page)
                except:
                    logging.info("No next page available, ending scrape.")
                    return False
                self.lib.click_element_when_visible(next_page)
                return True
            except Exception as e:
                if self.detect_ad():
                    self.close_ad()
                    logging.warning(
                        "Ad interfered with pagination, closed ad.")
                    continue
                else:
                    logging.error(f"Error trying to go to the next page: {e}")
                    return False

    def detect_ad(self):
        result = self.lib.is_element_enabled(
            "name:metering-bottompanel", missing_ok=True)
        if result:
            logging.info("Ad detected!")
        return self.lib.is_element_enabled("name:metering-bottompanel", missing_ok=True)

    def close_ad(self):
        try:
            shadow_root = self.lib.get_webelement(
                "name:metering-bottompanel", shadow=True)
            close_ad = self.lib.get_webelement(
                "class:met-flyout-close", shadow_root)
            self.lib.click_element(close_ad)
        except Exception as e:
            logging.error(f"Failed to close ad: {e}")
        else:
            logging.info("Closed ad!")

    def get_csv_path(self):
        csv_filename = f"{self.search_phrase.replace(' ', '')}{self.retrieve_months}{self.category}.csv"
        return os.path.join(self.output_path, csv_filename)


if __name__ == "__main__":
    search_phrase = "test"
    category = ""
    retrieve_months = 0
    output_path = "/mnt/e/Documentos/GitHub/Thoughtful-AI-Coding-Challenge/output"

    scraper = NewsScraper(search_phrase, retrieve_months,
                          category, output_path)
    scraper.setup_browser()
    scraper.search_news()
    scraper.scrape_news()
    logging.info("News scraping completed.")
