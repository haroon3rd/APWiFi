#!/bin/bash

rm -f /etc/wpa_supplicant/wpa_supplicant.conf
rm -f /home/pi/Projects/RaspiWifi/tmp/*
rm /etc/cron.raspiwifi/noreboot_client_bootstrapper
cp /usr/lib/raspiwifi/reset_device/static_files/noreboot_host_bootstrapper /etc/cron.raspiwifi/
chmod +x /etc/cron.raspiwifi/noreboot_host_bootstrapper
mv /etc/dhcpcd.conf /etc/dhcpcd.conf.original
cp /usr/lib/raspiwifi/reset_device/static_files/dhcpcd.conf /etc/
mv /etc/dnsmasq.conf /etc/dnsmasq.conf.original
cp /usr/lib/raspiwifi/reset_device/static_files/dnsmasq.conf /etc/
cp /usr/lib/raspiwifi/reset_device/static_files/dhcpcd.conf /etc/
touch /etc/raspiwifi/host_mode
sudo python3 /usr/lib/raspiwifi/configuration_app/app.py &
sudo killall wpa_supplicant
sleep 2
sudo service networking restart
sleep 2
sudo /sbin/dhcpcd -q -b
sleep 5
sudo hostapd -dd /etc/hostapd/hostapd.conf &
ps -ef | grep dnsmasq | grep -v grep | awk '{print $2}' | xargs sudo kill
sudo service dnsmasq start
sleep 2
sudo service networking restart