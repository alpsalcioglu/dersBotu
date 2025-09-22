from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, base64, requests, datetime, glob, os
import config

# --- Mailjet ayarları ---
MAILJET_API_KEY = "62ae372b1aae93e0953e208ced02632e"
MAILJET_SECRET_KEY = "2193f70c14fb7ffcbef74740c8d33492"
MAIL_FROM = "alpsalcioglu10@gmail.com"   # Gönderen mail
MAIL_TO = "alpsalcioglu10@gmail.com"     # Alıcı mail

def send_mail(subject, text, screenshot_path):
    """Mailjet ile mail gönder (ekran görüntüsü ekli)."""
    with open(screenshot_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("utf-8")
    filename = screenshot_path.split("/")[-1]

    url = "https://api.mailjet.com/v3.1/send"
    payload = {
        "Messages":[
            {
                "From": {
                    "Email": MAIL_FROM,
                    "Name": "Ders Bot"
                },
                "To": [
                    {
                        "Email": MAIL_TO
                    }
                ],
                "Subject": subject,
                "TextPart": text,
                "Attachments": [
                    {
                        "ContentType": "image/png",
                        "Filename": filename,
                        "Base64Content": file_data
                    }
                ]
            }
        ]
    }

    r = requests.post(url, auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), json=payload)
    print("Mail gönderildi:", r.status_code, r.text)


def clean_old_screenshots(pattern):
    """Belirli tipteki eski ekran görüntülerini siler."""
    for f in glob.glob(pattern):
        try:
            os.remove(f)
            print(f"Silindi: {f}")
        except:
            pass


# --- Selenium ayarları ---
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # tarayıcı açmadan
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(executable_path="/snap/bin/chromium.chromedriver", options=options)
driver.get(config.URL)
driver.maximize_window()

# Login gerekiyorsa sadece o zaman yap
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
    print(">>> Zaten login olunmuş, devam ediliyor.")


# --- Döngü ---
last_mail_time = 0
while True:
    try:
        # 1) Field Elective -> SEÇ butonuna tıkla
        field_button = driver.find_element(By.CSS_SELECTOR, "span.label.label-important")
        field_button.click()
        print(">>> Field Elective SEÇ butonuna basıldı.")
        time.sleep(1)

        # 2) Ayşe Salman şubesi -> Şubeyi Seç
        section_button = driver.find_element(By.ID, "btnuzunluk")
        section_button.click()
        print(">>> Ayşe Salman şubesi seçildi, kontrol ediliyor...")
        time.sleep(2)

        # 3) Kontenjan uyarısını kontrol et
        try:
            warning = driver.find_element(By.ID, "swal2-content")
            if "Kontenjanı kalmadığı için" in warning.text:
                print("⚠️ Kontenjan yok!")

                # "Tamam" butonuna bas (önce normal click, olmazsa JS click)
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
                    # Eski "kontenjan_yok" dosyalarını sil
                    clean_old_screenshots("kontenjan_yok_*.png")

                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot = f"kontenjan_yok_{timestamp}.png"
                    driver.save_screenshot(screenshot)
                    send_mail("Kontenjan Hâlâ Dolu",
                              "Kontenjan açılmadı, ders seçilemedi.",
                              screenshot)
                    last_mail_time = now

                driver.refresh()
                time.sleep(3)
                continue

        except NoSuchElementException:
            # Uyarı bulunamadı → ders seçilmiş
            print("🎉 Ders başarıyla seçildi!")

            # Eski "ders_secilmis" dosyalarını sil
            clean_old_screenshots("ders_secilmis_*.png")

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot = f"ders_secilmis_{timestamp}.png"
            driver.save_screenshot(screenshot)
            send_mail("SEÇİLDİ BU İŞ TAMAMDIR KOÇUM!",
                      "Ders başarıyla seçildi! Artık uğraşma 🎉",
                      screenshot)
            break

    except Exception as e:
        print(f"Hata oluştu: {e}")
        driver.refresh()
        time.sleep(5)
        continue