from flask import Flask, render_template, request
import subprocess
import os
import logging
import reset_lib
import time
from threading import Thread
import fileinput

#logging.config.fileConfig('/etc/raspiwifi/logger.conf')
logger = logging.getLogger('APConfig')
reset_lib.set_log_level(logger)
#loggingLevel = reset_lib.set_log_level()
#logger.setLevel(loggingLevel)

app = Flask(__name__)
app.debug = True

config_hash = reset_lib.config_hash

@app.route('/')
def index():
    wifi_ap_array = reset_lib.scan_wifi_networks()
    #config_hash = reset_lib.config_file_hash()

    return render_template('app.html', wifi_ap_array = wifi_ap_array, config_hash = config_hash)


@app.route('/manual_ssid_entry')
def manual_ssid_entry():
    return render_template('manual_ssid_entry.html')

@app.route('/wpa_settings')
def wpa_settings():
    #config_hash = reset_lib.config_file_hash()
    return render_template('wpa_settings.html', wpa_enabled = config_hash['wpa_enabled'], wpa_key = config_hash['wpa_key'])


@app.route('/save_credentials', methods = ['GET', 'POST'])
def save_credentials():
    ssid = request.form['ssid']
    wifi_key = request.form['wifi_key']
    logger.info("New user input received, creating wpa_supplicant.")
    logger.info("Trying to set up STATION mode...")
    create_wpa_supplicant(ssid, wifi_key)
    if reset_lib.any_saved_network_exists():
        reset_lib.unsave_access_point()
    
    # Call set_ap_client_mode() in a thread otherwise the reboot will prevent
    # the response from getting to the browser
    def sleep_and_start_ap():
        time.sleep(2)
        reset_lib.set_ap_client_mode()
    t = Thread(target=sleep_and_start_ap)
    t.start()

    return render_template('save_credentials.html', ssid = ssid)


@app.route('/save_wpa_credentials', methods = ['GET', 'POST'])
def save_wpa_credentials():
    #config_hash = reset_lib.config_file_hash()
    wpa_enabled = request.form.get('wpa_enabled')
    wpa_key = request.form['wpa_key']

    if str(wpa_enabled) == '1':
        update_wpa(1, wpa_key)
    else:
        update_wpa(0, wpa_key)

    def sleep_and_reboot_for_wpa():
        time.sleep(2)
        reset_lib.run_subprocess('reboot')

    t = Thread(target=sleep_and_reboot_for_wpa)
    t.start()

    #config_hash = config_file_hash()
    return render_template('save_wpa_credentials.html', wpa_enabled = config_hash['wpa_enabled'], wpa_key = config_hash['wpa_key'])



def create_wpa_supplicant(ssid, wifi_key):
    temp_conf_file = open('wpa_supplicant.conf.tmp', 'w')

    temp_conf_file.write('ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n')
    temp_conf_file.write('update_config=1\n')
    temp_conf_file.write('\n')
    temp_conf_file.write('network={\n')
    temp_conf_file.write('	ssid="' + ssid + '"\n')

    if wifi_key == '':
        temp_conf_file.write('	key_mgmt=NONE\n')
    else:
        temp_conf_file.write('	psk="' + wifi_key + '"\n')

    temp_conf_file.write('	}')

    temp_conf_file.close

    reset_lib.run_subprocess('mv wpa_supplicant.conf.tmp /etc/wpa_supplicant/wpa_supplicant.conf')


def update_wpa(wpa_enabled, wpa_key):
    with fileinput.FileInput('/etc/raspiwifi/raspiwifi.conf', inplace=True) as raspiwifi_conf:
        for line in raspiwifi_conf:
            if 'wpa_enabled=' in line:
                line_array = line.split('=')
                line_array[1] = wpa_enabled
                print(line_array[0] + '=' + str(line_array[1]))

            if 'wpa_key=' in line:
                line_array = line.split('=')
                line_array[1] = wpa_key
                print(line_array[0] + '=' + line_array[1])

            if 'wpa_enabled=' not in line and 'wpa_key=' not in line:
                print(line, end='')



if __name__ == '__main__':
    #config_hash = resetlib. config_file_hash()

    if config_hash['ssl_enabled'] == "1":
        app.run(host = '0.0.0.0', port = int(config_hash['server_port']), ssl_context='adhoc', debug=False)
    else:
        app.run(host = '0.0.0.0', port = int(config_hash['server_port']), debug=False)
