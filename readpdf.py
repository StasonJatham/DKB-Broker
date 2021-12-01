# -*- coding: cp852 -*-

# https://realpython.com/pdf-python/
from PyPDF2 import PdfFileReader
import fitz  # this is pymupdf
from pathlib import Path
import re
from datetime import datetime
import requests


import time

from pathlib import Path

import re
from bs4 import BeautifulSoup as bs


def extract_information(pdf_path):

    # with fitz.open(pdf_path) as doc:
    #    text = ""
    #    for page in doc:
    #        text += page.get_text()
    # print(text)

    with open(pdf_path, 'rb') as f:
        pdf = PdfFileReader(f)
        information = pdf.getDocumentInfo()
        number_of_pages = pdf.getNumPages()

    txt = f"Information about {pdf_path}"
    '''
    txt = f"""
    Information about {pdf_path}:
    Author: {information.author}
    Creator: {information.creator}
    Producer: {information.producer}
    Subject: {information.subject}
    Title: {information.title}
    Number of pages: {number_of_pages}
    """
    '''

    print(txt)
    return information


def get_wkn(text: str):
    wkn_regex = r"(WKN_)(.*?)(?=_)"
    wkn = ""
    matches = re.finditer(wkn_regex, text, re.MULTILINE)
    for match in matches:
        wkn = match.group()

    wkn = wkn.replace("WKN_", "")
    return wkn


def get_kosteninfo_company(text: str):
    kosteninfo_company = r"(?<=Wertpapier )(.*?)(?=vom)"
    koco = ""
    matches = re.finditer(kosteninfo_company, text, re.MULTILINE)
    for match in matches:
        koco = match.group()
    return koco


def get_datetime(text: str):
    date_time = r"(?<=vom)(.*?)(?=zu)"
    dt = ""
    matches = re.finditer(date_time, text, re.MULTILINE)
    for match in matches:
        dt = match.group()

    dt = "".join(dt.split()).replace("_", "")

    if "," in dt:
        datetime_object = datetime.strptime(
            dt, '%d.%m.%Y,%H:%M')
    else:
        datetime_object = datetime.strptime(
            dt, '%d.%m.%Y')
    return datetime_object


def get_document_title(text: str):

    if "dividend" in text.lower():
        dividend_re = r"(?<=_-_)(.*?)((?=_vom))"
        title = ""
        matches = re.finditer(dividend_re, text, re.MULTILINE)
        for match in matches:
            title = match.group()

        subtitle = title.split("_")[1] if len(title.split("_")) > 0 else ""
        title = title.split("_")[0] if "_" in title else title
        return title, subtitle

    else:
        title_re = r"(?<=/\d{14}/)(.*?)((?=_)|(?= zu))"
        title = ""
        matches = re.finditer(title_re, text, re.MULTILINE)
        for match in matches:
            title = match.group()

        subtitle_re = r"(?<=_-_.{13})(.*?)((?=_vom))"
        subtitle = ""
        matches = re.finditer(subtitle_re, text, re.MULTILINE)
        for match in matches:
            subtitle = match.group()

        return title, subtitle


def wkn_enrich(wkn: str):
    # https://www.boerse-muenchen.de/Aktie/A1H92V
    stuttgart_url = f"https://www.boerse-stuttgart.de/de-de/produkte/aktien/stuttgart/{wkn}"
    boerse_stuttgart = requests.get(stuttgart_url)

    soup = bs(boerse_stuttgart.text, 'html.parser')

    symbol = soup.select_one(
        '#Daten-\&-Zahlen > div > div > div > div:nth-child(3) > div > dl.bsg-description-list.bsg-fs-master-data__col.bsg-fs-master-data__list.bsg-fs-master-data__list--first > dd:nth-child(6)').text

    header = soup.select_one(
        'body > main > div.bsg-ribbon.bsg-fs-header-hint > div > div')

    company = header.select_one("h1").text.strip()
    isin = header.select_one(
        "div > strong:nth-child(2)").text.strip().replace("ISIN ", "")

    return {
        "symbol": symbol,
        "company": company,
        "isin": isin
    }


