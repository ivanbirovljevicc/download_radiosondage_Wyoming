# download_radiosondage_Wyoming
Preuzimanje radiosondaza sa Wyuoming univerziteta, zaobilazeci antibot i antiagent zastite.
# 🌤️ UWyo RadioSondage CSV Downloader (Selenium-Powered)

This Streamlit application provides an automated solution for batch-downloading meteorological sounding data from the University of Wyoming (UWyo) server.
It is specifically designed to handle the website's anti-bot protections while providing a user-friendly interface for data extraction in CSV format.

## 🛠️ Technical Features
* [cite_start]**Selenium Integration:** Emulates a real browser environment to successfully bypass the UWyo server's anti-bot mechanisms[cite: 3, 18].
* [cite_start]**Headless Operation:** Configured to run in the background (headless mode) on a Linux server environment[cite: 3, 18].
* [cite_start]**In-Memory Processing:** To ensure speed and security, data is stored in the server's RAM and packaged into a ZIP archive on-the-fly, rather than being saved to a permanent disk[cite: 17, 25].
* **Real-time RAM Monitor:** Features a live counter that displays the current data size (MB) in the server's memory.
* [cite_start]**Flexible Filtering:** Users can select specific years, months, and UTC sounding times (00, 06, 12, 18)[cite: 7, 8, 16].

## 📂 Project Structure
* `skripta.py`: The core Python script containing the Streamlit UI and Selenium scraping logic.
* `requirements.txt`: Specifies necessary Python libraries: `streamlit`, `selenium`, and `webdriver-manager`.
* `packages.txt`: Defines system-level dependencies (`chromium`, `chromium-driver`) required for the browser to function on Streamlit Cloud.

## 📖 How to Use
1.  [cite_start]**Station ID:** Enter the 5-digit station code (e.g., `13275` for Belgrade-kosutnjak)[cite: 6].
2.  [cite_start]**Date Selection:** Select the desired Year and one or more Months[cite: 7, 8].
3.  [cite_start]**UTC Times:** Choose the sounding intervals you need (00, 06, 12, or 18 UTC)[cite: 16].
4.  **Process:** Click **"Run Download"**.
5.  [cite_start]The bot will navigate to the CSV links and extract the data[cite: 11, 12].
6.  [cite_start]**Download:** Once the process is complete, a **"Download ZIP"** button will appear to save all files to your local machine[cite: 25].

## ⚠️ Stability Note
[cite_start]The script includes optimized delays between requests to ensure respectful scraping and to prevent IP blocking from the source server[cite: 13, 14].

📦 Installation & Usage Clone this repository. Install dependencies: pip install -r requirements.txt
Run the app: streamlit run skripta.py
