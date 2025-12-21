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
WAIT_TIME = 15 [cite: 1]

# --- FUNKCIJA ZA PODEŠAVANJE SELENIUMA (Optimizovano za Cloud) ---
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("window-size=1920,1080")
    
    # Automatsko instaliranje Chrome drajvera koji odgovara okruženju
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- POMOĆNE FUNKCIJE ---
def generisi_datume(godina):
    start_datum = datetime.date(godina, 1, 1) [cite: 8]
    kraj_datum = datetime.date(godina, 12, 31) [cite: 8]
    if godina == datetime.date.today().year:
        kraj_datum = datetime.date.today() - datetime.timedelta(days=1) [cite: 8]
        
    lista_datuma = []
    trenutni_datum = start_datum [cite: 8]
    while trenutni_datum <= kraj_datum: [cite: 8]
        lista_datuma.append(trenutni_datum) [cite: 8]
        trenutni_datum += datetime.timedelta(days=1) [cite: 8]
    return lista_datuma [cite: 9]

# --- GLAVNI STREAMLIT INTERFEJS ---
st.set_page_config(page_title="UWyo Sounding Downloader", page_icon="🌤️")
st.title("🌤️ UWyo Sounding CSV Downloader")

with st.sidebar:
    st.header("Podešavanja")
    stanica_kod = st.text_input("KOD STANICE", value="13275") [cite: 6]
    godina = st.number_input("GODINA", min_value=1950, max_value=datetime.date.today().year, value=2018) [cite: 7]
    vremena_za_rad = st.multiselect("Termini (UTC)", ["00", "06", "12", "18"], default=["00", "12"])

if st.button("🚀 Pokreni preuzimanje"):
    if not stanica_kod:
        st.error("Molimo unesite kod stanice.")
    else:
        lista_datuma = generisi_datume(godina)
        total_attempts = len(lista_datuma) * len(vremena_za_rad) [cite: 17]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_expander = st.expander("Detaljan log operacija", expanded=True)
        
        uspesni_fajlovi = {} # Čuvamo u memoriji: {ime_fajla: sadržaj}
        
        driver = None
        try:
            driver = setup_driver() [cite: 18]
            status_text.info("🤖 Browser pokrenut u pozadini. Počinjem prikupljanje...")
            
            count = 0
            for datum in lista_datuma:
                for vreme in vremena_za_rad:
                    count += 1
                    napredak = count / total_attempts
                    progress_bar.progress(napredak)
                    
                    datum_str = datum.strftime('%Y-%m-%d')
                    status_text.text(f"Obrađujem: {datum_str} {vreme} UTC ({count}/{total_attempts})")
                    
                    # Formiranje URL-a
                    datetime_str = f"{datum_str} {vreme}:00:00"
                    target_url = f"https://weather.uwyo.edu/wsgi/sounding?datetime={datetime_str}&id={stanica_kod}&type=TEXT%3ALIST&src=BUFR" [cite: 9]
                    
                    try:
                        driver.get(target_url)
                        
                        # Čekanje na CSV link pomoću tvog XPath-a
                        csv_link_xpath = "//a[contains(@href, 'type=TEXT:CSV') and contains(text(), 'Comma Separated Values')]" [cite: 11]
                        csv_link = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, csv_link_xpath))
                        )
                        
                        # Umesto klika, uzimamo URL i idemo direktno na njega da pročitamo tekst
                        csv_url = csv_link.get_attribute("href")
                        driver.get(csv_url)
                        
                        # Čitanje sadržaja stranice (sirovi CSV tekst)
                        csv_content = driver.find_element(By.TAG_NAME, "pre").text if "pre" in driver.page_source else driver.page_source
                        
                        if len(csv_content) > 100: # Provera da li ima podataka
                            filename = f"{stanica_kod}_{datum.strftime('%Y%m%d')}{vreme}.csv" [cite: 9]
                            uspesni_fajlovi[filename] = csv_content
                            log_expander.write(f"✅ {filename} - Uspešno")
                        else:
                            log_expander.write(f"⚠️ {datum_str} {vreme}UTC - Nema podataka na stranici")
                            
                    except Exception:
                        log_expander.write(f"❌ {datum_str} {vreme}UTC - Podaci nisu dostupni (Timeout)")
                    
                    time.sleep(0.1) # Mala pauza radi stabilnosti [cite: 1]

            status_text.success(f"Završeno! Prikupljeno fajlova: {len(uspesni_fajlovi)}")
            
            # --- ZIPOVANJE I DOWNLOAD ---
            if uspesni_fajlovi:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zf:
                    for name, content in uspesni_fajlovi.items():
                        zf.writestr(name, content)
                
                st.download_button(
                    label="📥 Preuzmi sve sondaže (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"Sondaze_{stanica_kod}_{godina}.zip",
                    mime="application/zip"
                )

        except Exception as e:
            st.error(f"Kritična greška: {e}")
        finally:
            if driver:
                driver.quit() [cite: 24]