def parse_kosteninformation(file: str):
    text = ""
    with fitz.open(file) as doc:
        for page in doc:
            text += page.get_text()

    anlagebetrag_re = r"(?<=Anlagebetrag\s)(.*?)(?= )"
    # wkn_re = r"(?<=Finanzinstrument)(.*?)(?=dargestellt)"
    company_re = r"(?<=dargestellt:\s)(.*?)(?=\n)"
    stueck_re = r'(?<=Stck )(.*?)(?=\n)'
    ausfuehrplatz_re = r'(?<=Ausfhrungsplatz\n)(.*?)(?=\n)'
    gesamtkosten_re = r"(?<=Wertentwicklung\s)(.*?)(?=\n)"
    gesamtkoste_pct_re = r"(?<=\s)(.*?)(?= % p\.a\.)"

    anlagebetrag = ""
    matches = re.finditer(anlagebetrag_re, text, re.MULTILINE)
    for match in matches:
        anlagebetrag = match.group()

    company = ""
    matches = re.finditer(company_re, text, re.MULTILINE)
    for match in matches:
        company = match.group()

    stueck = ""
    matches = re.finditer(stueck_re, text, re.MULTILINE)
    for match in matches:
        stueck = match.group()

    ausfuehrplatz = ""
    matches = re.finditer(ausfuehrplatz_re, text, re.MULTILINE)
    for match in matches:
        ausfuehrplatz = match.group()

    gesamtkosten = ""
    matches = re.finditer(gesamtkosten_re, text, re.MULTILINE)
    for match in matches:
        gesamtkosten = match.group()

    gesamtkoste_pct = ""
    matches = re.finditer(gesamtkoste_pct_re, text, re.MULTILINE)
    for match in matches:
        gesamtkoste_pct = match.group()

    return {
        "amount": anlagebetrag.replace(",", "."),
        "company": company,
        # "stocks": stueck,
        # "market": ausfuehrplatz,
        "total_fee": gesamtkosten.replace(" ?", "").replace(",", "."),
        "total_fee_pct": gesamtkoste_pct.replace(",", ".")
    }


def parse_dividend(file: str):
    text = ""
    with fitz.open(file) as doc:
        for page in doc:
            text += page.get_text()

    dividend_re = r"(?<=Ausmachender Betrag\n)(.*?)(?=\n)"
    capitalgains_re = r"(?<=Kapitalertragsteuerpflichtige Dividende\n)(.*?)(?=\n)"
    sparpauschale_verrechnet_re = r"(?<=Verrechneter Sparer-Pauschbetrag\n)(.*?)(?= )"
    calc_base_capitalgains_re = r"(?<=Berechnungsgrundlage fr die Kapitalertragsteuer\n)(.*?)(?=\n)"
    dividend_type_re = r"(?<=Art der Dividende\n)(.*?)(?=\n)"
    country_of_origin_re = r"(?<=Herkunftsland\n)(.*?)(?=\n)"
    dividen_per_stock_re = r"(?<=Dividende pro Stck\n)(.*?)(?=\n)"
    dividen_forex_re = r"(?<=Dividende pro Stck\n)(.*?)(?=\n)\n.*(?=\n)"
    bestandsstichtag_re = r"(?<=Bestandsstichtag\n)(.*?)(?=\n)"
    extag_re = r"(?<=Ex-Tag\n)(.*?)(?=\n)"
    geschaeftsjahr_re = r"(?<=Gesch„ftsjahr\n)(.*?)(?=\n)"
    zahlbarkeitstag_re = r"(?<=Zahlbarkeitstag\n)(.*?)(?=\n)"
    stockcount_re = r"(?<=Stck )(.*?)(?=\n)"
    latest_sparpauschale_re = r"(?<=Nachher\n)(.*?)(?=\n)\n.*\n.*"

    dividen_forex = ""
    matches = re.finditer(dividen_forex_re, text, re.MULTILINE)
    for match in matches:
        dividen_forex = match.group()

    dividen_per_stock = dividen_forex.split('\n')[0].replace(",", ".")
    dividen_forex = dividen_forex.split('\n')[1] if len(
        dividen_forex.split('\n')) > 0 else ""

    latest_sparpauschale = ""
    matches = re.finditer(latest_sparpauschale_re, text, re.MULTILINE)
    for match in matches:
        latest_sparpauschale = match.group()

    latest_sparpauschale = latest_sparpauschale.split("\n")[2].replace(
        ",", ".") if len(latest_sparpauschale.split("\n")) >= 2 else ""

    return {
        "original_dividend": {
            "dividend_per_stock": dividen_per_stock,
            "currency": dividen_forex,
        }
    }


