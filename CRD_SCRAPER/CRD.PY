from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time

# Create CSV file for scraped data
scraped_data_file = open("scraped_smiles_data.csv", "w", newline="", encoding="utf-8")
scraped_writer = csv.writer(scraped_data_file, quoting=csv.QUOTE_ALL)
scraped_writer.writerow(["Reaction URL", "Product Page", "SMILES #", "Data"])

# Setup Chrome driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.maximize_window()

try:
    url = "https://kmt.vander-lingen.nl/archive"
    driver.get(url)
    time.sleep(2)

    # Get all reaction data links
    links = driver.find_elements(By.LINK_TEXT, "reaction data")
    reaction_urls = [link.get_attribute("href") for link in links]

    # Filter out None or empty URLs
    reaction_urls = [url for url in reaction_urls if url]

    print(f"Found {len(reaction_urls)} reaction data links\n")

    # Save the links to CSV for reference
    with open("reaction_links.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Index", "URL"])
        for index, link in enumerate(reaction_urls, 1):
            writer.writerow([index, link])
    
    print(f"Saved all links to reaction_links.csv\n")

    # ============= MAIN LOOP: Visit Each Reaction Data Link =============
    for index, link in enumerate(reaction_urls, 1):
        print(f"\n{'='*70}")
        print(f"REACTION DATA [{index}/{len(reaction_urls)}]")
        print(f"{'='*70}")
        print(f"URL: {link}")
        
        # Navigate to the reaction data page
        driver.get(link)
        time.sleep(3)
        
        # ============= PRODUCT PAGE LOOP =============
        product_page = 1
        while True:
            print(f"\n  Product Page {product_page}")
            print(f"  Current URL: {driver.current_url}")
            
            # Get Results badge count
            try:
                results_badge = driver.find_element(By.CSS_SELECTOR, "button.btn-info .badge")
                total_results = int(results_badge.text.strip())
                print(f"     Results: {total_results}")
            except:
                total_results = 0
                print(f"     Could not find Results badge - quitting product pages")
                break
            
            # If Results is 0, quit and go back
            if total_results == 0:
                print(f"     Results = 0, moving to next reaction data")
                break
            
            # ============= SMILES BUTTON LOOP =============
            smiles_clicked = 0
            
            while True:
                # Find all SMILES buttons on current page
                smiles_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    "button.btn.btn-outline-success.btn-sm[data-reaction-smiles]")
                
                if not smiles_buttons:
                    print(f"       No SMILES buttons found on this page")
                    break
                
                print(f"       Found {len(smiles_buttons)} SMILES buttons on this page")
                
                # Click each SMILES button
                for btn_index, btn in enumerate(smiles_buttons, 1):
                    try:
                        print(f"          → Clicking SMILES button {smiles_clicked + 1}/{total_results}")
                        btn.click()
                        time.sleep(3)  # Stay for 3 seconds
                        
                        # ============= SCRAPE MODAL DATA =============
                        try:
                            # Get the SMILES data from the data attribute
                            smiles_data = btn.get_attribute("data-reaction-smiles")
                            
                            modal_title = ""
                            modal_text = ""
                            
                            # Parse the SMILES data - format is typically: reactants>reagents>products
                            # The > symbol separates: reactants > reagents/solvents > products
                            if smiles_data:
                                parts = smiles_data.split(">")
                                
                                reactants = parts[0].strip() if len(parts) > 0 else ""
                                solvent_reagents = parts[1].strip() if len(parts) > 1 else ""
                                product = parts[2].strip() if len(parts) > 2 else ""
                                
                                print(f"             REACTANTS: {reactants}")
                                print(f"             SOLVENT/REAGENTS: {solvent_reagents}")
                                print(f"             PRODUCT: {product}")
                            
                            # Try to read modal content
                            try:
                                modal_body = driver.find_element(By.CSS_SELECTOR, ".modal-body")
                                modal_text = modal_body.text.strip()
                                print(f"             Modal Content: {modal_text}")
                            except:
                                pass
                            
                            # Try to get modal title
                            try:
                                modal_title = driver.find_element(By.CSS_SELECTOR, ".modal-title")
                                modal_title = modal_title.text.strip()
                                print(f"             Title: {modal_title}")
                            except:
                                pass
                            
                            # Write to CSV with formatted labels and new lines
                            formatted_data = f"""REACTION URL: {link}

SMILES #{smiles_clicked}

REACTANTS:
{reactants}

SOLVENT/REAGENTS:
{solvent_reagents}

PRODUCT:
{product}

MODAL TITLE:
{modal_title}

MODAL CONTENT:
{modal_text}

{'='*70}"""
                            
                            scraped_writer.writerow([
                                link,
                                product_page,
                                smiles_clicked,
                                formatted_data
                            ])
                            scraped_data_file.flush()
                            
                        except Exception as scrape_error:
                            print(f"             Error scraping data: {scrape_error}")
                        
                        # Close the modal
                        try:
                            close_btn = driver.find_element(By.CSS_SELECTOR, ".modal .close")
                            close_btn.click()
                        except:
                            try:
                                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            except:
                                pass
                        
                        time.sleep(0.5)
                        smiles_clicked += 1
                        
                    except Exception as e:
                        print(f"          Error clicking button: {e}")
                
                # Check if clicked SMILES equals total Results
                if smiles_clicked >= total_results:
                    print(f"       Clicked {smiles_clicked}/{total_results} - All SMILES on this product done!")
                    break
                
                # Check if there's a "Next" pagination button for SMILES
                try:
                    next_btn = driver.find_element(By.LINK_TEXT, "Next")
                    print(f"       Clicking 'Next' for more SMILES...")
                    next_btn.click()
                    time.sleep(2)
                except:
                    print(f"       No more SMILES pages, but not all clicked yet")
                    break
            
            print(f"     Total SMILES clicked on product page: {smiles_clicked}")
            
            # Scroll to bottom to find the Next product button
            print(f"  Scrolling to bottom of page...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # After all SMILES are clicked, try to click the Next product button
            try:
                # Find ALL anchor tags with class "btn btn-primary"
                next_buttons = driver.find_elements(By.CSS_SELECTOR, "a.btn.btn-primary")
                
                print(f"  Found {len(next_buttons)} buttons with class 'btn btn-primary'")
                
                next_btn = None
                for btn in next_buttons:
                    btn_text = btn.text.strip()
                    btn_href = btn.get_attribute("href")
                    print(f"      Button: {btn_text} | URL: {btn_href}")
                    
                    # Look for the one with "Next" text and a positive number in href
                    if btn_text == "Next" and btn_href and "/start/" in btn_href:
                        # Extract the start number from href
                        start_num = int(btn_href.split("/start/")[-1])
                        if start_num > 0:  # Next button should have positive number
                            next_btn = btn
                            break
                
                if next_btn:
                    next_url = next_btn.get_attribute("href")
                    print(f"  Found correct 'Next' button")
                    print(f"  Next URL: {next_url}")
                    print(f"  Navigating to Next Product Page...")
                    
                    # Navigate directly to the next URL
                    driver.get(next_url)
                    time.sleep(3)
                    product_page += 1
                    print(f"  Moved to Product Page {product_page}...\n")
                else:
                    print(f"  No more Product pages - Finished this reaction data")
                    break
                    
            except Exception as e:
                print(f"  Error finding Next button - Finished this reaction data")
                print(f"  Error: {e}")
                break
        
        print(f"Completed reaction data [{index}/{len(reaction_urls)}]")
        print(f"{'='*70}\n")

    print(f"\nFinished visiting all {len(reaction_urls)} reaction data pages!")

finally:    
    scraped_data_file.close()
    driver.quit()
    print("Script completed and browser closed.")
    print(f"All data saved to scraped_smiles_data.csv")