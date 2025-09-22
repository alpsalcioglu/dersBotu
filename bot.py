from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, base64, requests, datetime, glob, os
import config

# --- Mailjet ayarları ---
MAILJET_API_KEY = "62ae372b1aae93e0953e208ced02632e"
MAILJET_SECRET_KEY = "2193f70c14fb7ffcbef74740c8d33492"
MAIL_FROM = "alpsalcioglu10@gmail.com"
MAIL_TO = "alpsalcioglu10@gmail.com"

def send_mail(subject, text, screenshot_path, pdf_path=None):
    attachments = []

    # PNG ekle
    with open(screenshot_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("utf-8")
    attachments.append({
        "ContentType": "image/png",
        "Filename": os.path.basename(screenshot_path),
        "Base64Content": file_data,
    })

    # PDF ekle (varsa)
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode("utf-8")
        attachments.append({
            "ContentType": "application/pdf",
            "Filename": os.path.basename(pdf_path),
            "Base64Content": pdf_data,
        })

    url = "https://api.mailjet.com/v3.1/send"
    payload = {
        "Messages": [
            {
                "From": {"Email": MAIL_FROM, "Name": "Ders Bot"},
                "To": [{"Email": MAIL_TO}],
                "Subject": subject,
                "TextPart": text,
                "Attachments": attachments,
            }
        ]
    }

    r = requests.post(url, auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), json=payload)
    print("Mail gönderildi:", r.status_code, r.text)

def clean_old_files(pattern):
    for f in glob.glob(pattern):
        try:
            os.remove(f)
            print(f"Silindi: {f}")
        except:
            pass

# --- Selenium ayarları ---
download_dir = os.path.abspath("./pdfs")
os.makedirs(download_dir, exist_ok=True)

options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True
}
options.add_experimental_option("prefs", prefs)
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service("/snap/bin/chromium.chromedriver")
driver = webdriver.Chrome(service=service, options=options)

driver.get(config.URL)
driver.maximize_window()

# --- Login fonksiyonu ---
def try_login():
    try:
        username_box = driver.find_element(By.ID, "inputUsername")
        password_box = driver.find_element(By.ID, "inputPassword")
        login_btn = driver.find_element(By.CLASS_NAME, "login_btn")

        username_box.send_keys(config.USERNAME)
        password_box.send_keys(config.PASSWORD)
        login_btn.click()
        print(">>> Login yapıldı.")
        time.sleep(5)
    except NoSuchElementException:
        pass

# Ders Programı PDF indirme fonksiyonu (CDP ile direkt PDF)
def download_ders_programi_pdf(filename):
    ders_prog_btn = driver.find_element(By.CSS_SELECTOR, "button.solbtn")
    driver.execute_script("arguments[0].click();", ders_prog_btn)
    time.sleep(2)

    yazdir_btn = driver.find_element(By.CSS_SELECTOR, "button.btn.btn-info")
    driver.execute_script("arguments[0].click();", yazdir_btn)
    time.sleep(2)

    pdf = driver.execute_cdp_cmd("Page.printToPDF", {
        "format": "A4",
        "printBackground": True
    })

    pdf_path = os.path.join(download_dir, filename)
    with open(pdf_path, "wb") as f:
        f.write(base64.b64decode(pdf['data']))

    print(f"✅ Ders Programı PDF kaydedildi: {pdf_path}")
    return pdf_path

# İlk giriş denemesi
try_login()

# --- Döngü ---
last_mail_time = 0
while True:
    try:
        try_login()

        # 1) Field Elective -> SEÇ butonuna tıkla (modal açılır)
        field_button = driver.find_element(By.CSS_SELECTOR, "span.label.label-important")
        driver.execute_script("arguments[0].click();", field_button)
        print(">>> Field Elective SEÇ butonuna basıldı.")
        time.sleep(2)

        # 2) Ayşe Salman satırını bul ve şubeyi seç
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        clicked = False
        for row in rows:
            row_text = row.text.lower()
            if "salman" in row_text:   # soyadına göre kontrol
                select_button = row.find_element(By.CSS_SELECTOR, "button")
                driver.execute_script("arguments[0].click();", select_button)
                print(">>> Ayşe Salman şubesi seçildi, kontrol ediliyor...")
                clicked = True
                time.sleep(2)
                break

        if not clicked:
            print("⚠️ Ayşe Salman bulunamadı, fallback ile btnuzunluk tıklanıyor...")
            try:
                section_button = driver.find_element(By.ID, "btnuzunluk")
                driver.execute_script("arguments[0].click();", section_button)
                time.sleep(2)
            except:
                print("❌ Fallback butonu da bulunamadı!")

        # 3) Kontenjan uyarısını kontrol et
        try:
            warning = driver.find_element(By.ID, "swal2-content")
            if "Kontenjanı kalmadığı için" in warning.text:
                print("⚠️ Kontenjan yok!")

                try:
                    ok_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm.swal2-styled"))
                    )
                    ok_btn.click()
                except:
                    ok_btn = driver.find_element(By.CSS_SELECTOR, "button.swal2-confirm.swal2-styled")
                    driver.execute_script("arguments[0].click();", ok_btn)

                now = time.time()
                if now - last_mail_time > 600:  
                    clean_old_files("kontenjan_yok_*.png")

                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot = f"kontenjan_yok_{timestamp}.png"
                    driver.save_screenshot(screenshot)

                    pdf_file = download_ders_programi_pdf(f"ders_programi_{timestamp}.pdf")

                    send_mail("Kontenjan Hâlâ Dolu",
                              "Kontenjan açılmadı, ders seçilemedi.",
                              screenshot,
                              pdf_file)
                    last_mail_time = now

                driver.refresh()
                time.sleep(3)
                continue

        except NoSuchElementException:
            # Uyarı yok → ders seçildi
            print("🎉 Ders başarıyla seçildi!")

            clean_old_files("ders_secilmis_*.png")

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot = f"ders_secilmis_{timestamp}.png"
            driver.save_screenshot(screenshot)

            pdf_file = download_ders_programi_pdf(f"ders_programi_{timestamp}.pdf")

            send_mail("SEÇİLDİ BU İŞ TAMAMDIR KOÇUM!",
                      "Ders başarıyla seçildi! Artık uğraşma 🎉",
                      screenshot,
                      pdf_file)
            break

    except Exception as e:
        print(f"Hata oluştu: {e}")
        driver.refresh()
        time.sleep(5)
        continue