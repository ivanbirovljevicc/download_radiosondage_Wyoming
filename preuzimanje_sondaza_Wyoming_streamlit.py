import streamlit as st
import os
import datetime
import time
import zipfile
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# --- KONFIGURACIJA I KONSTANTE ---
WAIT_TIME = 15

# --- FUNKCIJA ZA PODEŠAVANJE SELENIUMA ---
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("window-size=1920,1080")
    
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- POMOĆNE FUNKCIJE ---
def generisi_datume(godina):
    start_datum = datetime.date(godina, 1, 1)
    kraj_datum = datetime.date(godina, 12, 31)
    if godina == datetime.date.today().year:
        kraj_datum = datetime.date.today() - datetime.timedelta(days=1)
        
    lista_datuma = []
    trenutni_datum = start_datum
    while trenutni_datum <= kraj_datum:
        lista_datuma.append(trenutni_datum)
        trenutni_datum += datetime.timedelta(days=1)
    return lista_datuma

# --- INTERFEJS ---
st.set_page_config(page_title="UWyo Sounding Downloader", page_icon="🌤️")
st.title("🌤️ UWyo Sounding CSV Downloader")

with st.sidebar:
    st.header("Podešavanja")
    stanica_kod = st.text_input("KOD STANICE", value="13275")
    godina = st.number_input("GODINA", min_value=1950, max_value=2025, value=2018)
    vremena_za_rad = st.multiselect("Termini (UTC)", ["00", "06", "12", "18"], default=["00", "12"])

if st.button("🚀 Pokreni preuzimanje"):
    lista_datuma = generisi_datume(godina)
    total_attempts = len(lista_datuma) * len(vremena_za_rad)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_expander = st.expander("Log operacija", expanded=True)
    
    uspesni_fajlovi = {}
    
    driver = None
    try:
        driver = setup_driver()
        count = 0
        for datum in lista_datuma:
            for vreme in vremena_za_rad:
                count += 1
                progress_bar.progress(count / total_attempts)
                
                datum_str = datum.strftime('%Y-%m-%d')
                status_text.text(f"Obrađujem: {datum_str} {vreme} UTC")
                
                datetime_str = f"{datum_str} {vreme}:00:00"
                target_url = f"https://weather.uwyo.edu/wsgi/sounding?datetime={datetime_str}&id={stanica_kod}&type=TEXT%3ALIST&src=BUFR"
                
                try:
                    driver.get(target_url)
                    csv_link_xpath = "//a[contains(@href, 'type=TEXT:CSV')]"
                    csv_link = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, csv_link_xpath))
                    )
                    
                    csv_url = csv_link.get_attribute("href")
                    driver.get(csv_url)
                    csv_content = driver.find_element(By.TAG_NAME, "pre").text if "pre" in driver.page_source else driver.page_source
                    
                    if len(csv_content) > 100:
                        filename = f"{stanica_kod}_{datum.strftime('%Y%m%d')}{vreme}.csv"
                        uspesni_fajlovi[filename] = csv_content
                        log_expander.write(f"✅ {filename}")
                except:
                    log_expander.write(f"❌ {datum_str} {vreme}UTC - Nema podataka")
                
                time.sleep(0.1)

        if uspesni_fajlovi:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zf:
                for name, content in uspesni_fajlovi.items():
                    zf.writestr(name, content)
            
            st.download_button("📥 Preuzmi ZIP", zip_buffer.getvalue(), f"Sondaze_{stanica_kod}.zip")

    finally:
        if driver:
            driver.quit()
