import streamlit as st
import datetime
import zipfile
import requests
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

# --- KONFIGURACIJA ---
st.set_page_config(page_title="UWyo Downloader", page_icon="🌤️", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Podešavanja")
    stanica_kod = st.text_input("📍 KOD STANICE", value="13275")
    trenutna_godina = datetime.date.today().year
    godina = st.number_input("📅 GODINA", min_value=1900, max_value=trenutna_godina)
    vremena = st.multiselect("⏰ TERMINI (UTC)", ["00", "06", "12", "18"], default=["00", "12"])
    
    meseci_opcije = ["Januar", "Februar", "Mart", "April", "Maj", "Jun", 
                     "Jul", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar"]
    meseci_izbor = st.multiselect("🗓️ IZABERI MESECE", meseci_opcije, default=["Januar"])

st.title("🌪️ UWyo Sounding Data Downloader")

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    return webdriver.Chrome(service=service, options=options)

# --- GLAVNA AKCIJA ---
if st.button("🚀 POKRENI PREUZIMANJE"):
    if not meseci_izbor:
        st.error("Izaberite barem jedan mesec.")
    else:
        meseci_map = {m: i+1 for i, m in enumerate(meseci_opcije)}
        izabrani_brojevi = [meseci_map[m] for m in meseci_izbor]
        uspesni_fajlovi = {}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_expander = st.expander("Log operacija", expanded=True)

        driver = setup_driver()
        
        try:
            # Filtriranje datuma samo za izabrane mesece
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

            for datum in lista_datuma:
                for vreme in vremena:
                    count += 1
                    datum_str = datum.strftime('%Y-%m-%d')
                    izvor = "BUFR" if godina >= 2018 else "FM35"
                    
                    # URL do stranice koja sadrži link ka CSV-u
                    target_url = f"https://weather.uwyo.edu/wsgi/sounding?datetime={datum_str}%20{vreme}:00:00&id={stanica_kod}&type=TEXT%3ALIST&src={izvor}"
                    
                    try:
                        driver.get(target_url)
                        # Čekamo da se pojavi link, ali NE klikćemo na njega drajverom
                        link_element = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'type=TEXT:CSV')]"))
                        )
                        csv_url = link_element.get_attribute("href")
                        
                        # Čitamo sadržaj preko requests-a (ovo pretraživač ne vidi kao download)
                        r = requests.get(csv_url)
                        if r.status_code == 200 and len(r.text) > 100:
                            filename = f"{stanica_kod}_{datum.strftime('%Y%m%d')}_{vreme}UTC.csv"
                            uspesni_fajlovi[filename] = r.text
                            log_expander.write(f"✅ {filename}")
                    except:
                        log_expander.write(f"❌ {datum_str} {vreme}UTC - Nedostupno")
                    
                    progress_bar.progress(count / total_tasks)
                    status_text.text(f"Obrađeno: {count}/{total_tasks}")

            if uspesni_fajlovi:
                st.success(f"Sakupljeno {len(uspesni_fajlovi)} fajlova.")
                
                # Pakovanje u ZIP
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for name, content in uspesni_fajlovi.items():
                        zf.writestr(name, content)
                
                # JEDAN taster za download na kraju
                st.download_button(
                    label="📥 PREUZMI ZIP ARHIVU",
                    data=zip_buffer.getvalue(),
                    file_name=f"Sondaze_{stanica_kod}_{godina}.zip",
                    mime="application/zip"
                )
        finally:
            driver.quit()
