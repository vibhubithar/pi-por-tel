# pi-por-tel
RaspberryPi, BerryIMU-GPS and InfluxDB based portable telemetry device

This repository focuses on the data collection aspect of the device. Assumption is that the device will be offline and will be ccontineously collecting data.
In another repository i'll focus on the data synchronization with the cetral location where it can be analyzed.

Things that you will need 
1. Raspberry Pi Zero (Chosen because the form factor is small)
2. Berry IMU GPS - V4 (GPS IMU HAT for RPI)
3. External powered GPS antennae

Installation
1. Prepare RPI 0 with Buster build in server mode
2. Install influxdb ver 1.8.5 (Raspberry pi)
    https://pimylifeup.com/raspberry-pi-influxdb/
    sudo apt update
    sudo apt upgrade
    wget -qO- https://repos.influxdata.com/influxdb.key | sudo apt-key add -
    (important step add only the one belongs to your raspbian distro - check with cat /etc/os-release)
    echo "deb https://repos.influxdata.com/debian buster stable" | sudo tee /etc/apt/sources.list.d/ influxdb.list
    sudo apt update 
    sudo apt install influxdb
    sudo systemctl unmask influxdb
    sudo systemctl enable influxdb
    sudo systemctl start influxdb
    influx
3. Preparing system 
   sudo apt-get install git
   sudo apt-get install i2c-tools
   
4. Preparing system to run Python Code
     sudo pip3 install serial
     sudo pip3 install pynmea2
     sudo pip3 install board
     sudo pip3 install busio
     sudo pip3 install influxdb
