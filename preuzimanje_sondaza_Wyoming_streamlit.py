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
    options.add_argument("window-size=1920,1080")
    
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- POMOĆNA FUNKCIJA ZA DATUME SA MESECEM ---
def generisi_datume(godina, meseci_izbor):
    lista_datuma = []
    # Mapiranje imena meseci na brojeve
    meseci_map = {
        "Januar": 1, "Februar": 2, "Mart": 3, "April": 4, "Maj": 5, "Jun": 6,
        "Jul": 7, "Avgust": 8, "Septembar": 9, "Oktobar": 10, "Novembar": 11, "Decembar": 12
    }
    
    for mesec_ime in meseci_izbor:
        m_num = meseci_map[mesec_ime]
        # Određivanje broja dana u mesecu
        if m_num == 12:
            sledeci_mesec = datetime.date(godina + 1, 1, 1)
        else:
            sledeci_mesec = datetime.date(godina, m_num + 1, 1)
        
        poslednji_dan = (sledeci_mesec - datetime.timedelta(days=1)).day
        
        for dan in range(1, poslednji_dan + 1):
            d = datetime.date(godina, m_num, dan)
            # Ne idemo u budućnost 
            if d < datetime.date.today():
                lista_datuma.append(d)
    return lista_datuma

# --- INTERFEJS ---
st.set_page_config(page_title="UWyo Downloader v2", page_icon="🌤️")
st.title("🌤️ UWyo Sounding CSV Downloader")

with st.sidebar:
    st.header("Podešavanja")
    stanica_kod = st.text_input("KOD STANICE", value="13275")
    godina = st.number_input("GODINA", min_value=1950, max_value=2025, value=2018)
    
    svi_meseci = ["Januar", "Februar", "Mart", "April", "Maj", "Jun", 
                  "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"]
    meseci_izbor = st.multiselect("Izaberi mesece", svi_meseci, default=["Januar"])
    
    vremena_za_rad = st.multiselect("Termini (UTC)", ["00", "06", "12", "18"], default=["00", "12"])

if st.button("🚀 Pokreni preuzimanje"):
    if not meseci_izbor:
        st.warning("Izaberite barem jedan mesec.")
    else:
        lista_datuma = generisi_datume(godina, meseci_izbor)
        total_attempts = len(lista_datuma) * len(vremena_za_rad)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        mem_info = st.empty() # Za prikaz MB u RAM-u
        log_expander = st.expander("Log operacija", expanded=True)
        
        uspesni_fajlovi = {}
        ukupna_velicina_bajtova = 0
        
        driver = None
        try:
            driver = setup_driver()
            count = 0
            for datum in lista_datuma:
                for vreme in vremena_za_rad:
                    count += 1
                    progress_bar.progress(count / total_attempts)
                    
                    datum_str = datum.strftime('%Y-%m-%d')
                    status_text.text(f"Obrađujem: {datum_str} {vreme} UTC ({count}/{total_attempts})")
                    
                    target_url = f"https://weather.uwyo.edu/wsgi/sounding?datetime={datum_str}%20{vreme}:00:00&id={stanica_kod}&type=TEXT%3ALIST&src=BUFR"
                    
                    try:
                        driver.get(target_url)
                        csv_link_xpath = "//a[contains(@href, 'type=TEXT:CSV')]"
                        csv_link = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, csv_link_xpath)))
                        
                        csv_url = csv_link.get_attribute("href")
                        driver.get(csv_url)
                        csv_content = driver.find_element(By.TAG_NAME, "pre").text if "pre" in driver.page_source else driver.page_source
                        
                        if len(csv_content) > 100:
                            filename = f"{stanica_kod}_{datum.strftime('%Y%m%d')}{vreme}.csv"
                            uspesni_fajlovi[filename] = csv_content
                            
                            # Ažuriranje brojača memorije [cite: 13, 25]
                            ukupna_velicina_bajtova += sys.getsizeof(csv_content)
                            mb_size = ukupna_velicina_bajtova / (1024 * 1024)
                            mem_info.metric("Zauzeće RAM-a", f"{mb_size:.2f} MB")
                            
                            log_expander.write(f"✅ {filename}")
                    except:
                        log_expander.write(f"❌ {datum_str} {vreme}UTC - Nema podataka")
                    
                    time.sleep(0.1)

            status_text.success(f"Završeno! Ukupno fajlova: {len(uspesni_fajlovi)}")

            if uspesni_fajlovi:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zf:
                    for name, content in uspesni_fajlovi.items():
                        zf.writestr(name, content)
                
                st.download_button("📥 Preuzmi ZIP sa podacima", zip_buffer.getvalue(), f"Sondaze_{stanica_kod}_{godina}.zip")

        finally:
            if driver:
                driver.quit()
