import requests
from bs4 import BeautifulSoup
import time
from plyer import notification
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
import winsound
import logging

timestamp = time.strftime("%Y%m%d-%H%M%S")

def load_credentials(file_path):
    with open(file_path, "r") as file:
        return json.load(file)

def send_email(subject, body, credentials):
    from_email = credentials["email_from"]
    from_password = credentials["email_from_pass"]
    to_email = credentials["email_to"]

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.close()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_desktop_notification(message):
    notification.notify(
        title='TURNOS PARA PASAPORTE',
        message=message,
        timeout=20  # Notification timeout in seconds
    )
    sound_path = "C:\\Windows\\Media\\notify.wav"  # Adjust this path to a valid sound file
    winsound.PlaySound(sound_path, winsound.SND_FILENAME)

def fetch_html(source):
    if source.startswith("http"):
        try:
            response = requests.get(source)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching URL: {e}")
            return None
    else:
        try:
            with open(source, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            print(f"Error reading local file: {e}")
            return None

def parse_table(html_content, service_name):
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", class_="table-bordered")
    
    if not table:
        print("Table with class 'table-bordered' not found.")
        return None

    rows = table.find_all("tr")
    for row in rows:
        first_cell = row.find("td")
        if first_cell and service_name in first_cell.get_text(strip=True):
            try:
                last_opening = row.find_all("td")[1].get_text(strip=True)
                next_opening = row.find_all("td")[2].get_text(strip=True)
                request_link = row.find("a")["href"]
                return {
                    "service": first_cell.get_text(strip=True),
                    "last_opening": last_opening,
                    "next_opening": next_opening,
                    "request_link": request_link
                }
            except Exception as e:
                print(f"Error extracting data from row: {e}")
                return None

    print(f"Service '{service_name}' not found in the table.")
    return None

def check_for_updates(service_name, previous_values, source, credentials):
    html_content = fetch_html(source)
    if html_content:
        service_info = parse_table(html_content, service_name)
        if service_info:
            current_last_opening = service_info['last_opening']
            current_next_opening = service_info['next_opening']

            if (current_last_opening != previous_values['last_opening']) or (current_next_opening != previous_values['next_opening']):
                subject = f"Update detected for service '{service_name}'"
                body = (f"Service: {service_info['service']}\n"
                        f"Last Opening: {current_last_opening}\n"
                        f"Next Opening: {current_next_opening}\n"
                        f"Request Link: {service_info['request_link']}")
                send_email(subject, body, credentials)
                send_desktop_notification(body)
                return {"last_opening": current_last_opening, "next_opening": current_next_opening}

    return previous_values

def load_previous_values(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    else:
        return {"last_opening": "", "next_opening": ""}

def save_previous_values(file_path, values):
    with open(file_path, "w") as file:
        json.dump(values, file)

def get_latest_state_file(directory):
    files = [f for f in os.listdir(directory) if f.startswith("out_") and f.endswith(".json")]
    if not files:
        return None
    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    return os.path.join(directory, latest_file)

def main():
    # Initialize logging
    logging.basicConfig(filename='script_log.txt', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info('Script started')

    service_name = "Pasaportesrenovación y primera vez"
    state_dir = ".\\diff\\"
    
    # source = ".\\test.html"
    source = "https://www.cgeonline.com.ar/informacion/apertura-de-citas.html"
    credentials_file_path = ".\\credentials.json"

    # Load email credentials
    credentials = load_credentials(credentials_file_path)
    to_email = credentials["email_to"]

    while True:
        # Load previous values from the latest timestamped file
        latest_state_file_path = get_latest_state_file(state_dir)
        if latest_state_file_path:
            previous_values = load_previous_values(latest_state_file_path)
        else:
            previous_values = {"last_opening": "", "next_opening": ""}

        # Check for updates and save new values if there are changes
        new_values = check_for_updates(service_name, previous_values, source, credentials)
        if new_values != previous_values:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            timestamped_state_file_path = os.path.join(state_dir, f"out_{timestamp}.json")
            save_previous_values(timestamped_state_file_path, new_values)  # Save with timestamp if there's an update
            # previous_values = new_values

        time.sleep(300)  # Check every 5 minutes
        # time.sleep(15)  # test

if __name__ == "__main__":
    main()
