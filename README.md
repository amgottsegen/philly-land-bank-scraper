## Quick set up
/usr/bin/python3.11 -m venv venv && source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
echo '{"key":"YOUR_AIS_KEY"}' >> ais_auth.json