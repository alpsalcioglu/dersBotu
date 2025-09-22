from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
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
        driver.execute_script("arguments[0].click();", login_btn)
        print(">>> Login yapıldı.")
        WebDriverWait(driver, 10).until_not(
            EC.presence_of_element_located((By.ID, "inputUsername"))
        )
        time.sleep(2)
    except NoSuchElementException:
        pass

# --- Yardımcı: Field Elective modalını güvenli aç ---
def open_fe_modal():
    fe_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "span.label.label-important"))
    )
    driver.execute_script("arguments[0].click();", fe_btn)
    print(">>> Field Elective SEÇ butonuna basıldı.")
    # Açık modalı bekle
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.XPATH,
            "//div[contains(@class,'modal') and (contains(@class,'show') or contains(@style,'display: block'))]"
        ))
    )

# --- Yardımcı: Açık modalda 'Ayşe SALMAN' satırının 'Şubeyi Seç' butonuna bas ---
def click_salman_in_modal() -> bool:
    try:
        # Türkçe harfler için case-insensitive eşleştirme
        button = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class,'modal') and (contains(@class,'show') or contains(@style,'display: block'))]"
            "//tr[td[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ', 'abcdefghijklmnopqrstuvwxyzçğiöşü'), 'salman')]]"
            "//button"
        )))
        driver.execute_script("arguments[0].click();", button)
        print(">>> Ayşe Salman şubesi seçildi, kontrol ediliyor...")
        time.sleep(1.5)
        return True
    except Exception as e:
        print("⚠️ Ayşe Salman bulunamadı (", type(e).__name__, ")")
        return False

# --- Ders Programı PDF indirme (CDP ile direkt PDF) ---
def download_ders_programi_pdf(filename):
    ders_prog_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.solbtn"))
    )
    driver.execute_script("arguments[0].click();", ders_prog_btn)

    yazdir_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-info"))
    )
    driver.execute_script("arguments[0].click();", yazdir_btn)
    time.sleep(1)

    pdf = driver.execute_cdp_cmd("Page.printToPDF", {"format": "A4", "printBackground": True})
    pdf_path = os.path.join(download_dir, filename)
    with open(pdf_path, "wb") as f:
        f.write(base64.b64decode(pdf['data']))
    print(f"✅ Ders Programı PDF kaydedildi: {pdf_path}")
    return pdf_path

# İlk giriş
try_login()

# --- Ana Döngü ---
last_mail_time = 0
while True:
    try:
        try_login()

        # 1) Modalı aç
        open_fe_modal()

        # 2) Ayşe Salman satırındaki butona bas; olmazsa fallback
        clicked = click_salman_in_modal()
        if not clicked:
            try:
                fb = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "btnuzunluk"))
                )
                driver.execute_script("arguments[0].click();", fb)
                time.sleep(1.5)
            except Exception:
                print("❌ Fallback 'btnuzunluk' da bulunamadı!")

        # 3) Kontenjan uyarısı varsa işle
        try:
            warning = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.ID, "swal2-content"))
            )
            if "Kontenjanı kalmadığı için" in warning.text:
                print("⚠️ Kontenjan yok!")
                try:
                    ok_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm.swal2-styled"))
                    )
                    driver.execute_script("arguments[0].click();", ok_btn)
                except Exception:
                    try:
                        ok_btn = driver.find_element(By.CSS_SELECTOR, "button.swal2-confirm.swal2-styled")
                        driver.execute_script("arguments[0].click();", ok_btn)
                    except Exception:
                        pass

                now = time.time()
                if now - last_mail_time > 600:
                    clean_old_files("kontenjan_yok_*.png")
                    clean_old_files(os.path.join(download_dir, "ders_programi_*.pdf"))

                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot = f"kontenjan_yok_{ts}.png"
                    driver.save_screenshot(screenshot)
                    pdf_file = download_ders_programi_pdf(f"ders_programi_{ts}.pdf")
                    send_mail("Kontenjan Hâlâ Dolu",
                              "Kontenjan açılmadı, ders seçilemedi.",
                              screenshot,
                              pdf_file)
                    last_mail_time = now

                driver.refresh()
                time.sleep(2.5)
                continue
        except Exception:
            # Uyarı elementi bulunmadıysa ders seçilmiş olabilir
            print("🎉 Ders başarıyla seçildi!")
            clean_old_files("ders_secilmis_*.png")
            clean_old_files(os.path.join(download_dir, "ders_programi_*.pdf"))

            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot = f"ders_secilmis_{ts}.png"
            driver.save_screenshot(screenshot)
            pdf_file = download_ders_programi_pdf(f"ders_programi_{ts}.pdf")
            send_mail("SEÇİLDİ BU İŞ TAMAMDIR KOÇUM!",
                      "Ders başarıyla seçildi! Artık uğraşma 🎉",
                      screenshot,
                      pdf_file)
            break

    except StaleElementReferenceException:
        # DOM yenilendiyse başa sar
        print("↻ DOM yenilendi, tekrar deniyorum...")
        driver.refresh()
        time.sleep(2)
        continue
    except Exception as e:
        print(f"Hata oluştu: {e.__class__.__name__}: {e}")
        driver.refresh()
        time.sleep(3)
        continue