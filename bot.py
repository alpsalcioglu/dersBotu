from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, base64, requests, datetime, glob, os
import config

# ==========================
# Mailjet
# ==========================
MAILJET_API_KEY = "62ae372b1aae93e0953e208ced02632e"
MAILJET_SECRET_KEY = "2193f70c14fb7ffcbef74740c8d33492"
MAIL_FROM = "alpsalcioglu10@gmail.com"
MAIL_TO = "alpsalcioglu10@gmail.com"

def send_mail(subject, text, screenshot_path, pdf_path=None):
    atts = []
    with open(screenshot_path, "rb") as f:
        atts.append({
            "ContentType": "image/png",
            "Filename": os.path.basename(screenshot_path),
            "Base64Content": base64.b64encode(f.read()).decode("utf-8"),
        })
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            atts.append({
                "ContentType": "application/pdf",
                "Filename": os.path.basename(pdf_path),
                "Base64Content": base64.b64encode(f.read()).decode("utf-8"),
            })
    r = requests.post(
        "https://api.mailjet.com/v3.1/send",
        auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY),
        json={"Messages":[{"From":{"Email":MAIL_FROM,"Name":"Ders Bot"},
                           "To":[{"Email":MAIL_TO}],
                           "Subject":subject,"TextPart":text,"Attachments":atts}]}
    )
    print("Mail gönderildi:", r.status_code, r.text)

def clean_old_files(pattern):
    for f in glob.glob(pattern):
        try: os.remove(f); print("Silindi:", f)
        except: pass

# ==========================
# Selenium / Chrome
# ==========================
download_dir = os.path.abspath("./pdfs")
os.makedirs(download_dir, exist_ok=True)

options = webdriver.ChromeOptions()
options.add_experimental_option("prefs", {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True
})
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
    try:
        WebDriverWait(driver, 12).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        pass
    time.sleep(0.8)

def js_click(el):
    driver.execute_script("arguments[0].click();", el)

def try_login():
    """Login sayfası varsa giriş yapar."""
    try:
        u = driver.find_element(By.ID, "inputUsername")
        p = driver.find_element(By.ID, "inputPassword")
        b = driver.find_element(By.CLASS_NAME, "login_btn")
        u.clear(); p.clear()
        u.send_keys(config.USERNAME); p.send_keys(config.PASSWORD); js_click(b)
        print(">>> Login yapıldı.")
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(0.5)
    except NoSuchElementException:
        pass  # zaten login

def open_fe_modal():
    """Field Elective modalını aç ve tam yüklenmesini bekle."""
    fe = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "span.label.label-important"))
    )
    js_click(fe)
    print(">>> Field Elective SEÇ butonuna basıldı.")

    # Modalın gerçekten açılmasını bekle
    WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'modal') and contains(@class,'show')]"))
    )
    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.XPATH,
            "//div[contains(@class,'modal') and contains(@class,'show')]//table//tr"))
    )
    time.sleep(1)  #

def click_salman_in_modal():
    """Açık modaldaki SALMAN satırındaki 'Şubeyi Seç'e bas."""
    try:
        row = WebDriverWait(driver, 12).until(EC.presence_of_element_located((
            By.XPATH,
            "//div[contains(@class,'modal') and contains(@class,'show')]"
            "//tr[td[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜÂÎÛ', 'abcdefghijklmnopqrstuvwxyzçğiöşüâîû'), 'salman')]]"
        )))
        # 'Şubeyi Seç' / 'Seç' butonu
        try:
            btn = row.find_element(By.XPATH, ".//button[contains(translate(., 'ÇĞİÖŞÜÂÎÛAEIOU', 'çğiöşüâîûaeiou'),'seç')]")
        except NoSuchElementException:
            btn = row.find_element(By.CSS_SELECTOR, "button")
        js_click(btn)
        print(">>> Ayşe Salman şubesi seçildi, kontrol ediliyor...")
        time.sleep(0.5)
        return True
    except TimeoutException:
        print("⚠️ Ayşe Salman bulunamadı!")
        return False

