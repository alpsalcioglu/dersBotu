from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, base64, requests, datetime, glob, os
import config

# ==========================
# Mailjet ayarları
# ==========================
MAILJET_API_KEY = "62ae372b1aae93e0953e208ced02632e"
MAILJET_SECRET_KEY = "2193f70c14fb7ffcbef74740c8d33492"
MAIL_FROM = "alpsalcioglu10@gmail.com"
MAIL_TO = "alpsalcioglu10@gmail.com"

def send_mail(subject, text, screenshot_path, pdf_path=None):
    attachments = []

    with open(screenshot_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("utf-8")
    attachments.append({
        "ContentType": "image/png",
        "Filename": os.path.basename(screenshot_path),
        "Base64Content": file_data,
    })

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
        "Messages": [{
            "From": {"Email": MAIL_FROM, "Name": "Ders Bot"},
            "To": [{"Email": MAIL_TO}],
            "Subject": subject,
            "TextPart": text,
            "Attachments": attachments,
        }]
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

# ==========================
# Selenium / Chrome ayarları
# ==========================
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

# ==========================
# Yardımcılar
# ==========================
def hard_refresh():
    driver.get(config.URL)
    # sayfa readyState 'complete' olana kadar bekle
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        pass
    time.sleep(1.0)

def js_click(el):
    driver.execute_script("arguments[0].click();", el)

def try_login():
    """Login ekranı görünüyorsa giriş yapar; yoksa dokunmaz."""
    try:
        username_box = driver.find_element(By.ID, "inputUsername")
        password_box = driver.find_element(By.ID, "inputPassword")
        login_btn = driver.find_element(By.CLASS_NAME, "login_btn")
        username_box.clear(); password_box.clear()
        username_box.send_keys(config.USERNAME)
        password_box.send_keys(config.PASSWORD)
        js_click(login_btn)
        print(">>> Login yapıldı.")
        # login sonrası sayfa yüklenmesini bekle
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(1.0)
    except NoSuchElementException:
        # zaten loginliyiz
        pass

def open_fe_modal():
    """Field Elective modalını güvenle aç ve görünür olmasını bekle."""
    fe_btn = WebDriverWait(driver, 12).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "span.label.label-important"))
    )
    js_click(fe_btn)
    print(">>> Field Elective SEÇ butonuna basıldı.")

    # modal görünür olsun
    WebDriverWait(driver, 12).until(
        EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'modal') and contains(@class,'show')]"))
    )
    # tablo satırları yüklenene kadar bekle (Ajax olabilir)
    WebDriverWait(driver, 12).until(
        EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class,'modal') and contains(@class,'show')]//table//tr"))
    )
    time.sleep(0.5)

def click_salman_in_modal():
    """
    Açık modaldaki tabloda 'salman' içeren satırın 'Şubeyi Seç' butonuna tıklar.
    Döner: True (başarılı) / False (bulunamadı)
    """
    try:
        # Türkçe harfler için case-insensitive eşleştirme: translate ile küçült
        salman_row = WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//div[contains(@class,'modal') and contains(@class,'show')]"
                "//tr[td[contains(translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜÂÎÛ', 'abcdefghijklmnopqrstuvwxyzçğiöşüâîû'), 'salman')]]"
            ))
        )
        try:
            # Buton metnine göre deneyelim (Şubeyi Seç / Seç)
            select_btn = salman_row.find_element(By.XPATH, ".//button[contains(translate(., 'ÇĞİÖŞÜÂÎÛAEIOU', 'çğiöşüâîûaeiou'),'seç')]")
        except NoSuchElementException:
            select_btn = salman_row.find_element(By.CSS_SELECTOR, "button")

        js_click(select_btn)
        print(">>> Ayşe Salman şubesi seçildi, kontrol ediliyor...")
        time.sleep(0.8)
        return True

    except TimeoutException:
        print("⚠️ Ayşe Salman bulunamadı!")
        return False

def close_swal_and_modal_then_refresh():
    """Kontenjan uyarısı geldiğinde: Tamam → modal kapanana kadar bekle → hard refresh."""
    # Önce Tamam’a bas
    try:
        ok_btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm.swal2-styled"))
        )
        js_click(ok_btn)
        print(">>> Tamam butonuna basıldı.")
    except TimeoutException:
        print("❌ Tamam butonu bulunamadı veya tıklanamadı!")

    # SweetAlert kapanmasını bekle (ihtiyari)
    try:
        WebDriverWait(driver, 6).until(
            EC.invisibility_of_element_located((By.ID, "swal2-content"))
        )
    except TimeoutException:
        pass

    # Modal kapanmasını bekle
    try:
        WebDriverWait(driver, 8).until_not(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'modal') and contains(@class,'show')]"))
        )
        print(">>> Modal kapandı.")
    except TimeoutException:
        print("❌ Modal kapanmadı (zorlama hard refresh).")

    # Hard refresh
    hard_refresh()

def download_ders_programi_pdf(filename):
    """Ders Programı → Yazdır → CDP ile PDF al."""
    ders_prog_btn = WebDriverWait(driver, 12).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.solbtn"))
    )
    js_click(ders_prog_btn)

    yazdir_btn = WebDriverWait(driver, 12).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-info"))
    )
    js_click(yazdir_btn)
    time.sleep(0.8)

    pdf = driver.execute_cdp_cmd("Page.printToPDF", {"format": "A4", "printBackground": True})
    pdf_path = os.path.join(download_dir, filename)
    with open(pdf_path, "wb") as f:
        f.write(base64.b64decode(pdf['data']))

    print(f"✅ Ders Programı PDF kaydedildi: {pdf_path}")
    return pdf_path

# ==========================
# Başlat
# ==========================
hard_refresh()
try_login()

last_mail_time = 0
while True:
    try:
        try_login()          # logout olduysa yakala
        hard_refresh()       # her tur saf başlangıç

        # 1) Modalı aç ve tabloyu gerçekten yüklet
        open_fe_modal()

        # 2) Ayşe Salman satırını bul ve tıkla (yoksa başa)
        if not click_salman_in_modal():
            # modal açık kaldıysa kapansın diye ESC veya refresh tercih edilebilir;
            # en sağlamı hard refresh:
            hard_refresh()
            continue

        # 3) Kontenjan uyarısı kontrolü
        uyarı_var = False
        try:
            warning = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.ID, "swal2-content"))
            )
            if "Kontenjanı kalmadığı için" in warning.text:
                uyarı_var = True
        except TimeoutException:
            pass

        if uyarı_var:
            print("⚠️ Kontenjan yok!")

            # 10 dk kuralı
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

            close_swal_and_modal_then_refresh()
            continue

        # 4) Eğer uyarı yoksa ders seçildi demektir
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

    except Exception as e:
        print(f"Hata oluştu: {e.__class__.__name__}: {e}")
        hard_refresh()
        time.sleep(2)
        continue