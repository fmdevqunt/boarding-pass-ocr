import time
import re
import json
import codecs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ===================== CONFIGURATION =====================
AIRPORT_LIST_URL = "https://www.prioritypass.com/airport-lounges"
OUTPUT_FILE = "selected_countries_lounges.json"
HEADLESS = True                     # Set False to watch the browser
SELENIUM_DELAY = 2                  # seconds between actions
AIRPORT_DELAY = 5                    # seconds between airports
TARGET_COUNTRIES = ["United Kingdom", "United States Of America"]
# ==========================================================

# ----------------------------------------------------------------------
# PART 1: Extract airport list from the page (reliable Selenium method)
# ----------------------------------------------------------------------
def extract_airports_from_page(driver):
    """
    Use the already‑open driver to extract the airportsByRegions JSON.
    Returns a list of airport dictionaries with keys:
        country, airport_name, url, relative_path
    """
    print("🌐 Extracting airport list from page...")
    driver.get(AIRPORT_LIST_URL)
    time.sleep(5)

    # Wait for airport links to appear
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/lounges/']"))
        )
        print("✅ Airport links detected.")
    except TimeoutException:
        print("⚠️ No airport links found – proceeding anyway.")

    # Find the script containing 'airportsByRegions'
    scripts = driver.find_elements(By.TAG_NAME, "script")
    target_content = None
    for script in scripts:
        content = script.get_attribute("innerHTML")
        if content and "airportsByRegions" in content:
            target_content = content
            break

    if not target_content:
        print("❌ Could not find script with 'airportsByRegions'.")
        return []

    # Locate the key (with or without quotes)
    key_variants = ['"airportsByRegions"', 'airportsByRegions']
    key_pos = -1
    used_key = None
    for variant in key_variants:
        key_pos = target_content.find(variant)
        if key_pos != -1:
            used_key = variant
            break
    if key_pos == -1:
        print("❌ Could not find 'airportsByRegions' key.")
        return []

    # Find colon after key
    colon_pos = target_content.find(':', key_pos + len(used_key))
    if colon_pos == -1:
        print("❌ No colon after key.")
        return []

    # Find first '{' after colon (start of JSON object)
    start_pos = target_content.find('{', colon_pos)
    if start_pos == -1:
        print("❌ No opening brace after colon.")
        return []

    # Brace counting to find matching closing '}'
    stack = []
    end_pos = start_pos
    for i, char in enumerate(target_content[start_pos:], start=start_pos):
        if char == '{':
            stack.append('{')
        elif char == '}':
            if stack:
                stack.pop()
                if not stack:
                    end_pos = i
                    break
    if stack:
        print("❌ Could not find matching closing brace.")
        return []

    json_str = target_content[start_pos:end_pos+1]

    # Unescape the string (e.g., convert {\"Asia\":...} to {"Asia":...})
    try:
        json_str = codecs.decode(json_str, 'unicode_escape')
    except Exception:
        json_str = json_str.replace('\\"', '"')

    # Remove trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    # Parse JSON
    try:
        airports_by_regions = json.loads(json_str)
        print("✅ JSON parsed successfully.")
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return []

    # Build flat list of airports
    airports = []
    for region, region_data in airports_by_regions.items():
        if isinstance(region_data, dict) and 'items' in region_data:
            for item in region_data['items']:
                if 'url' in item and 'name' in item:
                    exact_path = item['url']
                    full_url = "https://www.prioritypass.com" + exact_path
                    path_parts = exact_path.split('/')
                    country = path_parts[2].replace('-', ' ').title() if len(path_parts) >= 3 else "Unknown"
                    airports.append({
                        'country': country,
                        'airport_name': item['name'],
                        'url': full_url,
                        'relative_path': exact_path
                    })

    print(f"✅ Extracted {len(airports)} airports.")
    return airports

