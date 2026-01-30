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
    # Dodatne opcije za stabilnost na Cloud serverima
    options.add_argument("--disable-gpu")
    options.add_argument("--blink-settings=imagesEnabled=false") # Ne učitava slike, štedi RAM
    
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- INTERFEJS ---
st.set_page_config(page_title="UWyo Downloader", page_icon="🌤️", layout="wide")

with st.sidebar:
    st.header("⚙️ Konfiguracija")
    stanica_kod = st.text_input("📍 KOD STANICE", value="13275")
    
    trenutna_godina = datetime.date.today().year
    godina = st.number_input("📅 GODINA", min_value=1900, max_value=trenutna_godina)
    
    vremena = st.multiselect("⏰ TERMINI (UTC)", ["00", "06", "12", "18"], default=["00", "12"])
    
    meseci_opcije = ["Januar", "Februar", "Mart", "April", "Maj", "Jun", "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"]
    meseci_izbor = st.multiselect("🗓️ IZABERI MESECE", meseci_opcije, default=["Januar"])

st.title("🌪️ UWyo Sounding Data Downloader")

if st.button("🚀 POKRENI PREUZIMANJE"):
    if not meseci_izbor:
        st.error("Izaberi barem jedan mesec!")
    else:
        meseci_map = {m: i+1 for i, m in enumerate(meseci_opcije)}
        izabrani_brojevi = [meseci_map[m] for m in meseci_izbor]
        
        uspesni_fajlovi = {}
        ukupna_velicina_bajtova = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        mem_info = st.empty() # Tvoja metrika za RAM
        log_expander = st.expander("Log preuzimanja", expanded=True)

        driver = setup_driver()
        
        try:
            # Lista datuma
            lista_datuma = []
            danas = datetime.date.today()
            for m in izabrani_brojevi:
                for d in range(1, 32):
                    try:
                        datum = datetime.date(godina, m, d)
                        if datum <= danas:
                            lista_datuma.append(datum)
                    except ValueError:
                        continue
            
            lista_datuma.sort()
            total_tasks = len(lista_datuma) * len(vremena)
            count = 0
            restart_counter = 0 # Brojač za RAM osigurač

            for datum in lista_datuma:
                for vreme in vremena:
                    count += 1
                    restart_counter += 1
                    
                    # --- OSIGURAČ ZA RAM (Restart drajvera na svakih 40 zahteva) ---
                    if restart_counter >= 40:
                        driver.quit()
                        driver = setup_driver()
                        restart_counter = 0
                        log_expander.write("🔄 *Sistem: Restartujem drajver radi oslobađanja RAM-a...*")

                    datum_str = datum.strftime('%Y-%m-%d')
                    izvor = "BUFR" if godina >= 2018 else "FM35"
                    target_url = f"https://weather.uwyo.edu/wsgi/sounding?datetime={datum_str}%20{vreme}:00:00&id={stanica_kod}&type=TEXT%3ALIST&src={izvor}"
                    
                    try:
                        driver.get(target_url)
                        csv_link = WebDriverWait(driver, 7).until(
                            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'type=TEXT:CSV')]"))
                        )
                        driver.get(csv_link.get_attribute("href"))
                        
                        sadrzaj = driver.find_element(By.TAG_NAME, "pre").text
                        
                        if len(sadrzaj) > 100:
                            filename = f"{stanica_kod}_{datum.strftime('%Y%m%d')}_{vreme}UTC.csv"
                            uspesni_fajlovi[filename] = sadrzaj
                            
                            # Tvoja metrika za RAM
                            ukupna_velicina_bajtova += sys.getsizeof(sadrzaj)
                            mb_size = ukupna_velicina_bajtova / (1024 * 1024)
                            mem_info.metric("Zauzeće RAM-a (podaci)", f"{mb_size:.2f} MB")
                            
                            log_expander.write(f"✅ {filename}")
                    except:
                        log_expander.write(f"❌ {datum_str} {vreme}UTC - Nema podataka")
                    
                    progress_bar.progress(count / total_tasks)
                    status_text.text(f"Obrađeno: {count}/{total_tasks} | Trenutno: {datum_str}")

            if uspesni_fajlovi:
                st.success(f"🏁 Završeno! Sakupljeno {len(uspesni_fajlovi)} fajlova.")
                
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for name, content in uspesni_fajlovi.items():
                        zf.writestr(name, content)
                
                st.download_button(
                    label="📥 PREUZMI ZIP ARHIVU",
                    data=zip_buffer.getvalue(),
                    file_name=f"Sondaze_{stanica_kod}_{godina}.zip",
                    mime="application/zip",
                    key="zip_dl_btn"
                )
        finally:
            driver.quit()
