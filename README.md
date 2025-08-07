# Philly Land Bank Scraper

Find out which publicly owned properties in Philly are being transferred to new owners. 

Designed to be run monthly, the scraper fetches the latest agenda PDF from the Land Bank Board's website, parses out all addresses, tags them with OPA and PWD IDs for easy merging with other datasets, and writes the result to a geocoded csv.

## Quick set up
```
/usr/bin/python3.11 -m venv venv && source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
echo '{"key":"YOUR_AIS_KEY"}' >> ais_auth.json
```
