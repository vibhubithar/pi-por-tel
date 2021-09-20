# Pi-Por-Tel 

##### (Noun) A RaspberryPi, BerryIMU-GPS, and InfluxDB based portable telemetry device
##### "use pi-por-tel to talk to your car"

This repository focuses on the data collection aspect of the device. The assumption is that the device will be offline and will be continuously collecting data. In another repository, I'll focus on the data synchronization with the central location where it can be analyzed.

## Things that you will need

- Raspberry Pi Zero (Chosen because the form factor is small)
- Berry IMU GPS - V4 (GPS IMU HAT for RPI)
- External powered GPS antennae

## Installation

### Prepare RPI zero with Buster build (in server mode)

### Install influxdb ver 1.8.5 (Raspberry pi) 
```bash
sudo apt update 
sudo apt upgrade 
wget -qO- https://repos.influxdata.com/influxdb.key | sudo apt-key add - 
(important step add only the one belongs to your raspbian distro - check with cat /etc/os-release) 
echo "deb https://repos.influxdata.com/debian buster stable" | sudo tee /etc/apt/sources.list.d/ influxdb.list 
sudo apt update 
sudo apt install influxdb 
sudo systemctl unmask influxdb 
sudo systemctl enable influxdb 
sudo systemctl start influxdb influx
```
### Preparing system 
```bash
sudo apt-get install git 
sudo apt-get install i2c-tools
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
2. Run calibrateBerryIMU.py
```bash
python3 calibrateBerryIMU.py
```
3. Paste the results of the step above in the berryIMU-Gforce-TPA-GPS-influx.py file as shown in the section below
4. Run the command
```bash
python3 berryIMU-Gforce-TPA-GPS-influx.py --trip_type '<trip type on road /water / offroad>' --vehicle_type '<vehcile type SUV>' --brand '<vehicle brand>' --model '<vehicle model>' --seats <number of passengers> --mode '<what mode was the car in comfort/sports>' --logger_location '<location where device was placed>' --owner '<owner of the vehicle>' --tripID <numerical id of the trip> --trip_desc '<description of trip>'
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
