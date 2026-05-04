import asyncio
import os
import re
import time
import traceback
from urllib.parse import urlparse

import discord
import pyperclip
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LISHOGI_USERNAME = os.getenv("LISHOGI_USERNAME")
LISHOGI_PASSWORD = os.getenv("LISHOGI_PASSWORD")

KISHIN_URL_RE = re.compile(
    r"https?://kishin-analytics\.heroz\.jp/[^\s<>]+"
)


def is_kishin_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme in ("http", "https")
        and parsed.netloc == "kishin-analytics.heroz.jp"
    )


def extract_kishin_url(text: str) -> str | None:
    match = KISHIN_URL_RE.search(text)
    if not match:
        return None

    url = match.group(0).strip()
    url = url.rstrip(".,、。)）]］>")

    if not is_kishin_url(url):
        return None

    return url


def click_export_kifu_button(driver):
    """
    棋神アナリティクスの『棋譜を出力』ボタンをクリックする。
    """
    selector = r"div#tooltip\:_r_g_\:trigger > svg.chakra-icon:nth-of-type(1)"

    el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
    )

    print(f"棋譜を出力ボタンをCSSで発見: {selector}")

    ActionChains(driver).move_to_element(el).click().perform()
    time.sleep(1.0)


def click_copy_button(driver):
    """
    ダイアログ内の『コピー』ボタンをクリックする。
    """
    buttons = WebDriverWait(driver, 10).until(
        lambda d: d.find_elements(
            By.XPATH,
            "//*[self::button or @role='button'][normalize-space()='コピー']",
        )
    )

    print(f"完全一致の『コピー』ボタン数: {len(buttons)}")

    if not buttons:
        raise RuntimeError("『コピー』ボタンが見つかりませんでした。")

    target = buttons[-1]

    rect = driver.execute_script(
        """
        const r = arguments[0].getBoundingClientRect();

        return {
            x: Math.round(r.x),
            y: Math.round(r.y),
            width: Math.round(r.width),
            height: Math.round(r.height),
            text: arguments[0].innerText
        };
        """,
        target,
    )

    print("押すコピーボタン:")
    print(rect)

    ActionChains(driver).move_to_element(target).click().perform()
    time.sleep(1.0)


def get_kif_from_kishin(driver, url: str) -> str:
    """
    棋神アナリティクスURLを開き、KIFをクリップボードから取得する。
    """
    print("棋神アナリティクスのページを開いています...")
    driver.get(url)
    time.sleep(3.0)

    pyperclip.copy("")

    print("棋譜を出力ボタンをクリックします...")
    click_export_kifu_button(driver)

    print("KIFコピー按钮をクリックします...")
    click_copy_button(driver)

    copied = pyperclip.paste()

    print("クリップボード文字数:", len(copied))

    if not copied.strip():
        raise RuntimeError("クリップボードが空です。コピーに失敗しました。")

    return copied


def find_visible(driver, by: By, selector: str):
    elements = driver.find_elements(by, selector)
    for element in elements:
        if element.is_displayed() and element.is_enabled():
            return element
    return None


def find_first_visible_css(driver, selectors: list[str]):
    for selector in selectors:
        element = find_visible(driver, By.CSS_SELECTOR, selector)
        if element is not None:
            return element
    return None


def login_to_lishogi(driver) -> None:
    """
    lishogi にログインする。ログイン済みの場合は何もしない。
    """
    if not LISHOGI_USERNAME or not LISHOGI_PASSWORD:
        raise RuntimeError(".env に LISHOGI_USERNAME と LISHOGI_PASSWORD を設定してください。")

    print("lishogi login page を開いています...")
    driver.get("https://lishogi.org/login")

    wait = WebDriverWait(driver, 20)

    if "/login" not in urlparse(driver.current_url).path:
        print("lishogi はすでにログイン済みです。")
        return

    username_selectors = [
        "input[name='username']",
        "input[name='usernameOrEmail']",
        "input[autocomplete='username']",
        "input[type='text']",
        "input[type='email']",
    ]
    password_selectors = [
        "input[name='password']",
        "input[autocomplete='current-password']",
        "input[type='password']",
    ]

    username_input = wait.until(
        lambda d: find_first_visible_css(d, username_selectors)
    )
    password_input = wait.until(
        lambda d: find_first_visible_css(d, password_selectors)
    )

    username_input.clear()
    username_input.send_keys(LISHOGI_USERNAME)

    password_input.clear()
    password_input.send_keys(LISHOGI_PASSWORD)

    submit_button = wait.until(
        lambda d: find_visible(d, By.CSS_SELECTOR, "button[type='submit']")
    )

    before_path = urlparse(driver.current_url).path
    ActionChains(driver).move_to_element(submit_button).click().perform()

    print("lishogi のログイン完了を待っています...")

    def login_finished(d):
        current_path = urlparse(d.current_url).path
        visible_password = find_visible(d, By.CSS_SELECTOR, "input[type='password']")
        return current_path != before_path or visible_password is None

    wait.until(login_finished)

    if "/login" in urlparse(driver.current_url).path:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if "Authentication code" in body_text or "two-factor" in body_text.lower():
            raise RuntimeError("lishogi の二要素認証が必要です。自動ログインできませんでした。")
        raise RuntimeError("lishogi へのログインに失敗しました。ユーザー名またはパスワードを確認してください。")

    print("lishogi にログインしました。")