# ----------------------------------------------------------------------
# PART 2: Lounge scraping functions (unchanged from previous working version)
# ----------------------------------------------------------------------
def scrape_airport(driver, airport_info):
    """Visit an airport page, extract airport details and all lounges."""
    url = airport_info['url']
    print(f"\n🛫 Processing: {airport_info['airport_name']} ({airport_info['country']})")
    print(f"   URL: {url}")

    result = {
        'country': airport_info['country'],
        'airport_name': airport_info['airport_name'],
        'url': url,
        'airport_code': None,
        'airport_location': None,
        'total_experiences': None,
        'lounges': []
    }

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)

        # Handle cookie popup (if any)
        try:
            accept_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'accept') or contains(text(), 'Agree')]"))
            )
            accept_button.click()
            time.sleep(SELENIUM_DELAY)
        except TimeoutException:
            pass

        # Extract airport info using data-testid
        try:
            result['airport_code'] = driver.find_element(By.CSS_SELECTOR, "[data-testid='airport-code']").text.strip()
        except NoSuchElementException:
            result['airport_code'] = "N/A"

        try:
            result['airport_name'] = driver.find_element(By.CSS_SELECTOR, "[data-testid='airport-name']").text.strip()
        except NoSuchElementException:
            pass

        try:
            result['airport_location'] = driver.find_element(By.CSS_SELECTOR, "[data-testid='airport-location']").text.strip()
        except NoSuchElementException:
            result['airport_location'] = "N/A"

        try:
            result['total_experiences'] = driver.find_element(By.CSS_SELECTOR, ".InfoSection_filter-terminals__YVaHm span.text-default").text.strip()
        except:
            result['total_experiences'] = "N/A"

        # Wait for lounge cards
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li a[href*='/lounges/']")))
        except TimeoutException:
            print("   ⚠️ No lounge cards found on this page.")
            return result

        # Collect all lounge basic info
        card_elements = driver.find_elements(By.CSS_SELECTOR, "li a[href*='/lounges/']")
        lounges_basic = []
        for card in card_elements:
            try:
                detail_url = card.get_attribute("href")
                lounge_id = detail_url.split('/')[-1].split('?')[0]
                name = card.find_element(By.CSS_SELECTOR, "h4").text.strip()

                try:
                    terminal = card.find_element(By.CSS_SELECTOR, "p[data-testid='outlet-card-terminal']").text.strip()
                except:
                    terminal = "N/A"

                try:
                    hours_elem = card.find_element(By.XPATH, ".//p[contains(text(),'Hours:')]")
                    opening_hours = hours_elem.text.replace("Hours:", "").strip()
                except:
                    opening_hours = "N/A"

                try:
                    img_elem = card.find_element(By.CSS_SELECTOR, "img")
                    image_url = img_elem.get_attribute("src") or ""
                except:
                    image_url = ""

                lounges_basic.append({
                    'lounge_id': lounge_id,
                    'name': name,
                    'terminal': terminal,
                    'opening_hours': opening_hours,
                    'image_url': image_url,
                    'detail_url': detail_url
                })
            except Exception as e:
                print(f"      ⚠️ Skipping a card: {e}")
                continue

        print(f"   Found {len(lounges_basic)} lounge cards.")

        # Process each detail page
        for idx, basic in enumerate(lounges_basic, 1):
            try:
                print(f"      Processing lounge {idx}: {basic['name']}...")
                detail_data = scrape_lounge_detail(driver, basic['detail_url'])
                full_lounge = {**basic, **detail_data}
                result['lounges'].append(full_lounge)
                print(f"      ✅ Lounge {idx} done.")
            except Exception as e:
                print(f"      ⚠️ Error on lounge {idx}: {e}")
                result['lounges'].append({**basic, 'amenities': 'N/A', 'access_notes': 'N/A', 'conditions': []})

    except Exception as e:
        print(f"   ❌ Error processing airport page: {e}")

    return result

