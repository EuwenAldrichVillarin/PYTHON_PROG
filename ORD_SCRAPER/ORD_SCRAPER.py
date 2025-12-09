

import time
import argparse
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def scrape_all_datasets(headless: bool = False, timeout: int = 30) -> None:
    base_url = "https://open-reaction-database.org"
    datasets = {}
    
    # Initialize data collection structure
    scraped_data = []  # List to store all extracted data rows
    csv_filename = "scraped_data.csv"
    csv_columns = ['dataset_id', 'section', 'tab', 'data_type', 'value', 'index']
    
    # Initialize CSV file with header
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
        print(f"✓ CSV file initialized: {csv_filename}\n")
    except Exception as e:
        print(f"✗ Error initializing CSV file: {e}\n")
    
    options = Options()
    if headless:
        # Selenium 4.8+ supports the new headless flag, but fallback works too
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Install driver via webdriver-manager and start Chrome
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        # Maximize the browser window
        driver.maximize_window()
        
        driver.get(base_url)

        wait = WebDriverWait(driver, timeout)

        # Look for an <a> element whose text is exactly 'Browse' (top navigation)
        browse = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Browse']"))
        )
        print("Found 'Browse' element; clicking it...")
        browse.click()

        # Wait for the URL to change from the landing page
        wait.until(lambda d: d.current_url != base_url)
        print("Navigation successful; current URL:", driver.current_url)
        
        # Wait for the browse page to fully load
        time.sleep(0.5)
        
        # Wait for dataset links to be present
        print("Waiting for dataset IDs to load...")
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'ord_dataset-')]"))
        )
        
        # Count the total number of dataset IDs present
        dataset_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ord_dataset-')]")
        total_dataset_ids = len(dataset_links)
        print(f"Found {total_dataset_ids} total dataset IDs on the browse page.")
        
        # Get all dataset URLs
        print("Collecting all dataset URLs...")
        dataset_urls = []
        for link in dataset_links:
            dataset_urls.append(link.get_attribute("href"))
        
        # Helper function to save data incrementally to CSV
        def save_to_csv(data_to_save):
            """Append data rows to CSV file."""
            try:
                with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                    writer.writerows(data_to_save)
            except Exception as e:
                print(f"✗ Error saving to CSV: {e}")
        
        # Define process_dataset function (will process Inputs/Outcomes inside a modal)
        def process_dataset(dataset_number: int, dataset_id: str = None):
            """Process Inputs and Outcomes for a single dataset and collect data."""
            print(f"\n{'='*60}")
            print(f"Processing Dataset #{dataset_number}")
            print(f"{'='*60}")
            
            # Look for and click "Inputs" in the navbar
            print("Looking for 'Inputs' navbar item...")
            try:
                inputs_nav = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@class='nav-item' and contains(text(), 'inputs')]"))
                )
                print("Found 'Inputs' navbar item, clicking it...")
                inputs_nav.click()
                
                # Wait for the inputs section to load
                time.sleep(0.5)
                print("Inputs section loaded.")
                
                # Find all tabs within the inputs section (id="inputs")
                tabs = driver.find_elements(By.XPATH, "//div[@id='inputs']//div[@class='tabs']//div[contains(@class, 'tab')]")
                total_tabs = len(tabs)
                print(f"Found {total_tabs} tabs in inputs section")
                
                # Process each tab
                for tab_idx in range(total_tabs):
                    tab_num = tab_idx + 1
                    tab_text = None  # Initialize tab_text
                    
                    # For tabs after the first, click the tab
                    if tab_idx > 0:
                        # Re-fetch tabs to avoid stale element
                        tabs = driver.find_elements(By.XPATH, "//div[@id='inputs']//div[@class='tabs']//div[contains(@class, 'tab')]")
                        tab = tabs[tab_idx]
                        tab_text = tab.text.strip()
                        
                        print(f"\nClicking tab {tab_num}/{total_tabs}: {tab_text}")
                        driver.execute_script("arguments[0].scrollIntoView(true);", tab)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", tab)
                        time.sleep(0.5)
                    else:
                        # Get the text of the first tab too
                        tabs = driver.find_elements(By.XPATH, "//div[@id='inputs']//div[@class='tabs']//div[contains(@class, 'tab')]")
                        if tabs:
                            tab_text = tabs[0].text.strip()
                        print(f"\nProcessing tab {tab_num}/{total_tabs} (already selected): {tab_text}")
                        time.sleep(0.5)
                    
                    # Find all <> buttons under the "input" div
                    code_buttons = driver.find_elements(By.XPATH, "//div[@class='input']//div[@class='button' and contains(text(), '<>')]")
                    print(f"Found {len(code_buttons)} '<>' buttons in tab {tab_num}")
                    
                    # Click each <> button
                    for btn_idx in range(len(code_buttons)):
                        try:
                            # Re-fetch buttons to avoid stale element
                            code_buttons = driver.find_elements(By.XPATH, "//div[@class='input']//div[@class='button' and contains(text(), '<>')]")
                            button = code_buttons[btn_idx]
                            
                            print(f"  Clicking '<>' button {btn_idx + 1}/{len(code_buttons)} in tab {tab_num}...")
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", button)
                            
                            # Wait 0.5 seconds
                            time.sleep(0.5)
                            
                            # Extract data from the modal
                            try:
                                # Check if modal contains identifiers
                                pre_elements = driver.find_elements(By.XPATH, "//pre")
                                has_identifiers = False
                                type_value = None
                                identifier_value = None
                                
                                if pre_elements:
                                    pre_text = pre_elements[0].text
                                    has_identifiers = 'identifiers' in pre_text
                                    
                                    if has_identifiers:
                                        # Extract all identifier values
                                        try:
                                            identifier_values = []
                                            search_start = 0
                                            while True:
                                                value_pos = pre_text.find('"value":', search_start)
                                                if value_pos == -1:
                                                    break
                                                value_start = value_pos + len('"value":')
                                                value_part = pre_text[value_start:].strip()
                                                if value_part.startswith('"'):
                                                    value_end = value_part.find('"', 1)
                                                    if value_end > 0:
                                                        identifier_values.append(value_part[1:value_end])
                                                search_start = value_start + 1
                                            
                                            # Print all identifier values with numbering if more than one
                                            if len(identifier_values) > 1:
                                                for idx, val in enumerate(identifier_values, 1):
                                                    print(f"    Identifier value {idx}: {val}")
                                                    save_to_csv([{
                                                        'dataset_id': dataset_id,
                                                        'section': 'Inputs',
                                                        'tab': tab_text,
                                                        'data_type': 'identifier',
                                                        'value': val,
                                                        'index': idx
                                                    }])
                                            elif len(identifier_values) == 1:
                                                print(f"    Identifier value: {identifier_values[0]}")
                                                save_to_csv([{
                                                    'dataset_id': dataset_id,
                                                    'section': 'Inputs',
                                                    'tab': tab_text,
                                                    'data_type': 'identifier',
                                                    'value': identifier_values[0],
                                                    'index': 1
                                                }])
                                        except Exception as e:
                                            print(f"    Could not extract identifier value: {e}")
                                    else:
                                        # Extract type and value when no identifiers
                                        try:
                                            if '"type":' in pre_text:
                                                type_start = pre_text.find('"type":') + len('"type":')
                                                type_part = pre_text[type_start:].strip()
                                                if type_part.startswith('"'):
                                                    type_end = type_part.find('"', 1)
                                                    if type_end > 0:
                                                        type_value = type_part[1:type_end]
                                                        print(f"    Type: {type_value}")
                                                        save_to_csv([{
                                                            'dataset_id': dataset_id,
                                                            'section': 'Inputs',
                                                            'tab': tab_text,
                                                            'data_type': 'type',
                                                            'value': type_value,
                                                            'index': 1
                                                        }])
                                        except Exception as e:
                                            print(f"    Could not extract type: {e}")
                                        
                                        try:
                                            if '"value":' in pre_text:
                                                value_start = pre_text.find('"value":') + len('"value":')
                                                value_part = pre_text[value_start:].strip()
                                                # Check if value is a number or string
                                                if value_part.startswith('"'):
                                                    value_end = value_part.find('"', 1)
                                                    if value_end > 0:
                                                        identifier_value = value_part[1:value_end]
                                                else:
                                                    # Handle numeric values
                                                    value_end = value_part.find(',')
                                                    if value_end == -1:
                                                        value_end = value_part.find('}')
                                                    if value_end > 0:
                                                        identifier_value = value_part[:value_end].strip()
                                                    else:
                                                        identifier_value = value_part.split()[0].strip()
                                                print(f"    Value: {identifier_value}")
                                                save_to_csv([{
                                                    'dataset_id': dataset_id,
                                                    'section': 'Inputs',
                                                    'tab': tab_text,
                                                    'data_type': 'value',
                                                    'value': identifier_value,
                                                    'index': 1
                                                }])
                                        except Exception as e:
                                            print(f"    Could not extract value: {e}")
                                
                                # Find the reaction_role from <pre> tag
                                reaction_role = None
                                try:
                                    pre_elements = driver.find_elements(By.XPATH, "//pre[contains(text(), 'reaction_role')]")
                                    if pre_elements:
                                        pre_text = pre_elements[0].text
                                        # Extract reaction_role value
                                        if 'reaction_role:' in pre_text:
                                            role_start = pre_text.find('reaction_role:') + len('reaction_role:')
                                            role_part = pre_text[role_start:].strip()
                                            # Get the role value (before newline or end)
                                            reaction_role = role_part.split()[0].strip()
                                            print(f"    Reaction role: {reaction_role}")
                                            save_to_csv([{
                                                'dataset_id': dataset_id,
                                                'section': 'Inputs',
                                                'tab': tab_text,
                                                'data_type': 'reaction_role',
                                                'value': reaction_role,
                                                'index': 1
                                            }])
                                except Exception as e:
                                    print(f"    Could not extract reaction_role: {e}")
                            except Exception as e:
                                print(f"    Error extracting data: {e}")
                            
                            # Look for and click the close button
                            try:
                                close_button = wait.until(
                                    EC.element_to_be_clickable((By.XPATH, "//div[@class='close']"))
                                )
                                print(f"  Closing modal...")
                                close_button.click()
                                time.sleep(0.5)
                            except Exception as e:
                                print(f"  Could not find or click close button: {e}")
                            
                        except Exception as e:
                            print(f"  Could not click '<>' button {btn_idx + 1}: {e}")
                    
                    print(f"Completed tab {tab_num}")
                
                print("\nAll tabs processed.")
                
            except Exception as e:
                print(f"Could not find or click 'Inputs' navbar item: {e}")
            
            # Look for and click "Outcomes" in the navbar
            print("\nLooking for 'Outcomes' navbar item...")
            try:
                outcomes_nav = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@class='nav-item' and contains(text(), 'outcomes')]"))
                )
                print("Found 'Outcomes' navbar item, clicking it...")
                outcomes_nav.click()
                
                # Wait for the outcomes section to load
                time.sleep(0.5)
                print("Outcomes section loaded.")
                
                # Find all Product tabs within the sub-section under Products title
                product_tabs = driver.find_elements(By.XPATH, "//div[@class='title' and contains(text(), 'Products')]/following-sibling::div[@class='sub-section']//div[@class='tabs']//div[contains(@class, 'tab')]")
                total_product_tabs = len(product_tabs)
                print(f"Found {total_product_tabs} Product tab(s)")
                
                # Process each Product tab
                for tab_idx in range(total_product_tabs):
                    tab_num = tab_idx + 1
                    tab_text = None  # Initialize tab_text
                    
                    # For tabs after the first, click the tab
                    if tab_idx > 0:
                        # Re-fetch tabs to avoid stale element
                        product_tabs = driver.find_elements(By.XPATH, "//div[@class='title' and contains(text(), 'Products')]/following-sibling::div[@class='sub-section']//div[@class='tabs']//div[contains(@class, 'tab')]")
                        tab = product_tabs[tab_idx]
                        tab_text = tab.text.strip()
                        
                        print(f"\nClicking Product tab {tab_num}/{total_product_tabs}: {tab_text}")
                        driver.execute_script("arguments[0].scrollIntoView(true);", tab)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", tab)
                        time.sleep(0.5)
                    else:
                        # Get the text of the first tab too
                        product_tabs = driver.find_elements(By.XPATH, "//div[@class='title' and contains(text(), 'Products')]/following-sibling::div[@class='sub-section']//div[@class='tabs']//div[contains(@class, 'tab')]")
                        if product_tabs:
                            tab_text = product_tabs[0].text.strip()
                        print(f"\nProcessing Product tab {tab_num}/{total_product_tabs} (already selected): {tab_text}")
                        time.sleep(0.5)
                    
                    # Find all <> buttons in the currently active Product tab
                    code_buttons = driver.find_elements(By.XPATH, "//div[@class='title' and contains(text(), 'Products')]/following-sibling::div[@class='sub-section']//div[@class='button' and contains(text(), '<>')]")
                    print(f"Found {len(code_buttons)} '<>' button(s) in Product tab {tab_num}")
                    
                    # Click each <> button in this Product tab
                    for btn_idx in range(len(code_buttons)):
                        try:
                            # Re-fetch buttons to avoid stale element
                            code_buttons = driver.find_elements(By.XPATH, "//div[@class='title' and contains(text(), 'Products')]/following-sibling::div[@class='sub-section']//div[@class='button' and contains(text(), '<>')]")
                            button = code_buttons[btn_idx]
                            
                            print(f"  Clicking '<>' button {btn_idx + 1}/{len(code_buttons)} in Product tab {tab_num}...")
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", button)
                            
                            # Wait 0.5 seconds
                            time.sleep(0.5)
                            
                            # Extract data from the modal
                            try:
                                # Check if modal contains identifiers
                                pre_elements = driver.find_elements(By.XPATH, "//pre")
                                has_identifiers = False
                                type_value = None
                                identifier_value = None
                                
                                if pre_elements:
                                    pre_text = pre_elements[0].text
                                    has_identifiers = 'identifiers' in pre_text
                                    
                                    if has_identifiers:
                                        # Extract all identifier values
                                        try:
                                            identifier_values = []
                                            search_start = 0
                                            while True:
                                                value_pos = pre_text.find('"value":', search_start)
                                                if value_pos == -1:
                                                    break
                                                value_start = value_pos + len('"value":')
                                                value_part = pre_text[value_start:].strip()
                                                if value_part.startswith('"'):
                                                    value_end = value_part.find('"', 1)
                                                    if value_end > 0:
                                                        identifier_values.append(value_part[1:value_end])
                                                search_start = value_start + 1
                                            
                                            # Print all identifier values with numbering if more than one
                                            if len(identifier_values) > 1:
                                                for idx, val in enumerate(identifier_values, 1):
                                                    print(f"    Identifier value {idx}: {val}")
                                                    save_to_csv([{
                                                        'dataset_id': dataset_id,
                                                        'section': 'Outcomes',
                                                        'tab': tab_text,
                                                        'data_type': 'identifier',
                                                        'value': val,
                                                        'index': idx
                                                    }])
                                            elif len(identifier_values) == 1:
                                                print(f"    Identifier value: {identifier_values[0]}")
                                                save_to_csv([{
                                                    'dataset_id': dataset_id,
                                                    'section': 'Outcomes',
                                                    'tab': tab_text,
                                                    'data_type': 'identifier',
                                                    'value': identifier_values[0],
                                                    'index': 1
                                                }])
                                        except Exception as e:
                                            print(f"    Could not extract identifier value: {e}")
                                    else:
                                        # Extract type and value when no identifiers
                                        try:
                                            if '"type":' in pre_text:
                                                type_start = pre_text.find('"type":') + len('"type":')
                                                type_part = pre_text[type_start:].strip()
                                                if type_part.startswith('"'):
                                                    type_end = type_part.find('"', 1)
                                                    if type_end > 0:
                                                        type_value = type_part[1:type_end]
                                                        print(f"    Type: {type_value}")
                                                        save_to_csv([{
                                                            'dataset_id': dataset_id,
                                                            'section': 'Outcomes',
                                                            'tab': tab_text,
                                                            'data_type': 'type',
                                                            'value': type_value,
                                                            'index': 1
                                                        }])
                                        except Exception as e:
                                            print(f"    Could not extract type: {e}")
                                        
                                        try:
                                            if '"value":' in pre_text:
                                                value_start = pre_text.find('"value":') + len('"value":')
                                                value_part = pre_text[value_start:].strip()
                                                # Check if value is a number or string
                                                if value_part.startswith('"'):
                                                    value_end = value_part.find('"', 1)
                                                    if value_end > 0:
                                                        identifier_value = value_part[1:value_end]
                                                else:
                                                    # Handle numeric values
                                                    value_end = value_part.find(',')
                                                    if value_end == -1:
                                                        value_end = value_part.find('}')
                                                    if value_end > 0:
                                                        identifier_value = value_part[:value_end].strip()
                                                    else:
                                                        identifier_value = value_part.split()[0].strip()
                                                print(f"    Value: {identifier_value}")
                                                save_to_csv([{
                                                    'dataset_id': dataset_id,
                                                    'section': 'Outcomes',
                                                    'tab': tab_text,
                                                    'data_type': 'value',
                                                    'value': identifier_value,
                                                    'index': 1
                                                }])
                                        except Exception as e:
                                            print(f"    Could not extract value: {e}")
                                
                                # Find the reaction_role from <pre> tag
                                reaction_role = None
                                try:
                                    pre_elements = driver.find_elements(By.XPATH, "//pre[contains(text(), 'reaction_role')]")
                                    if pre_elements:
                                        pre_text = pre_elements[0].text
                                        # Extract reaction_role value
                                        if 'reaction_role:' in pre_text:
                                            role_start = pre_text.find('reaction_role:') + len('reaction_role:')
                                            role_part = pre_text[role_start:].strip()
                                            # Get the role value (before newline or end)
                                            reaction_role = role_part.split()[0].strip()
                                            print(f"    Reaction role: {reaction_role}")
                                            save_to_csv([{
                                                'dataset_id': dataset_id,
                                                'section': 'Outcomes',
                                                'tab': tab_text,
                                                'data_type': 'reaction_role',
                                                'value': reaction_role,
                                                'index': 1
                                            }])
                                except Exception as e:
                                    print(f"    Could not extract reaction_role: {e}")
                            except Exception as e:
                                print(f"    Error extracting data: {e}")
                            
                            # Look for and click the close button
                            try:
                                close_button = wait.until(
                                    EC.element_to_be_clickable((By.XPATH, "//div[@class='close']"))
                                )
                                print(f"  Closing modal...")
                                close_button.click()
                                time.sleep(1)
                            except Exception as e:
                                print(f"  Could not find or click close button: {e}")
                            
                        except Exception as e:
                            print(f"  Could not click '<>' button {btn_idx + 1}: {e}")
                    
                    print(f"Completed Product tab {tab_num}")
                
                print("\nAll Product tabs processed.")
                
            except Exception as e:
                print(f"Could not find or click 'Outcomes' navbar item: {e}")
            
            print(f"\n{'='*60}")
            print(f"Finished Processing Dataset #{dataset_number}")
            print(f"{'='*60}\n")
        
        # ============ MAIN LOOP: Process each dataset ============
        for dataset_idx, dataset_url in enumerate(dataset_urls, 1):
            print(f"\n{'='*80}")
            print(f"Processing Dataset {dataset_idx} of {total_dataset_ids}")
            print(f"{'='*80}")
            
            # Extract dataset ID from URL
            dataset_id = dataset_url.split('/')[-1] if '/' in dataset_url else dataset_url
            print(f"Dataset ID: {dataset_id}")
            
            # Open the dataset in a new tab
            print("Opening dataset in a new tab...")
            driver.execute_script(f"window.open('{dataset_url}');")
            time.sleep(0.5)
            
            # Switch to the new tab (this will be the dataset tab)
            dataset_tab = driver.window_handles[-1]
            driver.switch_to.window(dataset_tab)
            time.sleep(0.5)
            
            # Wait for the dataset page to fully load by checking for specific elements
            print("Waiting for dataset page to fully load...")
            
            # Wait for URL to change to the dataset page
            wait.until(lambda d: "ord_dataset-" in d.current_url)
            
            # Wait for page body to be present
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Wait for document ready state
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Additional wait for any dynamic content to load
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'ord_dataset-') or contains(@class, 'dataset')]")))
            
            print(f"Dataset page fully loaded: {driver.current_url}")
            
            # Scroll to the very bottom of the page to load all content
            print("\nScrolling to the very bottom of the page...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            print("Reached the very bottom of the page.")
            
            # Change pagination to 100 entries per page
            print("\nLooking for pagination select dropdown...")
            try:
                # Wait for the select element to be present
                select_element = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//select[@name='pagination']"))
                )
                print("Found pagination select dropdown, selecting value 100...")
                
                # Use Select class to interact with the dropdown
                select = Select(select_element)
                select.select_by_value("100")
                
                time.sleep(0.5)
                print("Selected 100 entries per page.")
            except Exception as e:
                print(f"Could not select pagination option: {e}")
            
            # Scroll back to the top of the page
            print("\nScrolling back to the top of the page...")
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            
            # Wait for View Full Details buttons to be present
            print("\nWaiting for 'View Full Details' buttons to load...")
            try:
                wait.until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(@data-v, '') and text()='View Full Details']"))
                )
                print("View Full Details buttons are now present.")
            except Exception as e:
                print(f"Timeout waiting for View Full Details buttons: {e}")
            
            # Find all View Full Details buttons on the dataset page
            print("Looking for all 'View Full Details' buttons...")
            view_details_buttons = driver.find_elements(By.XPATH, "//button[contains(@data-v, '') and text()='View Full Details']")
            total_buttons = len(view_details_buttons)
            print(f"Found {total_buttons} total 'View Full Details' button(s)")
            
            # Process all View Full Details buttons on the current page
            try:
                total_buttons_processed = 0
                
                print(f"\n{'='*80}")
                print(f"Processing All View Full Details Buttons for Dataset {dataset_idx}")
                print(f"{'='*80}")
                
                if total_buttons == 0:
                    print("No buttons found.")
                else:
                    print(f"Starting to process {total_buttons} buttons...")
                    # Process each button
                    for button_idx in range(total_buttons):
                        total_buttons_processed += 1
                        button_num = total_buttons_processed
                        print(f"\n[Button {button_idx + 1}/{total_buttons}] Processing button...")
                        
                        # Re-fetch buttons to avoid stale element
                        view_details_buttons = driver.find_elements(By.XPATH, "//button[contains(@data-v, '') and text()='View Full Details']")
                        
                        if button_idx < len(view_details_buttons):
                            button = view_details_buttons[button_idx]
                            
                            print(f"Opening 'View Full Details' button in new tab...")
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(0.5)
                            
                            # Get the button's parent link or onclick URL
                            button_url = None
                            try:
                                # Try to find a parent link
                                parent_link = button.find_element(By.XPATH, "./ancestor::a")
                                button_url = parent_link.get_attribute("href")
                            except:
                                pass
                            
                            if not button_url:
                                try:
                                    # Try to get onclick attribute
                                    onclick = button.get_attribute("onclick")
                                    if onclick:
                                        print(f"Found onclick: {onclick}")
                                except:
                                    pass
                            
                            # If we found a URL, open it in a new tab
                            if button_url:
                                print(f"Opening URL in new tab: {button_url}")
                                driver.execute_script(f"window.open('{button_url}');")
                                time.sleep(0.5)
                                
                                # Switch to the new tab
                                driver.switch_to.window(driver.window_handles[-1])
                                time.sleep(0.5)
                                
                                # Process this modal's Inputs and Outcomes data
                                process_dataset(button_num, dataset_id)
                                
                                # Close the tab and switch back to the dataset window
                                print("Closing modal tab and returning to dataset page...")
                                driver.close()
                                driver.switch_to.window(dataset_tab)
                                time.sleep(0.5)
                            else:
                                print("Could not find URL for button, skipping...")
                
                print(f"\n{'='*80}")
                print(f"Completed processing {total_buttons_processed} buttons for dataset {dataset_idx}.")
                print(f"{'='*80}")
                
                # Save collected data to CSV after this dataset is processed
                if scraped_data:
                    print(f"\n✓ Saving {len(scraped_data)} rows to CSV...")
                    save_to_csv(scraped_data)
                    scraped_data.clear()  # Clear for next dataset
                    print(f"✓ Data saved to {csv_filename}")
                
            except Exception as e:
                print(f"Error processing View Full Details buttons: {e}")
            
            # Close the dataset tab and return to the main window
            print("\nClosing dataset tab and returning to browse page...")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(0.5)
        
        print(f"\n{'='*80}")
        print(f"Completed processing all {total_dataset_ids} datasets.")
        print(f"✓ All data has been saved to {csv_filename}")
        print(f"{'='*80}")
        
        print("Press Ctrl+C to exit.")
        
        while True:
            time.sleep(0.5)
        
    finally:
        driver.quit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Selenium scraper to visit all dataset IDs on open-reaction-database.org"
    )
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode")
    args = parser.parse_args()

    scrape_all_datasets(headless=args.headless)


if __name__ == "__main__":
    main()

