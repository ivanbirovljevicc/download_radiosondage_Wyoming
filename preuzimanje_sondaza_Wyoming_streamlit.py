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

# --- KONFIGURACIJA STRANICE ---
st.set_page_config(page_title="UWyo Arhiver", page_icon="🌤️", layout="wide")

# --- SIDEBAR PODEŠAVANJA ---
with st.sidebar:
    st.header("⚙️ Podešavanja")
    
    stanica_kod = st.text_input("📍 KOD STANICE", value="13275")
    
    # Dinamička maksimalna godina (trenutna godina u kojoj se nalazimo)
    trenutna_godina = datetime.date.today().year
    godina = st.number_input("📅 GODINA", min_value=1900, max_value=trenutna_godina)
    
    vremena = st.multiselect("⏰ TERMINI (UTC)", ["00", "06", "12", "18"], default=["00", "12"])
    
    meseci_opcije = ["Januar", "Februar", "Mart", "April", "Maj", "Jun", 
                     "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"]
    meseci_izbor = st.multiselect("🗓️ IZABERI MESECE", meseci_opcije, default=["Januar"])
    
    st.info("💡 Skripta automatski bira BUFR (2018+) ili FM35 (pre 2018) format.")

# --- GLAVNI DEO EKRANA ---
st.title("🌪️ UWyo Sounding Data Downloader")
st.write(f"Spreman za preuzimanje podataka za stanicu **{stanica_kod}** za **{godina}**. godinu.")

# --- FUNKCIJA ZA PODEŠAVANJE SELENIUMA ---
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-allow-origins=*")
    
    # ChromeDriverManager automatski rešava verziju na Streamlit Cloudu
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- LOGIKA PREUZIMANJA ---
if st.button("🚀 POKRENI PROCES PREUZIMANJA"):
    if not meseci_izbor:
        st.error("Morate izabrati barem jedan mesec!")
    else:
        # Mapiranje meseci
        meseci_map = {m: i+1 for i, m in enumerate(meseci_opcije)}
        izabrani_brojevi = [meseci_map[m] for m in meseci_izbor]
        
        uspesni_fajlovi = {}
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_expander = st.expander("Log operacija", expanded=True)

        driver = setup_driver()
        
        try:
            # Generisanje datuma
            lista_datuma = []
            curr = datetime.date(godina, 1, 1)
            kraj = datetime.date(godina, 12, 31)
            danas = datetime.date.today()

            while curr <= kraj:
                # Provera meseca i da ne idemo u budućnost
                if curr.month in izabrani_brojevi and curr <= danas:
                    lista_datuma.append(curr)
                curr += datetime.timedelta(days=1)

            total_tasks = len(lista_datuma) * len(vremena)
            if total_tasks == 0:
                st.warning("Nema datuma za obradu (proverite da niste izabrali mesec u budućnosti).")
            else:
                count = 0
                for datum in lista_datuma:
                    for vreme in vremena:
                        count += 1
                        datum_str = datum.strftime('%Y-%m-%d')
                        
                        # Određivanje izvora na osnovu godine
                        izvor = "BUFR" if godina >= 2018 else "FM35"
                        
                        target_url = (f"https://weather.uwyo.edu/wsgi/sounding?"
                                     f"datetime={datum_str}%20{vreme}:00:00&id={stanica_kod}&type=TEXT%3ALIST&src={izvor}")
                        
                        try:
                            driver.get(target_url)
                            # Čekamo link za CSV
                            csv_link = WebDriverWait(driver, 7).until(
                                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'type=TEXT:CSV')]"))
                            )
                            driver.get(csv_link.get_attribute("href"))
                            
                            # Skidamo RAW sadržaj
                            content = driver.find_element(By.TAG_NAME, "pre").text
                            
                            if len(content) > 100:
                                filename = f"{stanica_kod}_{datum.strftime('%Y%m%d')}_{vreme}UTC.csv"
                                uspesni_fajlovi[filename] = content
                                log_expander.write(f"✅ {filename} preuzet (Izvor: {izvor})")
                        except Exception:
                            log_expander.write(f"❌ {datum_str} {vreme}UTC - Nije pronađeno")
                        
                        # Osvežavanje progresa
                        progress_bar.progress(count / total_tasks)
                        status_text.text(f"Status: {count}/{total_tasks} | Trenutno obrađujem: {datum_str}")

               if uspesni_fajlovi:
                    st.success(f"🏁 Završeno! Preuzeto {len(uspesni_fajlovi)} fajlova.")
                    
                    # Kreiranje ZIP arhive u memoriji
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        for name, content in uspesni_fajlovi.items():
                            zf.writestr(name, content)
                    
                    # Fix: Koristimo ključ (key) da Streamlit ne bi pobrkao tastere pri osvežavanju
                    st.download_button(
                        label="📥 PREUZMI SVE KAO ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=f"Sondaze_{stanica_kod}_{godina}.zip",
                        mime="application/zip",
                        key="download-zip-btn"
                    )
                    
                    # VAŽNO: Isključujemo automatsko osvežavanje koje bi moglo pokrenuti dupli download
                    st.balloons()
                    
                   
                else:
                    st.error("Nijedan podatak nije pronađen.")
        
        except Exception as e:
            st.error(f"Došlo je do greške: {e}")
        finally:
            driver.quit()