def scrape_lounge_detail(driver, detail_url):
    """Visit lounge detail page and extract amenities, location, conditions."""
    driver.get(detail_url)
    time.sleep(SELENIUM_DELAY)

    amenities = []
    location_notes = []
    conditions_notes = []

    try:
        # Amenities
        amenity_blocks = driver.find_elements(By.XPATH, "//div[contains(@class, 'flex items-center justify-between') and contains(@class, 'py-[1rem]')]")
        for block in amenity_blocks:
            try:
                name_elem = block.find_element(By.CSS_SELECTOR, "span.pt-\\[3px\\].ml-\\[0\\.35rem\\].tracking-wide.whitespace-break-spaces")
                name = name_elem.text.strip()
                tags = [tag.text.strip() for tag in block.find_elements(By.CSS_SELECTOR, "span.FacilitiesRedesign_facility-details-tag__0JLtB")]
                if tags:
                    amenities.append(f"{name} ({', '.join(tags)})")
                else:
                    amenities.append(name)
            except NoSuchElementException:
                continue

        # Location section
        try:
            loc_button = driver.find_element(By.XPATH, "//h2[text()='Location']/ancestor::button")
            if loc_button.get_attribute("aria-expanded") == "false":
                driver.execute_script("arguments[0].click();", loc_button)
                time.sleep(1)
            loc_items = driver.find_elements(By.XPATH, "//h2[text()='Location']/ancestor::button/following-sibling::div//li")
            for item in loc_items:
                text = item.text.strip()
                if text:
                    location_notes.append(text)
        except NoSuchElementException:
            pass

        # Conditions section
        try:
            cond_button = driver.find_element(By.XPATH, "//h2[text()='Conditions']/ancestor::button")
            if cond_button.get_attribute("aria-expanded") == "false":
                driver.execute_script("arguments[0].click();", cond_button)
                time.sleep(1)
            cond_items = driver.find_elements(By.XPATH, "//h2[text()='Conditions']/ancestor::button/following-sibling::div//li")
            for item in cond_items:
                text = item.text.strip()
                if text:
                    conditions_notes.append(text)
        except NoSuchElementException:
            pass

        # Fallback
        if not location_notes:
            loc_list = driver.find_elements(By.XPATH, "//h2[text()='Location']/following::ul[1]//li")
            for item in loc_list:
                location_notes.append(item.text.strip())
        if not conditions_notes:
            cond_list = driver.find_elements(By.XPATH, "//h2[text()='Conditions']/following::ul[1]//li")
            for item in cond_list:
                conditions_notes.append(item.text.strip())

    except Exception as e:
        print(f"      ⚠️ Error on detail page: {e}")

    # Combine location and conditions into access_notes
    access_parts = []
    if location_notes:
        access_parts.append("Location:\n- " + "\n- ".join(location_notes))
    # if conditions_notes:
    #     access_parts.append("Conditions:\n- " + "\n- ".join(conditions_notes))
    access_notes = "\n\n".join(access_parts) if access_parts else "N/A"

    return {
        'amenities': "; ".join(amenities) if amenities else "N/A",
        'access_notes': access_notes,
        'conditions': conditions_notes
    }

# ----------------------------------------------------------------------
# MAIN: Extract, filter, scrape, and save
# ----------------------------------------------------------------------
def main():
    print("=" * 60)
    print("Priority Pass Scraper – Airport List + Lounge Details")
    print("=" * 60)

    # Set up Selenium driver (reused for both extraction and scraping)
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument('--headless')
    options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(options=options)

    all_data = []
    try:
        # Step 1: Get full airport list
        all_airports = extract_airports_from_page(driver)
        if not all_airports:
            print("❌ No airports extracted. Exiting.")
            return

        # Step 2: Filter for target countries (exact match, case‑insensitive)
        target_airports = []
        for apt in all_airports:
            if any(apt['country'].lower() == t.lower() for t in TARGET_COUNTRIES):
                target_airports.append(apt)

        print(f"\n🎯 Found {len(target_airports)} airports in selected countries.")
        if not target_airports:
            print("No matching airports. Exiting.")
            return

        # Step 3: Scrape each airport
        total = len(target_airports)
        for idx, airport in enumerate(target_airports, 1):
            print(f"\n--- Progress: {idx}/{total} ---")
            airport_result = scrape_airport(driver, airport)
            all_data.append(airport_result)

            # Save intermediate results every 5 airports
            if idx % 5 == 0:
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, indent=2, ensure_ascii=False)
                print(f"💾 Intermediate save: {idx} airports processed.")

            if idx < total:
                time.sleep(AIRPORT_DELAY)

        # Final save
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Scraping complete. Data saved to {OUTPUT_FILE}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()