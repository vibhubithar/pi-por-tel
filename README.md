# Pi-Por-Tel 

##### (Noun) A RaspberryPi, BerryIMU-GPS, and InfluxDB based portable telemetry device
##### "use pi-por-tel to talk to your car"

##### So what is pi-por-tel?
It is a portable vehicle telemetry collection device or simply put it logs the sensors attached to this device on to a locally installed timeSeries database. It's hardware based on Rpi zero, inertial measurement unit (IMU) and GPS, with a software stack that uses Python and influxDB

##### What can it do for me?
- You can place it your car to collect race telemetry on the track and analyze it for faster track times. 
- I am using it to see what is my car doing on curvy roads that makes my child car sick.

##### Is it talking to the car using OBDII?
Not at this time, but interfacing OBDII wont be that hard

##### How do you power it?
USB port from my car powers the mini router and then mini-router's USB port powers the device

##### What is this repository for?
This repository focuses on the data collection aspect of the device. The assumption is that the device will be offline and will be continuously collecting data. In another repository, I'll focus on the data synchronization with the central location where it can be analyzed. 

So assemble, clone and go-on!

## Things that you will need

- Raspberry Pi Zero (Chosen because the form factor is small) - https://amzn.to/3nRFF2A 
- Berry IMU GPS - V4 (GPS IMU HAT for RPI) - https://amzn.to/3AtjZxd
- External powered GPS antenna - https://amzn.to/2XBlEmg
- Mini router (optional but handy) - https://amzn.to/3hOvk3m

## Hardware Assembly

### It's so simple that this picture should summarize
![Screenshot](assembled-pi-por-tel.jpg)

## Software Installation

### Prepare RPI zero with Buster build (in server mode)
#### - RPI OS Image - you can get it from here https://www.raspberrypi.org/software/operating-systems/#raspberry-pi-os-32-bit 
#### - SD card creation - I used etcher from balena.io 

#### Setup BerryIMU HAT for Raspberry pi

- Follow every step at :  https://ozzmaker.com/berrygps-setup-guide-raspberry-pi/
- while you are in the raspi-config also
  - enable SSH
  - change the power LED to blink on disk activity, crude but handy to see that the sensor data logs are being written

### Install influxdb ver 1.8.5 (Raspberry pi) 
```bash
sudo apt update
sudo apt upgrade -y
wget -qO- https://repos.influxdata.com/influxdb.key | sudo apt-key add -
source /etc/os-release
echo "deb https://repos.influxdata.com/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
sudo apt update && sudo apt install -y influxdb
sudo systemctl unmask influxdb.service
sudo systemctl start influxdb
sudo systemctl enable influxdb.service
```
### Preparing system 
```bash
sudo apt-get install -y git 
sudo apt-get install -y i2c-tools
sudo apt-get install -y python3-pip
```
### Preparing system to run Python Code 
```bash
sudo pip3 install serial 
sudo pip3 install pynmea2 
sudo pip3 install board 
sudo pip3 install busio 
sudo pip3 install influxdb
```
## Usage
1. Clone the repository on your raspberry pi
2. Run calibrateBerryIMU.py (optional but important to get better compass heading readings)
```bash
python3 calibrateBerryIMU.py

(output will look like this)
magXmin = -1790
magYmin = 2211
magZmin = -828
magXmax = -1745
magYmax = 2243
magZmax = -519
```
3. Paste the results of the step above in the berryIMU-Gforce-TPA-GPS-influx.py file as shown in the section below
```bash
################# Compass Calibration values ############
# Use calibrateBerryIMU.py to get calibration values
# Calibrating the compass isnt mandatory, however a calibrated
# compass will result in a more accurate heading value.

magXmin =  -3924
magYmin =  -125
magZmin =  -1446
magXmax =  289
magYmax =  2633
magZmax =  2242
```
4. Run the command
without tag values for influxdb
```bash
python3 berryIMU-Gforce-TPA-GPS-influx.py
```
OR 
with tag values for influxdb
```bash
python3 berryIMU-Gforce-TPA-GPS-influx.py --trip_type '<trip type on road /water / offroad>' --vehicle_type '<vehcile type SUV>' --brand '<vehicle brand>' --model '<vehicle model>' --seats <number of passengers> --mode '<what mode was the car in comfort/sports>' --logger_location '<location where device was placed>' --owner '<owner of the vehicle>' --tripID <numerical id of the trip> --trip_desc '<description of trip>'
```
## Outcome of all the hardwork as plotted in grafana
I'll be talking more about the aggregator setup in a separate repository as I dont recommend setting up grafana on the RPI 0

![Screenshot](pi-por-tel-grafana1.png)
![Screenshot](pi-portel-grafana-2.png)

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
