import streamlit as st
import os
import datetime
import time
import zipfile
import sys
import requests # Dodajemo requests za stabilnije čitanje podataka
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# --- KONFIGURACIJA STRANICE ---
st.set_page_config(page_title="UWyo Arhiver", page_icon="🌤️", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Konfiguracija")
    stanica_kod = st.text_input("📍 KOD STANICE", value="13275")
    trenutna_godina = datetime.date.today().year
    godina = st.number_input("📅 GODINA", min_value=1900, max_value=trenutna_godina)
    vremena = st.multiselect("⏰ TERMINI (UTC)", ["00", "06", "12", "18"], default=["00", "12"])
    meseci_opcije = ["Januar", "Februar", "Mart", "April", "Maj", "Jun", 
                     "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"]
    meseci_izbor = st.multiselect("🗓️ IZABERI MESECE", meseci_opcije, default=["Januar"])
    st.info("💡 Ova verzija čita podatke direktno u memoriju bez skidanja pojedinačnih fajlova.")

st.title("🌪️ UWyo Sounding Data Downloader")

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # KLJUČNO: Isključujemo Chrome-ov podrazumevani download prompt
    prefs = {
        "download.default_directory": "/dev/null", # Šalje download u "crnu rupu"
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    return webdriver.Chrome(service=service, options=options)

if st.button("🚀 POKRENI PREUZIMANJE"):
    if not meseci_izbor:
        st.error("Izaberite mesece!")
    else:
        meseci_map = {m: i+1 for i, m in enumerate(meseci_opcije)}
        izabrani_brojevi = [meseci_map[m] for m in meseci_izbor]
        uspesni_fajlovi = {}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_expander = st.expander("Log operacija", expanded=True)

        driver = setup_driver()
        
        try:
            lista_datuma = []
            curr = datetime.date(godina, 1, 1)
            kraj = datetime.date(godina, 12, 31)
            danas = datetime.date.today()

            while curr <= kraj:
                if curr.month in izabrani_brojevi and curr <= danas:
                    lista_datuma.append(curr)
                curr += datetime.timedelta(days=1)

            total_tasks = len(lista_datuma) * len(vremena)
            count = 0

            for datum in lista_datuma:
                for vreme in vremena:
                    count += 1
                    datum_str = datum.strftime('%Y-%m-%d')
                    izvor = "BUFR" if godina >= 2018 else "FM35"
                    target_url = (f"https://weather.uwyo.edu/wsgi/sounding?"
                                 f"datetime={datum_str}%20{vreme}:00:00&id={stanica_kod}&type=TEXT%3ALIST&src={izvor}")
                    
                    try:
                        driver.get(target_url)
                        # Pronalazimo URL, ali NE idemo na njega preko driver.get()
                        csv_link_element = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'type=TEXT:CSV')]"))
                        )
                        csv_url = csv_link_element.get_attribute("href")
                        
                        # TRIK: Koristimo Cookies iz Seleniuma da skinemo fajl preko requests-a u memoriju
                        # Ovo sprečava Browser da pokrene fizički download fajla
                        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
                        response = requests.get(csv_url, cookies=cookies)
                        
                        if response.status_code == 200 and len(response.text) > 100:
                            filename = f"{stanica_kod}_{datum.strftime('%Y%m%d')}_{vreme}UTC.csv"
                            uspesni_fajlovi[filename] = response.text
                            log_expander.write(f"✅ {filename}")
                    except:
                        log_expander.write(f"❌ {datum_str} {vreme}UTC - Nedostupno")
                    
                    progress_bar.progress(count / total_tasks)
                    status_text.text(f"Status: {count}/{total_tasks}")

            if uspesni_fajlovi:
                st.success(f"Preuzeto {len(uspesni_fajlovi)} fajlova.")
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for name, content in uspesni_fajlovi.items():
                        zf.writestr(name, content)
                
                st.download_button(
                    label="📥 PREUZMI ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"Sondaze_{stanica_kod}_{godina}.zip",
                    mime="application/zip",
                    key="download_btn"
                )
                st.balloons()

        finally:
            driver.quit()
