import requests, sys, re, os, time, pdfplumber, json
import pandas as pd
from bs4 import BeautifulSoup
from io import BytesIO

with open("ais_auth.json") as f:
    AIS_KEY = json.load(f)["key"]

def fetch_and_read_pdf(url):
    """
    Fetch a PDF from a URL and open it with pdfplumber
    
    Args:
        url (str): URL of the PDF to fetch
    
    Returns:
        all_text: a string of all extracted PDF content
    """
    try:
        # Fetch the PDF
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        # Check if the content is actually a PDF
        content_type = response.headers.get('content-type', '')
        if 'pdf' not in content_type.lower():
            print(f"Warning: Content-Type is '{content_type}', may not be a PDF")
        
        # Create a BytesIO object from the response content
        pdf_bytes = BytesIO(response.content)
        
        # Open with pdfplumber
        pdf = pdfplumber.open(pdf_bytes)
        
        # Extract text from all pages
        all_text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"
        
        print(f"Total characters extracted: {len(all_text)}")
        pdf.close()

        return all_text
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching PDF: {e}")
        return None
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return None
    
def extract_addresses(all_text):
    """
    Extract street addresses from Philly Land Bank Board agendas
    
    Args:
        all_text (str): a string of all extracted PDF content
    
    Returns:
        address_df: a pandas DataFrame with all normalized addresses
    """

    from passyunk.parser import PassyunkParser
    parser = PassyunkParser()

    #get all content that occurs between a bullet point and an opening parenthesis
    prop_lists = re.findall(r'•([^\()]*)', all_text)

    all_addrs = []
    for i in prop_lists:
        i = i.strip()
        i = i.replace("\n", " ")
        #if its a bullet point that starts with a number, it's a list of properties
        if re.match(r'\d',i[0]):
            #a semicolon is used to seperate lists of properties by street
            streets = i.split(";")
            for j in streets:
                #extract the street name
                street_name = re.findall(r'^[\d\s,\-*]+(.*?)$', j)[0].strip().upper().replace(".","")
                #within a street name, a comma is used to seperate house numbers
                address_numbers = j.split(",")
                for k in address_numbers:
                    last_item = k == address_numbers[-1]
                    k = k.strip()
                    k = k.replace("*", "")
                    k = k.replace(".", "")
                    #the last item in the comma seperated list already contains the street name
                    if last_item:
                        clean_addr = k.upper()
                    else:
                        clean_addr = f"{k} {street_name}"
                    parsed = parser.parse(clean_addr)
                    standardized_addr = parsed['components']['output_address']
                    all_addrs.append(standardized_addr)
    print(f'Extracted {len(all_addrs)} addresses from agenda...')
    return pd.DataFrame(data={'ADDRESS':all_addrs})

def query_addresses_ais(df):
   """
    Query Philly's Address Information System for info on each address in a dataframe
    
    Args:
        df: a pandas DataFrame with all normalized addresses
    
    Returns:
        df: a pandas DataFrame with all normalized addresses, OPA and PWD parcel IDs, and parcel coordinates
    """
   df[['OPA', 'PWD', 'lat', 'lon']] = None
   for idx, row in df.iterrows():
        addr = row['ADDRESS']
        print(f'Querying for info on {addr}...')
        spaced_addr = addr.replace(' ','%20')
        url = f'https://api.phila.gov/ais_doc/v1/search/{spaced_addr}?gatekeeperKey={AIS_KEY}'
        resp = requests.get(url)
        if resp.status_code == 404:
            print(f'No match for {addr}, continuing...')
            continue

        if resp.status_code == 429:
            print('waiting for 60 seconds to rate limit API usage...')
            time.sleep(60)
            resp = requests.get(url)
        elif resp.status_code != 200:
            print(f'Failure for {addr} with code {resp.status_code}: {resp.content}')
            continue

        content = json.loads(resp.content)
        if 'features' in content:
            df.at[idx, 'lon'] = content['features'][0]['geometry']['coordinates'][0]
            df.at[idx, 'lat'] = content['features'][0]['geometry']['coordinates'][1]
            df.at[idx,'OPA'] = content['features'][0]['properties']['opa_account_num']
            df.at[idx,'PWD'] = content['features'][0]['properties']['pwd_parcel_id']
   return df

def write_results(output_dir, df, date):
    """
    Query Philly's Address Information System for info on each address in a dataframe
    
    Args:
        df: a pandas DataFrame with all normalized addresses
    
    Returns:
        df: a pandas DataFrame with all normalized addresses, OPA and PWD parcel IDs, and parcel coordinates
    """
    current_path = os.path.join(output_dir, 'current_agenda.csv')
    df.to_csv(current_path)

    archive_path_root = os.path.join(output_dir, 'archive')
    os.makedirs(archive_path_root, exist_ok=True)
    archive_path = os.path.join(archive_path_root, f"{date.replace(' ','_').lower()}.csv")
    df.to_csv(archive_path)

    print(f"Wrote {len(df)} records to {archive_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        OUTPUT_DIR = "."
        print("No output directory specified, using current working directory...")
    elif os.path.exists(sys.argv[1]):
        OUTPUT_DIR = sys.argv[1]
        print(f"Writing output to {OUTPUT_DIR}...")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}
    home = requests.get("https://phillylandbank.org/philadelphia-land-bank-board/", headers=headers)
    home.raise_for_status()  # Raises an HTTPError for bad responses

    soup = BeautifulSoup(home.content, 'html.parser')
    agenda_urls = [tag.get('href') for tag in soup.find_all('a') if 'Agenda' in tag.contents[0]]

    if os.path.exists("parsed_urls.json"):
        with open("parsed_urls.json") as f:
            parsed_urls = json.load(f)
    else:
        parsed_urls = []
    if len(agenda_urls) == len(parsed_urls):
        print("No new agendas to parse, exiting...")
        sys.exit(0)
    else:
        agenda_url = agenda_urls[0]
        print(f"Scraping addresses from newly posted agenda at {agenda_url}...")

    all_text = fetch_and_read_pdf(agenda_url)
    date = re.findall(r'MEETING\n.*DAY(.*?20\d\d)', all_text)[0]
    date = date.replace(",", "")
    date = date.strip()

    print(f'Extracting addresses from agenda for PLB meeting on {date}...')
    addr_df = extract_addresses(all_text)
    full_df = query_addresses_ais(addr_df)

    #add meeting date and agenda url to all rows
    full_df['PLB_MEETING_DATE'] = date
    full_df['PLB_AGENDA_URL'] = agenda_url

    #save results as current agenda and for archive
    try:
        write_results(OUTPUT_DIR, full_df, date)
    except OSError as e:
        print(f"Failed to write to {OUTPUT_DIR} with exception {e}...")
        print("Trying to write to current working directory...")
        write_results(".", full_df, date)


    with open("parsed_urls.json", 'w') as f:
        json.dump(agenda_urls, f)