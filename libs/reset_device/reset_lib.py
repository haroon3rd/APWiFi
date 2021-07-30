import os
import sys
import time
import uuid
import timeit
import fileinput
import logging
#import logging.config
import subprocess
from threading import Thread

global config_hash
current_state = "NONE"
previous_time=0

# Initialize logger here
logging.basicConfig(filename='/etc/raspiwifi/wmy-wifi.log', filemode='a+', format='%(asctime)s | %(levelname)s - %(name)s : %(message)s',level=logging.DEBUG)
logger = logging.getLogger('ResetLib')
logger.info("################   Started logging...  ################")



# This function reads the configuration
# file and stores it in config_hash[]
def config_file_hash():
    logger.info("---------:::::  Reading configuration file :::::--------")
    config_file = open('/etc/raspiwifi/raspiwifi.conf')
    hash_map = {}
    for line in config_file:
        line_key = line.split("=")[0]
        line_value = line.split("=")[1].rstrip()
        hash_map[line_key] = line_value
        logger.info(line_key + " value is : " + line_value)

    return hash_map

config_hash = config_file_hash()

# Function to set log level
def set_log_level(logger):
    #config_hash = config_file_hash()
    level = config_hash["log_level"]
    if int(level)==1:
        logger.setLevel(logging.DEBUG)
        #return logging.DEBUG
    elif int(level)==2:
        logger.setLevel(logging.INFO)
        #return logging.INFO
    elif int(level)==3:
        logger.setLevel(logging.WARNING)
        #return logging.WARNING
    elif int(level)==4:
        logger.setLevel(logging.ERROR)
        #return logging.ERROR
    elif int(level)==5:
        logger.setLevel(logging.CRITICAL)
        #return logging.CRITICAL
    else:
        logger.setLevel(logging.NOTSET)
        #return logging.NOTSET
    

# Initialize logger with file
# logging.config.fileConfig('/etc/raspiwifi/logger.conf')

# Now set a custom log level
set_log_level(logger)
#logger.info(config_hash)

# Function to save PID to a file
def savePIDFile(pid, file):
    try:
        f = open(file, 'w')
        f.write(pid)
    except IOError as e:
        logger.error("PID cannot be written : " + str(e))
    finally:
        logger.info("PID #" + pid + " saved in file: " + file)
        f.close()

def killPIDFile(file):
    try:
        os.unlink(file)
        logger.debug("PID File successfully removed!")
    except IOError as e:
        logger.error("PID cannot be written : " + str(e))


def read_pid_from_pidfile(pidfile_path):
    pid = None
    try:
        pidfile = open(pidfile_path, 'r')
    except IOError:
        pass
    else:
        line = pidfile.readline().strip()
        try:
            pid = int(line)
        except ValueError:
            pass
        pidfile.close()

    return pid

# Function run os commands and catch the error
def run_subprocess(command):
    success = False
    #try:
    #    rcode = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=20)
    #    #rcode = subprocess.call(command, shell = True)
    #    if rcode.stderr != "":
    #        #print("Child process terminated by signal", -rcode, file=sys.stderr)
    #        logger.error("Terminated by signal " + str(-rcode))
    #        logger.error(command + "-error: " +  str(sys.stderr))
    #        #success = True
    #    else:
    #        logger.debug(command + "-returned " + str(rcode))
    #        success = True
    #except Exception as e:
    #    #print("Execution Failed!!: ", e, file=sys.stderr)
    #    logger.critical(command + " - Failed!!: ")
    #    logger.critical("Error: " + str(e))        
    
    rcode = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=20)
    #rcode = subprocess.call(command, shell = True)
    if rcode.returncode is not 0:
        #print("Child process terminated by signal", -rcode, file=sys.stderr)
        logger.error("Terminated by signal " + str(rcode.returncode))
        logger.error(command + "-error: " +  str(rcode.stderr))
        #success = True
    else:
        logger.debug(command + "-returned " + str(rcode.returncode))
        success = True 
    return success