def parse_buy(file: str):
    text = ""
    with fitz.open(file) as doc:
        for page in doc:
            text += page.get_text()

    amount_count_re = r"(?<=Stck )(.*?)(?=\n)"
    wkn_re = r"(?<=\()([A-Z0-9]{6})(?=\))"
    isin_re = r"([A-Z]{2})([A-Z0-9]{9})([0-9]{1})"
    marketplace_re = r"(?<=Handels-/Ausfhrungsplatz\n)(.*?)(?=\n)"
    # not sure if this works on limit orders
    ordertype_re = r"(?<=Market-Order\n)(.*?)(?=\n)"
    limit_re = r"(?<=Market-Order\n)(.*?)(?=\n).*\n.*"
    fill_price_re = r"(?<=Ausfhrungskurs )(.*?)(?=\n)"
    price_re = r"(?<=Kurswert\n)(.*?)(?=\n)"
    provision_re = r"(?<=Provision\n)(.*?)(?=\n)"
    boersen_fee_re = r"(?<=Transaktionsentgelt B”rse\n)(.*?)(?=\n)"
    deliverycost_re = r"(?<=šbertragungs-/Liefergebhr\n)(.*?)(?=\n)"
    total_procw_with_fee_re = r"(?<=Ausmachender Betrag\n)(.*?)(?=\n)"
    orderdate_re = r"(?<= Datum\n)(.*?)(?=\n)"
    order_open_till_re = r"(?<=Schlusstag/-Zeit )(.*?)(?=\n)"

    amount_count = ""
    matches = re.finditer(amount_count_re, text, re.MULTILINE)
    for match in matches:
        amount_count = match.group()

    wkn = ""
    matches = re.finditer(wkn_re, text, re.MULTILINE)
    for match in matches:
        wkn = match.group()

    isin = ""
    matches = re.finditer(isin_re, text, re.MULTILINE)
    for match in matches:
        isin = match.group()

    marketplace = ""
    matches = re.finditer(marketplace_re, text, re.MULTILINE)
    for match in matches:
        marketplace = match.group()

    ordertype = ""
    matches = re.finditer(ordertype_re, text, re.MULTILINE)
    for match in matches:
        ordertype = match.group()

    limit = ""
    matches = re.finditer(limit_re, text, re.MULTILINE)
    for match in matches:
        limit = match.group()

    fill_price = ""
    matches = re.finditer(fill_price_re, text, re.MULTILINE)
    for match in matches:
        fill_price = match.group()

    price = ""
    matches = re.finditer(price_re, text, re.MULTILINE)
    for match in matches:
        price = match.group()

    provision = ""
    matches = re.finditer(provision_re, text, re.MULTILINE)
    for match in matches:
        provision = match.group()

    boersen_fee = ""
    matches = re.finditer(boersen_fee_re, text, re.MULTILINE)
    for match in matches:
        boersen_fee = match.group()

    deliverycost = ""
    matches = re.finditer(deliverycost_re, text, re.MULTILINE)
    for match in matches:
        deliverycost = match.group()

    total_procw_with_fee = ""
    matches = re.finditer(total_procw_with_fee_re, text, re.MULTILINE)
    for match in matches:
        total_procw_with_fee = match.group()

    orderdate = ""
    matches = re.finditer(orderdate_re, text, re.MULTILINE)
    for match in matches:
        orderdate = match.group()

    order_open_till = ""
    matches = re.finditer(order_open_till_re, text, re.MULTILINE)
    for match in matches:
        order_open_till = match.group()

    return {
        amount_count,
        wkn,
        isin,
        marketplace,
        ordertype,
        limit,
        fill_price,
        price,
        provision,
        boersen_fee,
        deliverycost,
        total_procw_with_fee,
        orderdate,
        order_open_till,
    }