def force_close_modal():
    """Şube Listesi modalını kapat (Kapat/X/ESC) ve kapanmasını bekle."""
    # 1) 'Kapat' butonu
    try:
        kapat = driver.find_element(By.XPATH,
            "//div[contains(@class,'modal') and contains(@class,'show')]//button[contains(.,'Kapat')]")
        js_click(kapat)
    except NoSuchElementException:
        # 2) sağ üst X
        try:
            close_x = driver.find_element(By.XPATH,
                "//div[contains(@class,'modal') and contains(@class,'show')]//button[contains(@class,'close')]")
            js_click(close_x)
        except NoSuchElementException:
            # 3) ESC fallback
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass
    # görünmez olana kadar bekle (olmazsa devamında hard refresh yapılır)
    try:
        WebDriverWait(driver, 5).until_not(
            EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'modal') and contains(@class,'show')]"))
        )
        print(">>> Modal kapandı.")
        # 🔑 DOM stabilize olsun
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)  # ekstra buffer
    except TimeoutException:
        print("❌ Modal kapanmadı (hard refresh).")
        hard_refresh()

def close_alert_and_modal_then_reset():
    """SweetAlert 'Tamam' → modalı kapat → hard refresh ile sıfırla."""
    # Tamam
    try:
        ok = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm.swal2-styled"))
        )
        js_click(ok)
        print(">>> Tamam butonuna basıldı.")
    except TimeoutException:
        print("❌ Tamam butonu bulunamadı!")

    # Alert kaybolsun
    try:
        WebDriverWait(driver, 4).until(
            EC.invisibility_of_element_located((By.ID, "swal2-content"))
        )
    except TimeoutException:
        pass

    # Şube Listesi modalını kapat
    force_close_modal()

    # En sonda temiz başlangıç
    hard_refresh()

def download_ders_programi_pdf(filename):
    ders_prog_btn = WebDriverWait(driver, 12).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.solbtn"))
    )
    js_click(ders_prog_btn)
    yazdir_btn = WebDriverWait(driver, 12).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-info"))
    )
    js_click(yazdir_btn)
    time.sleep(0.5)

    pdf = driver.execute_cdp_cmd("Page.printToPDF", {"format":"A4", "printBackground":True})
    path = os.path.join(download_dir, filename)
    with open(path, "wb") as f:
        f.write(base64.b64decode(pdf["data"]))
    print("✅ Ders Programı PDF kaydedildi:", path)
    return path

# ==========================
# Başlat
# ==========================
hard_refresh()
try_login()

last_mail_time = 0
while True:
    try:
        try_login()
        hard_refresh()

        # 1) Modalı aç
        open_fe_modal()

        # 2) SALMAN satırını tıkla; bulunamazsa başa dön (temizle)
        if not click_salman_in_modal():
            force_close_modal()
            hard_refresh()
            continue

        # 3) Kontenjan alert var mı?
        had_alert = False
        try:
            warn = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.ID, "swal2-content"))
            )
            if "Kontenjanı kalmadığı için" in warn.text:
                had_alert = True
        except TimeoutException:
            pass

        if had_alert:
            print("⚠️ Kontenjan yok!")

            now = time.time()
            if now - last_mail_time > 600:
                clean_old_files("kontenjan_yok_*.png")
                clean_old_files(os.path.join(download_dir, "ders_programi_*.pdf"))
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                png = f"kontenjan_yok_{ts}.png"
                driver.save_screenshot(png)
                pdf = download_ders_programi_pdf(f"ders_programi_{ts}.pdf")
                send_mail("Kontenjan Hâlâ Dolu",
                          "Kontenjan açılmadı, ders seçilemedi.",
                          png, pdf)
                last_mail_time = now

            close_alert_and_modal_then_reset()
            continue

        # 4) Uyarı yoksa → seçildi
        print("🎉 Ders başarıyla seçildi!")
        clean_old_files("ders_secilmis_*.png")
        clean_old_files(os.path.join(download_dir, "ders_programi_*.pdf"))

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        ok_png = f"ders_secilmis_{ts}.png"
        driver.save_screenshot(ok_png)
        ok_pdf = download_ders_programi_pdf(f"ders_programi_{ts}.pdf")
        send_mail("SEÇİLDİ BU İŞ TAMAMDIR KOÇUM!",
                  "Ders başarıyla seçildi! Artık uğraşma 🎉",
                  ok_png, ok_pdf)
        break

    except Exception as e:
        print(f"Hata oluştu: {e.__class__.__name__}: {e}")
        hard_refresh()
        time.sleep(1.5)
        continue