def check_subprocess(command):
    success = False
    #try:
    #    rcode = subprocess.run("pgrep -x " + command + " >/dev/null", shell = True, text=True, capture_output=True, timeout=10)
    #    if rcode.stderr != "":
    #        logger.error("Terminated by signal " + str(-rcode))
    #        logger.error(command + "-error: " +  str(sys.stderr))
    #    else:
    #        success = True
    #except Exception as e:
    #    logger.critical("Error: " + str(e))  
    
    rcode = subprocess.run("pgrep -x " + command + " >/dev/null", shell = True, text=True, capture_output=True, timeout=10)
    if rcode.returncode is not 0:
        logger.error("Terminated by signal " + str(rcode.returncode))
        logger.error(command + "-error: " +  str(rcode.stderr))
    else:
        success = True
    #except Exception as e:
    #    logger.critical("Error: " + str(e))




# Function to check and activate
# wpa option if chosen by user
def wpa_check_activate(wpa_enabled, wpa_key):
    logger.info("Checking if wpa is required.")
    wpa_active = False
    reboot_required = False

    with open('/etc/hostapd/hostapd.conf') as hostapd_conf:
        for line in hostapd_conf:
            if 'wpa_passphrase' in line:
                wpa_active = True

    if wpa_enabled == '1' and wpa_active == False:
        reboot_required = True
        run_subprocess(
            'cp /usr/lib/raspiwifi/reset_device/static_files/hostapd.conf.wpa /etc/hostapd/hostapd.conf')

    if wpa_enabled == '1':
        with fileinput.FileInput('/etc/hostapd/hostapd.conf', inplace=True) as hostapd_conf:
            for line in hostapd_conf:
                if 'wpa_passphrase' in line:
                    if 'wpa_passphrase=' + wpa_key not in line:
                        print('wpa_passphrase=' + wpa_key)
                        run_subprocess('reboot')
                    else:
                        print(line, end='')
                else:
                    print(line, end='')

    if wpa_enabled == '0' and wpa_active == True:
        reboot_required = True
        run_subprocess(
            'cp /usr/lib/raspiwifi/reset_device/static_files/hostapd.conf.nowpa /etc/hostapd/hostapd.conf')

    return reboot_required


# Function to get last four digits of
# RPI MAC address to be added at the end
# of user defined SSID
def get_mac_last_four():
    mac_last_four = str(hex(uuid.getnode()))[-4:]
    return mac_last_four.upper()


# Function to update user defined SSID
# and add RPI model number at the end
# Has not been updated...

def update_ssid():
    logger.info("Updating SSID - if needed.")
    mac_last_four = str(hex(uuid.getnode()))[-4:].upper()
    ssid_prefix = config_hash['ssid_prefix']
    hostapd_restart = False
    ssid_change = False
    
    # Need a try catch here.
    with open('/etc/hostapd/hostapd.conf') as hostapd_conf:
        for line in hostapd_conf:
            if not ssid_prefix in line:
                print(ssid_prefix)
                ssid_change = True

    if ssid_change == True:
        logger.info("Updating SSID - adding last 4 digits of MAC.")
        with fileinput.FileInput("/etc/hostapd/hostapd.conf", inplace=True) as file:
            for line in file:
                if 'ssid=' in line:
                    line_array = line.split('=')
                    line_array[1] = ssid_prefix + '-' + mac_last_four
                    print(line_array[0] + '=' + line_array[1])
                else:
                    print(line, end='')

        #logger.info("SSID has been updated.")
        hostapd_restart = True

    return hostapd_restart


# Function to check if old_network.conf exists
def any_saved_network_exists():
    if os.path.exists('/etc/wpa_supplicant/old_network.conf'):
        logger.debug("A < SAVED > Network Exists.")
        return True
    else:
        return False