def parse_sell(file: str):
    text = ""
    with fitz.open(file) as doc:
        for page in doc:
            text += page.get_text()

    amount_count_re = r"(?<=Stck )(.*?)(?=\n)"
    wkn_re = r"(?<=\()([A-Z0-9]{6})(?=\))"
    isin_re = r"([A-Z]{2})([A-Z0-9]{9})([0-9]{1})"
    marketplace_re = r"(?<=Handels-/Ausfhrungsplatz\n)(.*?)(?=\n)"
    # not sure if this works on limit orders
    ordertype_re = r"(?<=Market-Order\n)(.*?)(?=\n)"
    limit_re = r"(?<=Market-Order\n)(.*?)(?=\n).*\n.*"  # still need to parse
    fill_price_re = r"(?<=Ausfhrungskurs )(.*?)(?=\n)"
    price_re = r"(?<=Kurswert\n)(.*?)(?=\n)"
    provision_re = r"(?<=Provision\n)(.*?)(?=\n)"
    boersen_fee_re = r"(?<=Transaktionsentgelt B”rse\n)(.*?)(?=\n)"
    deliverycost_re = r"(?<=šbertragungs-/Liefergebhr\n)(.*?)(?=\n)"
    total_procw_with_fee_re = r"(?<=Ausmachender Betrag\n)(.*?)(?=\n)"
    orderdate_re = r"(?<=Datum\n)(.*?)(?=\n)"
    order_open_till_re = r"(?<=Schlusstag/-Zeit )(.*?)(?=\n)"

    started_sale_re = r"(?<=Auftrag vom )(.*?)(?=\n)"
    loss_tax_re = r"(?<=Ver„uáerungsverlust\n)(.*?)(?=\n)"
    booked_loss_re = r"(?<=Eingebuchte Aktienverluste\n)(.*?)(?=\n)"
    calculated_loss_re = r"(?<=Verrechnete Aktienverluste\n)(.*?)(?=\n)"
    latest_sparpauschale_re = r"(?<=Nachher\n)(.*?)(?=\n)\n.*\n.*"
    # needs heavy parsing
    erloese_profit_loss_re = r"(?<=Erl”s\n)(.*?)(?=\n)\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*"
    """
    ant. Ergebnis
    Kauf
    4794417400
    12.04.2018
    Stck
    2,0000
    572,51-
    569,00
    3,51- (D)
    Summe aller Ertr„ge nach Differenzmethode und/oder Ersatzbemessungsgrundlage
    3,51-
    """

    amount_count = ""
    matches = re.finditer(amount_count_re, text, re.MULTILINE)
    for match in matches:
        amount_count = match.group()

    amount_count = ""
    matches = re.finditer(amount_count_re, text, re.MULTILINE)
    for match in matches:
        amount_count = match.group()

    wkn = ""
    matches = re.finditer(wkn_re, text, re.MULTILINE)
    for match in matches:
        wkn = match.group()

    isin = ""
    matches = re.finditer(isin_re, text, re.MULTILINE)
    for match in matches:
        isin = match.group()

    marketplace = ""
    matches = re.finditer(marketplace_re, text, re.MULTILINE)
    for match in matches:
        marketplace = match.group()

    ordertype = ""
    matches = re.finditer(ordertype_re, text, re.MULTILINE)
    for match in matches:
        ordertype = match.group()

    limit = ""
    matches = re.finditer(limit_re, text, re.MULTILINE)
    for match in matches:
        limit = match.group()

    fill_price = ""
    matches = re.finditer(fill_price_re, text, re.MULTILINE)
    for match in matches:
        fill_price = match.group()

    price = ""
    matches = re.finditer(price_re, text, re.MULTILINE)
    for match in matches:
        price = match.group()

    provision = ""
    matches = re.finditer(provision_re, text, re.MULTILINE)
    for match in matches:
        provision = match.group()

    boersen_fee = ""
    matches = re.finditer(boersen_fee_re, text, re.MULTILINE)
    for match in matches:
        boersen_fee = match.group()

    deliverycost = ""
    matches = re.finditer(deliverycost_re, text, re.MULTILINE)
    for match in matches:
        deliverycost = match.group()

    total_procw_with_fee = ""
    matches = re.finditer(total_procw_with_fee_re, text, re.MULTILINE)
    for match in matches:
        total_procw_with_fee = match.group()

    orderdate = ""
    matches = re.finditer(orderdate_re, text, re.MULTILINE)
    for match in matches:
        orderdate = match.group()

    order_open_till = ""
    matches = re.finditer(order_open_till_re, text, re.MULTILINE)
    for match in matches:
        order_open_till = match.group()

    return {
        "count": amount_count,
        "wkn": wkn,
        "isin": isin,
        "marketplace": marketplace,
        "ordertype": ordertype,
        "fill_price": fill_price,
        "price": price,
        "provision": provision,
        "total_procw_with_fee": total_procw_with_fee,
        "order_open_till": order_open_till,

        "boersen_fee": boersen_fee,  # broken
        "deliverycost": deliverycost,  # broken
        "limit": limit,  # broken
        "orderdate": orderdate,
    }


def main():

    pathlist = Path("dkb-pdfs").glob('**/*.pdf')
    for path in pathlist:
        # because path is object not string
        path_in_str = str(path)

        wkn = get_wkn(path_in_str)
        koco = get_kosteninfo_company(path_in_str)
        date_time = get_datetime(path_in_str)
        title, subtitle = get_document_title(path_in_str)

        # extract_information(path_in_str)

        print("-----------------------")
        print(path_in_str)
        print(f"WKN: {wkn}")
        print(f"Company: {koco}")
        print(f"Datetime: {str(date_time)}")
        print(f"Title: {title}")
        print(f"Subtitle: {subtitle}")
        print("-----------------------")

    # works so far still todo on dividend
    """
    test = parse_kosteninformation(
        "")
    print(test)

    test = parse_dividend(
        ""
    )
    print(test)    
    
    test = parse_buy(
        ""
    )
    
    # {"symbol": symbol,"company": company,"isin": isin}
    wkn_enrich(wkn)
    # print(wkn_enrich("A0D94M"))
    """

    # sale with loss
    test = parse_sell(
        "")
    print(test)
    # sale with profit
    test = parse_sell(
        "")


if __name__ == '__main__':
    main()
