import time
import timeit
import sys
import logging
import reset_lib

no_conn_counter = 0
retry_counter = 0
runtime = 0
save_network = True
wrong_password = False
consecutive_active_reports = 0
config_hash = reset_lib.config_hash
#reset_lib.update_ssid()
#logging.config.fileConfig('/etc/raspiwifi/logger.conf')
logger = logging.getLogger('CMonitor')
reset_lib.set_log_level(logger)
#loggingLevel = reset_lib.set_log_level()
#logger.setLevel(loggingLevel)
 
# If auto_config is set to 0 in /etc/raspiwifi/raspiwifi.conf exit this script
if config_hash['auto_config'] == "0":
    sys.exit()
else:
    sleep_timer = int(config_hash['loop_interval'])
    wait_timer = int(config_hash['wait_interval'])
    retry_attempt = int(config_hash['retry_attempt'])
    
    #time.sleep(10)
    # Main connection monitoring loop at 10 second interval
    while True:
        start = timeit.default_timer()
        
        # ########### WiFi STATE - STATION ##############
        # If iwconfig report valid association with an AP
        # Save the network as trusted old_network        
        if reset_lib.is_wifi_connected() == True:
            no_conn_counter=0
            logger.debug("Wifi in [STATION] mode. Delay:" + str(round(no_conn_counter,4)))
            #if not reset_lib.check_subprocess('dhcpcd'):
            #    reset_lib.run_subprocess('sudo service dhcpcd start')
            #if not reset_lib.check_subprocess('dnsmasq'):
            #    reset_lib.run_subprocess('sudo service dnsmasq start')
            retry_counter=0
            wrong_password = False
            reset_lib.save_access_point()
            reset_lib.notify_state_change("STATION")
        
        
        # ########## WiFi STATE - CONNECTING/RECONNECTING ##############
        # If iwconfig report no association with an AP add 10 to the "No
        # Connection Couter"
        elif reset_lib.is_wifi_active() == False:
            if reset_lib.any_saved_network_exists():
                logger.debug("Wifi in [RECONNECTING] mode. Delay:" + str(round(no_conn_counter,4)) +" Retry:" + str(round(retry_counter,4)))
                reset_lib.notify_state_change("RECONNECTING")
                if reset_lib.match_existing_network():
                    if retry_counter >= retry_attempt:
                        logger.info('Cannot connect to saved network, wrong password.' +" Retry:" + str(round(retry_counter,4)))
                        wrong_password = True
                        retry_counter=0
                        no_conn_counter = 0
                        reset_lib.reset_to_host_mode()
                    else:
                        retry_counter += 1
                        #retry_counter += sleep_timer + runtime
                        #logger.info('Incremented Retry timer to :' + str(round(retry_counter,4)))
                    no_conn_counter += sleep_timer + runtime
                    consecutive_active_reports = 0
                    #reset_lib.unsave_access_point()
                else:
                    #logger.info('No matched network?.')
                    no_conn_counter += sleep_timer + runtime
                    consecutive_active_reports = 0
            else:
                logger.debug("Wifi in [CONNECTING] mode. Delay:" + str(round(no_conn_counter,4)))
                reset_lib.notify_state_change("CONNECTING")
                
                #if retry_counter >= retry_attempt:
                if no_conn_counter > wait_timer:
                    logger.info('Wrong input, going back to AP Mode.')
                    reset_lib.unsave_access_point()
                    wrong_password = True
                    no_conn_counter = 0
                    retry_counter = 0
                    reset_lib.reset_to_host_mode()
                
                no_conn_counter += sleep_timer + runtime
                retry_counter +=1
        
        
        # ###################### WiFi STATE - AP ######################
        # If iwconfig report AP as a host AP add sleep_timer to the "No
        # Connection Couter" ## Describe me More
        elif reset_lib.is_wifi_host() == True:
            logger.debug("Wifi in [AP] mode. Delay:" + str(round(no_conn_counter,4)))
            #if not reset_lib.check_subprocess('dhcpcd'):
            #    reset_lib.run_subprocess('service dhcpcd start')
            #if not reset_lib.check_subprocess('dnsmasq'):
            #    reset_lib.run_subprocess('service dnsmasq start')
            #if not reset_lib.check_subprocess('hostapd'):
            #    reset_lib.run_subprocess('service hostapd start')
            reset_lib.notify_state_change("AP")
            #time.sleep(int(config_hash['auto_config_delay']))
            if reset_lib.match_existing_network() == True and wrong_password == False:
                if reset_lib.try_connect_to_old_network() == False:
                    logger.debug("No valid network to connect to. Retrying..")
                #else:
                    #reset_lib.unsave_access_point()
                    #logger.debug("No valid network to connect to. Retrying..")
                
        # ############## WiFi STATE - UNDEFINED ################
        # If iwconfig report association with an AP add 1 to the
        # consecutive_active_reports counter and 10 to the no_conn_counter      
        else:
            consecutive_active_reports += 1
            no_conn_counter += sleep_timer + runtime
            logger.info("No connection counter is now: " + str(round(no_conn_counter,4)))
            # Since wpa_supplicant seems to breifly associate with an AP for
            # 6-8 seconds to check the network key the below will reset the
            # no_conn_counter to 0 only if two 10 second checks have come up active.
            if consecutive_active_reports >= 2:
                logger.info("Resetting all counters..")
                no_conn_counter = 0
                consecutive_active_reports = 0

        
        # ########## WiFi STATE - TIMEOUT ##############
        # If the number of seconds not associated with an AP is greater or
        # equal to the auto_config_delay specified in the /etc/raspiwifi/raspiwifi.conf
        # trigger a reset into AP Host (Configuration) mode.
        if no_conn_counter >= int(config_hash['auto_config_delay']):
            logger.info("Going to [AP] Mode after 'requested' delay..")
            retry_counter = 0
            no_conn_counter = 0
            consecutive_active_reports = 0
            if wrong_password == True and reset_lib.match_existing_network() == False:
                logger.info('Removing < INVALID > Network.')
                reset_lib.unsave_access_point()
            reset_lib.reset_to_host_mode()
            
        runtime = timeit.default_timer() - start
        logger.debug("Loop runtime :" + str(round(runtime,4)))
        # Put the loop to sleep for a while
        #if runtime < sleep_timer:
            #time.sleep(sleep_timer-runtime)
        time.sleep(sleep_timer)