# Function to check if wpa_supplicant.conf exists
def any_default_network_exists():
    if os.path.exists('/etc/wpa_supplicant/wpa_supplicant.conf'):
        logger.debug("A < DEFAULT > Network Exists.")
        return True
    else:
        return False


# Function to create old_network.conf when connected
def save_access_point():
    logger.debug("Saving < VALID > wifi network.")
    run_subprocess('cp /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/old_network.conf')

# Function to remove old_network.conf when invalid
def unsave_access_point():
    logger.debug('Removing < INVALID > Network.')
    run_subprocess('rm -f /etc/wpa_supplicant/old_network.conf')
    #run_subprocess('rm -f /etc/wpa_supplicant/wpa_supplicant.conf')


# Function to kill and restart wpa supplicant
def try_wpa_connection():
    success = False
    logger.info("Restarting < WiFi > connection.")
    if any_default_network_exists() == False:
        run_subprocess('cp /etc/wpa_supplicant/wpa_supplicant.conf.original /etc/wpa_supplicant/wpa_supplicant.conf')
    for x in range(1):
        #run_subprocess("ps -ef | grep wpa_supplicant | grep -v grep | awk '{print $2}' | xargs sudo kill")
        #run_subprocess("sudo rm -f/var/run/wpa_supplicant/wlan0")
        if check_subprocess("wpa_supplicant"):
            run_subprocess("systemctl stop wpa_supplicant.service")
        if not check_subprocess('wpa_supplicant'):
            run_subprocess('wpa_supplicant -i wlan0 -B -c/etc/wpa_supplicant/wpa_supplicant.conf')
        if is_wifi_connected() == True:
            logger.info("######## Successful wpa connection.")    
            success = True
        else:
            time.sleep(2)
    return success
        

# Function to return Wifi Status if Managed but not Associated.
def is_wifi_active():
    iwconfig_out = subprocess.check_output(['iwconfig']).decode('utf-8')
    wifi_active = True

    if "Access Point: Not-Associated" in iwconfig_out:
        wifi_active = False
        logger.debug("Wifi station is not associated to any AP.")

    return wifi_active

# Function to return Wifi Status if Managed and Associated to an AP.
def is_wifi_connected():
    iwconfig_out = subprocess.check_output(['iwconfig']).decode('utf-8')
    wifi_connected = False

    if not "Access Point: Not-Associated" in iwconfig_out:
        if "Mode:Managed" in iwconfig_out:
            wifi_connected = True
            logger.debug("Wifi station is now associated to a valid AP.")
            #run_subprocess('cp /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/old_network.conf')
    return wifi_connected


# Function to return Wifi Status if Mode:Master.
def is_wifi_host():
    iwconfig_out = subprocess.check_output(['iwconfig']).decode('utf-8')
    wifi_host = False

    if "Mode:Master" in iwconfig_out:
        #logger.debug("Wifi mode is Mode:Master")
        wifi_host = True

    return wifi_host


# Function to immediately log state change
def notify_state_change(new_state):
    global current_state
    global previous_time
    if new_state != current_state:
        current_time = timeit.default_timer()
        duration = round(abs(previous_time-current_time),4)
        previous_time = current_time
        logger.info("State change after " + str(duration) )  
        logger.info("Current state is: [" + new_state + "]")
        current_state = new_state


# Function to scan Wifi networks and return a list array.
def scan_wifi_networks():
    iwlist_raw = subprocess.Popen(['iwlist', 'scan'], stdout=subprocess.PIPE)
    ap_list, err = iwlist_raw.communicate()
    ap_array = []
    logger.debug("Looking for available wireless network.")
    for line in ap_list.decode('utf-8').rsplit('\n'):
        if 'ESSID' in line:
            ap_ssid = line[27:-1]
            if ap_ssid != '':
                ap_array.append(ap_ssid)
    
    return ap_array


