#!/usr/bin/env python
# coding: utf-8

import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json, sys

def executeEmail(reciever_emails, subject, html):
    # import the SMTL config file
    SMTP_CONFIG_FILE = './smtp-config.json'
    SMTP_CONFIG = {}
    
    with open(SMTP_CONFIG_FILE, 'r') as f:
        SMTP_CONFIG = json.load(f)
    
    sender_email = SMTP_CONFIG['username']
    receiver_email = reciever_emails

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = ", ".join(receiver_email)

    # Create the plain-text and HTML version of your message
    text = html

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part 
    message.attach(part1)
    message.attach(part2)

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Try to log in to server and send email
    try:
        server = smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port'])
        server.starttls(context=context) # Secure the connection
        server.login(SMTP_CONFIG['username'], SMTP_CONFIG['password'])

        # Send email
        server.sendmail(sender_email, receiver_email, message.as_string())

        print("Sent!")
    except Exception as e:
        print(e)
    finally:
        server.quit()
