import streamlit as st
import os
import datetime
import time
import zipfile
import sys
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# --- FUNKCIJA ZA PODEŠAVANJE SELENIUMA ---
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("window-size=1200,800")
    
    # Korišćenje Chromium-a koji je standard za Streamlit Cloud
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- INTERFEJS ---
st.set_page_config(page_title="UWyo Sounding Downloader", page_icon="🌤️")
st.title("🌤️ UWyo Sounding Data Downloader")
st.markdown("Preuzimanje originalnih BUFR (2018+) i FM35 (pre 2018) podataka.")

col1, col2 = st.columns(2)
with col1:
    stanica_kod = st.text_input("KOD STANICE", value="13275")
    godina = st.number_input("GODINA", min_value=1973, max_value=2026, value=2015)
with col2:
    vremena = st.multiselect("TERMINI (UTC)", ["00", "06", "12", "18"], default=["00", "12"])

meseci_opcije = ["Januar", "Februar", "Mart", "April", "Maj", "Jun", "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"]
meseci_izbor = st.multiselect("IZABERI MESECE", meseci_opcije, default=["Januar"])

if st.button("🚀 POKRENI PREUZIMANJE"):
    # Mapiranje meseci
    meseci_map = {m: i+1 for i, m in enumerate(meseci_opcije)}
    izabrani_brojevi = [meseci_map[m] for m in meseci_izbor]
    
    uspesni_fajlovi = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_expander = st.expander("Detaljan log operacija", expanded=True)

    driver = setup_driver()
    
    try:
        # Generisanje liste datuma samo za izabrane mesece
        lista_datuma = []
        start_date = datetime.date(godina, 1, 1)
        end_date = datetime.date(godina, 12, 31)
        
        curr = start_date
        while curr <= end_date:
            if curr.month in izabrani_brojevi and curr <= datetime.date.today():
                lista_datuma.append(curr)
            curr += datetime.timedelta(days=1)

        total_tasks = len(lista_datuma) * len(vremena)
        count = 0

        for datum in lista_datuma:
            for vreme in vremena:
                count += 1
                datum_str = datum.strftime('%Y-%m-%d')
                
                # --- KLJUČNA LOGIKA ZA IZVOR ---
                izvor = "BUFR" if godina >= 2018 else "FM35"
                
                target_url = f"https://weather.uwyo.edu/wsgi/sounding?datetime={datum_str}%20{vreme}:00:00&id={stanica_kod}&type=TEXT%3ALIST&src={izvor}"
                
                try:
                    driver.get(target_url)
                    csv_link = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'type=TEXT:CSV')]"))
                    )
                    driver.get(csv_link.get_attribute("href"))
                    
                    content = driver.find_element(By.TAG_NAME, "pre").text
                    
                    if len(content) > 100:
                        filename = f"{stanica_kod}_{datum.strftime('%Y%m%d')}_{vreme}UTC.csv"
                        uspesni_fajlovi[filename] = content
                        log_expander.write(f"✅ {filename} (Izvor: {izvor})")
                except:
                    log_expander.write(f"❌ {datum_str} {vreme}UTC - Nema podataka")
                
                # Update UI
                progress_bar.progress(count / total_tasks)
                status_text.text(f"Obrađeno: {count}/{total_tasks} | Trenutno: {datum_str}")

        if uspesni_fajlovi:
            st.success(f"Preuzeto ukupno {len(uspesni_fajlovi)} fajlova!")
            
            # Pakovanje u ZIP
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for name, content in uspesni_fajlovi.items():
                    zf.writestr(name, content)
            
            st.download_button(
                label="📥 PREUZMI ZIP ARHIVU",
                data=zip_buffer.getvalue(),
                file_name=f"Sondaze_{stanica_kod}_{godina}.zip",
                mime="application/zip"
            )
        else:
            st.warning("Nije pronađen nijedan fajl za izabrane parametre.")

    finally:
        driver.quit()