# Function to check if there is any saved network that
# matches with one from the list of scanned network
def match_existing_network():
    #logger.info("< MATCHING > < YES / NO > ?.")
    ssid_found = False
    if any_saved_network_exists():
        # Need a try catch here.
        read_file = open('/etc/wpa_supplicant/old_network.conf')
        ssid_array = scan_wifi_networks()
        for line in read_file:
            if 'ssid=' in line:
                line_array = line.split('=')
                read_ssid = line_array[1].replace('"', '')
                read_ssid = read_ssid.rstrip("\n")
                if read_ssid in ssid_array:
                    logger.debug("A < MATCHING > network has been found.")
                    ssid_found = True
        read_file.close
    else:
        logger.debug('No < MATCHING > network information available..')
    return ssid_found



# Function to switch to STATION mode when a matching network is found.
def try_connect_to_old_network():
    success = False
    logger.debug("Trying to Connect to any < SAVED > network.")
    if match_existing_network() == True:
        run_subprocess('cp /etc/wpa_supplicant/old_network.conf /etc/wpa_supplicant/wpa_supplicant.conf')
        set_ap_client_mode()
        #def sleep_and_start_ap():
    #        time.sleep(2)
        #    set_ap_client_mode()
        #t = Thread(target=sleep_and_start_ap)
        #t.start()
   # time.sleep(3)
    if is_wifi_connected() == True:
        success = True 
    # else:
        #run_subprocess('')
    return success




# Function to setup STATION by removing/restarting ACCESS-POINT Mode files and services.
def set_ap_client_mode():
    logger.info("Setting Wifi as [STA].")
    # First kill the Flask Application
    # Remove the host_mode probing file
    run_subprocess('rm -f /etc/raspiwifi/host_mode')
    
    # Swap bootstrap files for next reboot
    run_subprocess('rm /etc/cron.raspiwifi/aphost_bootstrapper')
    run_subprocess('cp /usr/lib/raspiwifi/reset_device/static_files/apclient_bootstrapper /etc/cron.raspiwifi/')
    run_subprocess('chmod +x /etc/cron.raspiwifi/apclient_bootstrapper')
    
    # Swap/remove dnsmasq config files
    run_subprocess('mv /etc/dnsmasq.conf.original /etc/dnsmasq.conf')
    run_subprocess('rm -f /etc/dhcpcd.conf')
    run_subprocess('mv /etc/dhcpcd.conf.original /etc/dhcpcd.conf')
    
    # Kill hostapd, dnsmasq and dhcpd service
    logger.info("Killing hostapd, dnsmasq & dhcpcd..")
    run_subprocess("service hostapd stop")
    #while check_subprocess("hostapd"):
    #run_subprocess("ps -ef | grep hostapd | grep -v grep | awk '{print $2}' | xargs sudo kill")
    run_subprocess("systemctl stop dnsmasq.service")
    #while check_subprocess("dnsmasq"):
    #run_subprocess("ps -ef | grep dnsmasq | grep -v grep | awk '{print $2}' | xargs sudo kill")
    run_subprocess("systemctl stop dhcpcd.service")
    #while check_subprocess("dhcpcd"):
    #run_subprocess("ps -ef | grep dhcpcd | grep -v grep | awk '{print $2}' | xargs sudo kill")
    
    # Start dnsmasq and dhcpd service in correct order
    logger.info("Start dnsmasq & dhcpcd..")
    #while not check_subprocess("dhcpcd"):
    run_subprocess("systemctl start dhcpcd.service")
    #run_subprocess('sudo /sbin/dhcpcd -q -b &')
    #while not check_subprocess("dnsmasq"):
    run_subprocess('systemctl start dnsmasq.service')
        #time.sleep(1)
    
    
    # Restart wpa_supplicant service
    try_wpa_connection()
    # logger.info("Wifi switched to [STA] mode.")
    
    # Last kill the Flask Application
    logger.info("Killing the Flask application..")
    # run_subprocess("ps -ef | grep app.py | grep -v grep | awk '{print $2}' | xargs sudo kill")
    if os.path.isfile('/etc/raspiwifi/app.pid'):
        run_subprocess("ps -ef | grep app.py | grep -v grep | awk '{print $2}' | xargs sudo kill")
        run_subprocess("rm -f /etc/raspiwifi/app.pid")
    logger.info("All steps completed for STATION mode..")