def import_kif_to_lishogi(driver, kif_text: str) -> str:
    """
    lishogi の Import game ページに KIF を貼り付け、
    インポート後のURLを返す。
    """
    login_to_lishogi(driver)

    print("lishogiのインポートページを開いています...")
    driver.get("https://lishogi.org/paste")

    wait = WebDriverWait(driver, 20)

    textarea = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea"))
    )

    print("KIFをlishogiに入力します...")

    # send_keys だと長いKIFで遅いので JavaScript で直接入れる
    driver.execute_script(
        """
        const textarea = arguments[0];
        const value = arguments[1];

        textarea.value = value;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        textarea.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        textarea,
        kif_text,
    )

    time.sleep(0.5)

    print("Import game ボタンをクリックします...")

    # lishogi が英語UI/日本語UIどちらでも動きやすいように複数候補
    button_xpaths = [
        "//button[@type='submit']",
        "//*[self::button or @role='button'][contains(normalize-space(), 'Import game')]",
        "//*[self::button or @role='button'][contains(normalize-space(), 'インポート')]",
        "//*[self::button or @role='button'][contains(normalize-space(), '入力')]",
    ]

    import_button = None

    for xp in button_xpaths:
        candidates = driver.find_elements(By.XPATH, xp)
        visible_candidates = [b for b in candidates if b.is_displayed() and b.is_enabled()]
        if visible_candidates:
            import_button = visible_candidates[-1]
            print(f"Importボタンを発見: {xp}")
            break

    if import_button is None:
        raise RuntimeError("lishogiのImport gameボタンが見つかりませんでした。")

    before_url = driver.current_url

    ActionChains(driver).move_to_element(import_button).click().perform()

    print("lishogiのURL生成を待っています...")

    wait.until(lambda d: d.current_url != before_url)

    time.sleep(1.0)

    lishogi_url = driver.current_url

    if "lishogi.org/paste" in lishogi_url:
        raise RuntimeError("lishogiへのインポート後URLに遷移しませんでした。")

    print("lishogi URL:", lishogi_url)

    return lishogi_url


def make_driver():
    options = Options()
    options.add_argument("--window-size=1280,900")
    options.add_argument("--window-position=0,0")

    # headless だと棋神側のクリップボードコピーが失敗しやすいので使わない
    # options.add_argument("--headless=new")

    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)
    return driver


def kishin_url_to_lishogi_url(url: str) -> str:
    """
    棋神URL → KIF取得 → lishogiインポート → lishogi URL返却
    """
    driver = make_driver()

    try:
        kif_text = get_kif_from_kishin(driver, url)
        lishogi_url = import_kif_to_lishogi(driver, kif_text)
        return lishogi_url

    finally:
        driver.quit()


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

selenium_lock = asyncio.Lock()


@client.event
async def on_ready():
    print(f"ログインしました: {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    url = extract_kishin_url(message.content)
    if not url:
        return

    async with selenium_lock:
        await message.channel.send("棋譜を取得して、lishogiに読み込ませています...")

        try:
            lishogi_url = await asyncio.to_thread(kishin_url_to_lishogi_url, url)

            await message.reply(
                content=f"lishogiに読み込みました。\n{lishogi_url}",
                mention_author=False,
            )

        except Exception as e:
            traceback.print_exc()

            await message.reply(
                f"lishogiへの読み込みに失敗しました。\n```text\n{e}\n```",
                mention_author=False,
            )


def main():
    if not DISCORD_TOKEN:
        raise RuntimeError(".env に DISCORD_TOKEN が設定されていません。")
    if not LISHOGI_USERNAME or not LISHOGI_PASSWORD:
        raise RuntimeError(".env に LISHOGI_USERNAME と LISHOGI_PASSWORD を設定してください。")

    client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
