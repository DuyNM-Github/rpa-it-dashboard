# +
"""Packages and Modules Import"""
from RPA.Browser.Selenium import Selenium
from RPA.Tables import Table
from RPA.Excel.Files import Files
from RPA.FileSystem import FileSystem
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
import configparser
import threading
from pathlib import Path
import shutil
import os

browser = Selenium()
filesys = FileSystem()
excel = Files()
config = configparser.ConfigParser()

config.read('config.ini')

output_folder = f"{os.getcwd()}/"
url = "https://itdashboard.gov"
test_agency = config['DEFAULT']['TestAgency']
MAX_RETRIES = 5


# -

def initial_task():
    if filesys.does_file_exist(output_folder + "agency_data.xlsx") is True:
        filesys.remove_file(output_folder + "agency_data.xlsx")
    excel.create_workbook(output_folder + "agency_data.xlsx", fmt="xlsx")
    excel.save_workbook()
    excel.close_workbook()

    browser.open_available_browser(url, maximized=True)


def extract_agencies_list():
    global agency_table
    browser.click_link("#home-dive-in")
    browser.wait_until_element_is_visible("css:div#agency-tiles-container")
    agencies = browser.find_elements('xpath://*[@id="agency-tiles-widget"]\
                                    /div/div/div/div/div/div/div/a/span[1]')
    spendings = browser.find_elements('xpath://*[@id="agency-tiles-widget"]\
                                    /div/div/div/div/div/div/div/a/span[2]')
    agency_table = {
        "Agency": [agency.text for agency in agencies],
        "Spending": [spending.text for spending in spendings]
    }


def write_agency_list_to_workbook():
    excel.open_workbook(output_folder + "agency_data.xlsx")
    excel.rename_worksheet("Sheet", "Agencies")
    excel.append_rows_to_worksheet(
        content=agency_table,
        name="Agencies",
        header=True
    )
    excel.save_workbook()
    excel.close_workbook()


def load_investment_table():
    browser.click_link(test_agency)
    browser.wait_until_element_is_visible(
        'xpath://*[@id="investments-table-object"]', 120)
    browser.click_element('xpath://*[@id="investments-table-object_last"]')
    retry, complete = 0, False
    while retry < MAX_RETRIES or complete is True:
        try:
            while browser.find_element('id:investments-table-object_first')\
                         .get_attribute('class').find('disabled') != -1:
                pass
            else:
                browser.click_element('xpath://*[@id="investments-table-object_first"]')
                complete = True
                break
        except StaleElementReferenceException:
            retry += 1


def scrape_agency_investment_table():
    load_investment_table()
    global tableData, list_of_links
    tableData = {}
    list_of_links = {}
    headers = [elem.text for elem in browser.find_elements(
           'xpath://*[@id="investments-table-object_wrapper"]//div/table/thead/tr/th'
       )]
    for header in headers:
        if header is not None and header != '':
            tableData[header] = []
    next_page_available = True
    while next_page_available is True:
        col = 1
        for key, value in tableData.items():
            temp_list = [elem.text for elem in browser.find_elements(
                       'xpath://*[@id="investments-table-object"]\
                        /tbody/tr/td[{}]'.format(col)
                   )]
            if key == "UII":
                uiis = browser.find_elements('xpath://*[@id="investments-table-object"]\
                        /tbody/tr/td[{}]'.format(col))
                for uii in uiis:
                    try:
                        list_of_links[uii.text] = uii.find_element(By.TAG_NAME, 'a')\
                                                    .get_attribute('href')
                    except Exception:
                        pass
            value.extend(temp_list)
            col += 1
        if browser.find_element('id:investments-table-object_next')\
                .get_attribute('class').find('disabled') == -1:
            next_page_available = True
            browser.click_element('id:investments-table-object_next')
        else:
            next_page_available = False


def write_investment_to_workbook():
    excel.open_workbook(output_folder + "/agency_data.xlsx")
    excel.create_worksheet(test_agency)
    excel.append_rows_to_worksheet(
        content=tableData,
        name=test_agency,
        header=True
    )
    excel.save_workbook()
    excel.close_workbook()


def start_download_threads():
    thread1 = Threading.thread(target=donwload_pdfs, name="Download Thread")
    thread2 = Threading.thread(target=move_pdfs, name="Move File Thread")
    
    thread1.start()
    thread2.start()
    
    thread2.join()


def download_pdfs():
    for file, link in list_of_links.items():
        browser.go_to(link)
        browser.wait_until_element_is_visible("link:Download Business Case PDF")
        browser.click_link("Download Business Case PDF")
        current_dir = f"{os.getcwd()}/" + file + ".pdf"
        destination = output_folder + file + ".pdf"
        while filesys.does_file_not_exist(current_dir) is True:
            pass
        else:
            break


def move_pdfs():
    source = f"{os.getcwd()}/" + file + ".pdf"
    destination = output_folder + file + ".pdf"
    for file in list_of_links.keys():
        while filesys.does_file_not_exist(destination) is True:
            try:
                shutil.move(source, destination)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    try:
        initial_task()
        extract_agencies_list()
        write_agency_list_to_workbook()
        scrape_agency_investment_table()
        write_investment_to_workbook()
        download_pdfs()
    finally:
        print("Task Ended")
        browser.close_all_browsers()