# Function to setup ACCESS-POINT by removing/restarting STATION Mode files and services.
def reset_to_host_mode():
    logger.info("Setting Wifi as [AP].")
    #run_subprocess("ps -ef | grep wpa_supplicant | grep -v grep | awk '{print $2}' | xargs sudo kill")
    logger.info("Killing wpa_supplicant..")
    #while check_subprocess("wpa_supplicant"):
    run_subprocess("service wpa_supplicant stop")
    if not os.path.isfile('/etc/raspiwifi/host_mode'):
        # First remove existing wifi config file and any tmp file
        run_subprocess('rm -f /etc/wpa_supplicant/wpa_supplicant.conf')
        
        # Swap bootstrap files for next reboot
        run_subprocess('rm /etc/cron.raspiwifi/apclient_bootstrapper')
        run_subprocess('cp /usr/lib/raspiwifi/reset_device/static_files/aphost_bootstrapper /etc/cron.raspiwifi/')
        run_subprocess('chmod +x /etc/cron.raspiwifi/aphost_bootstrapper')
        
        # Swap/remove dhcpcd config files
        run_subprocess('mv /etc/dhcpcd.conf /etc/dhcpcd.conf.original')
        run_subprocess('cp /usr/lib/raspiwifi/reset_device/static_files/dhcpcd.conf /etc/')
        
        # Swap/remove dnsmasq config files
        run_subprocess('mv /etc/dnsmasq.conf /etc/dnsmasq.conf.original')
        run_subprocess('cp /usr/lib/raspiwifi/reset_device/static_files/dnsmasq.conf /etc/')
        
        # Create host_mode probing file
        run_subprocess('touch /etc/raspiwifi/host_mode')
        
        # Start Flask server
        if not os.path.isfile('/etc/raspiwifi/app.pid'):
            logger.info("Running the Flask application..")
            run_subprocess('sudo python3 /usr/lib/raspiwifi/reset_device/app.py &')
    
    # # Stop dnsmasq and dhcpcd service in any order
    logger.info("Killing dnsmasq & dhcpcd..")
    run_subprocess("systemctl stop dhcpcd.service")
    #while check_subprocess("dhcpcd"):
    #run_subprocess("ps -ef | grep dhcpcd | grep -v grep | awk '{print $2}' | xargs sudo kill")
    run_subprocess("systemctl stop dnsmasq.service")
    #while check_subprocess("dnsmasq"):
    #run_subprocess("ps -ef | grep dnsmasq | grep -v grep | awk '{print $2}' | xargs sudo kill")
    #time.sleep(1)
    
    # Start dnsmasq and dhcpcd service in order
    logger.info("Starting dnsmasq & dhcpcd..")
    #while not check_subprocess('dnsmasq'):
    run_subprocess('systemctl start dnsmasq.service')
        #time.sleep(4)
    run_subprocess('systemctl start dhcpcd.service')
    #while not check_subprocess('dhcpcd'):
    #run_subprocess('sudo /sbin/dhcpcd -q -b &')
        # time.sleep(1)
    
    # Start hostapd service
    # run_subprocess('sudo python3 /usr/lib/raspiwifi/reset_device/app.py &')
    # Restart wlan0 interface
    # run_subprocess('sudo service networking restart')
    run_subprocess('ifconfig wlan0 down')
    run_subprocess('ifconfig wlan0 up')
    logger.info("Starting hostapd service..")
    #while not check_subprocess('hostapd'):
    run_subprocess('systemctl start hostapd.service')
    time.sleep(5)
    
    logger.info("All steps completed for AP mode..")
    
    # Now recheck if all services are running, else restart
        
        
    # time.sleep(4)
    # logger.info("Wifi switched to [AP] mode.")
