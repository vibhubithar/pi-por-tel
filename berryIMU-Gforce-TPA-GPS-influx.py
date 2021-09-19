#!/usr/bin/python
#
#    This program  reads the angles from the acceleromteer, gyroscope
#    and mangnetometer on a BerryIMU connected to a Raspberry Pi.
#
#    This program includes two filters (low pass and median) to improve the
#    values returned from BerryIMU by reducing noise.
#
#    The BerryIMUv1, BerryIMUv2 and BerryIMUv3 are supported
#
#    This script is python 2.7 and 3 compatible
#
#    Feel free to do whatever you like with this code.
#    Distributed as-is; no warranty is given.
#
#    http://ozzmaker.com/
#command - python3 berryIMU-Gforce-TPA-GPS-influx.py --trip_type road --vehicle_type SUV --brand mercedes --model GLS450 --seats 7 --mode comfort --logger_location 'center console' --owner vibhu --tripID 1 --trip_desc 'albany - oakhurst'



import sys
import time
import math
import IMU
import datetime
import os
#for the temperature and  pressure readings
import smbus
#loggin
import logging
#setting up the log file and format
logFileName = 'gpsLogger'+datetime.datetime.utcnow().strftime("%Y-%m-%d-%H:%M:%S")+'.log'
logging.basicConfig(filename=logFileName, level=logging.CRITICAL, format='%(asctime)s.%(msecs)03d,%(message)s',datefmt='%Y-%m-%d %H:%M:%S')

import pynmea2
import serial
import io

#setting up serial for GPS comm
ser = serial.Serial('/dev/serial0', 9600, timeout=5.0)
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))

#influxDB
from influxdb import InfluxDBClient
import time #for timestamp
import csv
# from datetime import datetime

import argparse
parser = argparse.ArgumentParser()
# parser.add_argument("--file", help="Name of the input file")
parser.add_argument("--trip_type", default='road',help="road/walking/biking")
parser.add_argument("--vehicle_type", default='SUV', help="SUV/spors/coupe/racing")
parser.add_argument("--brand", default='mercedes', help="manufacturer")
parser.add_argument("--model", default='GLS450', help="model 981/gls/glc")
parser.add_argument("--seats", default= 7, help="max passenger capacity")
parser.add_argument("--mode", default='comfort',help="mode sports comfort auto eco")
parser.add_argument("--logger_location", default='center console', help="location where the hardware was placed")
parser.add_argument("--owner", default='vibhu', help="who was driving the vehicle")
parser.add_argument("--tripID", default=1, help="id for multiple trips in a day")
trip_desc_default = 'trip-'+datetime.datetime.utcnow().strftime("%Y-%m-%d-%H:%M:%S")
parser.add_argument("--trip_desc", default=trip_desc_default, help="start ending location of your trip")

args = parser.parse_args()

# filename = args.file #'motionData-4-22-21.csv'
trip_type= args.trip_type
vehicle_type= args.vehicle_type
model = args.model
brand = args.brand
seats = args.seats
mode = args.mode 
logger_location = args.logger_location
owner = args.owner
tripID = args.tripID
trip_desc = args.trip_desc


#creating influxdb object to enter data
influx_client = InfluxDBClient('localhost', 8086, 'root', 'root', 'gpsLogger')
result_client = influx_client.create_database('gpsLogger')
# print(result_client)


RMC_speed = 0.0
GGA_altitude = 0.0
GGA_sat_num = 0
GPS_datestamp = ''
GPS_timestamp = ''
GPS_lat = 0.0
GPS_lat_dir = ''
GPS_lon = 0.0
GPS_lon_dir = ''

RAD_TO_DEG = 57.29578
M_PI = 3.14159265358979323846
G_GAIN = 0.070          # [deg/s/LSB]  If you change the dps for gyro, you need to update this value accordingly
AA =  0.40              # Complementary filter constant
MAG_LPF_FACTOR = 0.4    # Low pass filter constant magnetometer
ACC_LPF_FACTOR = 0.4    # Low pass filter constant for accelerometer
ACC_MEDIANTABLESIZE = 9         # Median filter table size for accelerometer. Higher = smoother but a longer delay
MAG_MEDIANTABLESIZE = 9         # Median filter table size for magnetometer. Higher = smoother but a longer delay



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


'''
Here is an example:
magXmin =  -1748
magYmin =  -1025
magZmin =  -1876
magXmax =  959
magYmax =  1651
magZmax =  708
Dont use the above values, these are just an example.
'''
############### END Calibration offsets #################


#Kalman filter variables
Q_angle = 0.02
Q_gyro = 0.0015
R_angle = 0.005
y_bias = 0.0
x_bias = 0.0
XP_00 = 0.0
XP_01 = 0.0
XP_10 = 0.0
XP_11 = 0.0
YP_00 = 0.0
YP_01 = 0.0
YP_10 = 0.0
YP_11 = 0.0
KFangleX = 0.0
KFangleY = 0.0

# define BMP388 Device I2C address

I2C_ADD_BMP388_AD0_LOW = 0x76
I2C_ADD_BMP388_AD0_HIGH = 0x77
I2C_ADD_BMP388 = I2C_ADD_BMP388_AD0_HIGH

BMP388_REG_ADD_WIA = 0x00
BMP388_REG_VAL_WIA = 0x50

BMP388_REG_ADD_ERR = 0x02
BMP388_REG_VAL_FATAL_ERR = 0x01
BMP388_REG_VAL_CMD_ERR = 0x02
BMP388_REG_VAL_CONF_ERR = 0x04

BMP388_REG_ADD_STATUS = 0x03
BMP388_REG_VAL_CMD_RDY = 0x10
BMP388_REG_VAL_DRDY_PRESS = 0x20
BMP388_REG_VAL_DRDY_TEMP = 0x40

BMP388_REG_ADD_CMD = 0x7E
BMP388_REG_VAL_EXTMODE_EN = 0x34
BMP388_REG_VAL_FIFI_FLUSH = 0xB0
BMP388_REG_VAL_SOFT_RESET = 0xB6

BMP388_REG_ADD_PWR_CTRL = 0x1B
BMP388_REG_VAL_PRESS_EN = 0x01
BMP388_REG_VAL_TEMP_EN = 0x02
BMP388_REG_VAL_NORMAL_MODE = 0x30

BMP388_REG_ADD_PRESS_XLSB = 0x04
BMP388_REG_ADD_PRESS_LSB = 0x05
BMP388_REG_ADD_PRESS_MSB = 0x06
BMP388_REG_ADD_TEMP_XLSB = 0x07
BMP388_REG_ADD_TEMP_LSB = 0x08
BMP388_REG_ADD_TEMP_MSB = 0x09

BMP388_REG_ADD_T1_LSB = 0x31
BMP388_REG_ADD_T1_MSB = 0x32
BMP388_REG_ADD_T2_LSB = 0x33
BMP388_REG_ADD_T2_MSB = 0x34
BMP388_REG_ADD_T3 = 0x35
BMP388_REG_ADD_P1_LSB = 0x36
BMP388_REG_ADD_P1_MSB = 0x37
BMP388_REG_ADD_P2_LSB = 0x38
BMP388_REG_ADD_P2_MSB = 0x39
BMP388_REG_ADD_P3 = 0x3A
BMP388_REG_ADD_P4 = 0x3B
BMP388_REG_ADD_P5_LSB = 0x3C
BMP388_REG_ADD_P5_MSB = 0x3D
BMP388_REG_ADD_P6_LSB = 0x3E
BMP388_REG_ADD_P6_MSB = 0x3F
BMP388_REG_ADD_P7 = 0x40
BMP388_REG_ADD_P8 = 0x41
BMP388_REG_ADD_P9_LSB = 0x42
BMP388_REG_ADD_P9_MSB = 0x43
BMP388_REG_ADD_P10 = 0x44
BMP388_REG_ADD_P11 = 0x45

class BMP388(object):

    """docstring for BMP388"""

    def __init__(self, address=I2C_ADD_BMP388):
        self._address = address
        self._bus = smbus.SMBus(0x01)

        # Load calibration values.

        if self._read_byte(BMP388_REG_ADD_WIA) == BMP388_REG_VAL_WIA:
            print("Pressure sersor is BMP388!\r\n")
            u8RegData = self._read_byte(BMP388_REG_ADD_STATUS)
            if u8RegData & BMP388_REG_VAL_CMD_RDY:
                self._write_byte(BMP388_REG_ADD_CMD,
                                 BMP388_REG_VAL_SOFT_RESET)
                time.sleep(0.01)
        else:
            print ("Pressure sersor NULL!\r\n")
        self._write_byte(BMP388_REG_ADD_PWR_CTRL,
                         BMP388_REG_VAL_PRESS_EN
                         | BMP388_REG_VAL_TEMP_EN
                         | BMP388_REG_VAL_NORMAL_MODE)
        self._load_calibration()

    def _read_byte(self, cmd):
        return self._bus.read_byte_data(self._address, cmd)

    def _read_s8(self, cmd):
        result = self._read_byte(cmd)
        if result > 128:
            result -= 256
        return result

    def _read_u16(self, cmd):
        LSB = self._bus.read_byte_data(self._address, cmd)
        MSB = self._bus.read_byte_data(self._address, cmd + 0x01)
        return (MSB << 0x08) + LSB

    def _read_s16(self, cmd):
        result = self._read_u16(cmd)
        if result > 32767:
            result -= 65536
        return result

    def _write_byte(self, cmd, val):
        self._bus.write_byte_data(self._address, cmd, val)

    def _load_calibration(self):
        print ("_load_calibration\r\n")
        self.T1 = self._read_u16(BMP388_REG_ADD_T1_LSB)
        self.T2 = self._read_u16(BMP388_REG_ADD_T2_LSB)
        self.T3 = self._read_s8(BMP388_REG_ADD_T3)
        self.P1 = self._read_s16(BMP388_REG_ADD_P1_LSB)
        self.P2 = self._read_s16(BMP388_REG_ADD_P2_LSB)
        self.P3 = self._read_s8(BMP388_REG_ADD_P3)
        self.P4 = self._read_s8(BMP388_REG_ADD_P4)
        self.P5 = self._read_u16(BMP388_REG_ADD_P5_LSB)
        self.P6 = self._read_u16(BMP388_REG_ADD_P6_LSB)
        self.P7 = self._read_s8(BMP388_REG_ADD_P7)
        self.P8 = self._read_s8(BMP388_REG_ADD_P8)
        self.P9 = self._read_s16(BMP388_REG_ADD_P9_LSB)
        self.P10 = self._read_s8(BMP388_REG_ADD_P10)
        self.P11 = self._read_s8(BMP388_REG_ADD_P11)

        # print(self.T1)
        # print(self.T2)
        # print(self.T3)
        # print(self.P1)
        # print(self.P2)
        # print(self.P3)
        # print(self.P4)
        # print(self.P5)
        # print(self.P6)
        # print(self.P7)
        # print(self.P8)
        # print(self.P9)
        # print(self.P10)
        # print(self.P11)

    def compensate_temperature(self, adc_T):
        partial_data1 = adc_T - 256 * self.T1
        partial_data2 = self.T2 * partial_data1
        partial_data3 = partial_data1 * partial_data1
        partial_data4 = partial_data3 * self.T3
        partial_data5 = partial_data2 * 262144 + partial_data4
        partial_data6 = partial_data5 / 4294967296
        self.T_fine = partial_data6
        comp_temp = partial_data6 * 25 / 16384
        return comp_temp

    def compensate_pressure(self, adc_P):
        partial_data1 = self.T_fine * self.T_fine
        partial_data2 = partial_data1 / 0x40
        partial_data3 = partial_data2 * self.T_fine / 256
        partial_data4 = self.P8 * partial_data3 / 0x20
        partial_data5 = self.P7 * partial_data1 * 0x10
        partial_data6 = self.P6 * self.T_fine * 4194304
        offset = self.P5 * 140737488355328 + partial_data4 \
            + partial_data5 + partial_data6

        partial_data2 = self.P4 * partial_data3 / 0x20
        partial_data4 = self.P3 * partial_data1 * 0x04
        partial_data5 = (self.P2 - 16384) * self.T_fine * 2097152
        sensitivity = (self.P1 - 16384) * 70368744177664 \
            + partial_data2 + partial_data4 + partial_data5

        partial_data1 = sensitivity / 16777216 * adc_P
        partial_data2 = self.P10 * self.T_fine
        partial_data3 = partial_data2 + 65536 * self.P9
        partial_data4 = partial_data3 * adc_P / 8192
        partial_data5 = partial_data4 * adc_P / 512
        partial_data6 = adc_P * adc_P
        partial_data2 = self.P11 * partial_data6 / 65536
        partial_data3 = partial_data2 * adc_P / 128
        partial_data4 = offset / 0x04 + partial_data1 + partial_data5 \
            + partial_data3
        comp_press = partial_data4 * 25 / 1099511627776
        return comp_press

    def get_temperature_and_pressure_and_altitude(self):
        """Returns pressure in Pa as double. Output value of "6386.2"equals 96386.2 Pa = 963.862 hPa."""

        xlsb = self._read_byte(BMP388_REG_ADD_TEMP_XLSB)
        lsb = self._read_byte(BMP388_REG_ADD_TEMP_LSB)
        msb = self._read_byte(BMP388_REG_ADD_TEMP_MSB)
        adc_T = (msb << 0x10) + (lsb << 0x08) + xlsb
        temperature = self.compensate_temperature(adc_T)
        xlsb = self._read_byte(BMP388_REG_ADD_PRESS_XLSB)
        lsb = self._read_byte(BMP388_REG_ADD_PRESS_LSB)
        msb = self._read_byte(BMP388_REG_ADD_PRESS_MSB)

        adc_P = (msb << 0x10) + (lsb << 0x08) + xlsb
        pressure = self.compensate_pressure(adc_P)
        altitude = 4433000 * (0x01 - pow(pressure / 100.0 / 101325.0,
                              0.1903))

        return (temperature, pressure, altitude)

def kalmanFilterY ( accAngle, gyroRate, DT):
    y=0.0
    S=0.0

    global KFangleY
    global Q_angle
    global Q_gyro
    global y_bias
    global YP_00
    global YP_01
    global YP_10
    global YP_11

    KFangleY = KFangleY + DT * (gyroRate - y_bias)

    YP_00 = YP_00 + ( - DT * (YP_10 + YP_01) + Q_angle * DT )
    YP_01 = YP_01 + ( - DT * YP_11 )
    YP_10 = YP_10 + ( - DT * YP_11 )
    YP_11 = YP_11 + ( + Q_gyro * DT )

    y = accAngle - KFangleY
    S = YP_00 + R_angle
    K_0 = YP_00 / S
    K_1 = YP_10 / S

    KFangleY = KFangleY + ( K_0 * y )
    y_bias = y_bias + ( K_1 * y )

    YP_00 = YP_00 - ( K_0 * YP_00 )
    YP_01 = YP_01 - ( K_0 * YP_01 )
    YP_10 = YP_10 - ( K_1 * YP_00 )
    YP_11 = YP_11 - ( K_1 * YP_01 )

    return KFangleY

def kalmanFilterX ( accAngle, gyroRate, DT):
    x=0.0
    S=0.0

    global KFangleX
    global Q_angle
    global Q_gyro
    global x_bias
    global XP_00
    global XP_01
    global XP_10
    global XP_11


    KFangleX = KFangleX + DT * (gyroRate - x_bias)

    XP_00 = XP_00 + ( - DT * (XP_10 + XP_01) + Q_angle * DT )
    XP_01 = XP_01 + ( - DT * XP_11 )
    XP_10 = XP_10 + ( - DT * XP_11 )
    XP_11 = XP_11 + ( + Q_gyro * DT )

    x = accAngle - KFangleX
    S = XP_00 + R_angle
    K_0 = XP_00 / S
    K_1 = XP_10 / S

    KFangleX = KFangleX + ( K_0 * x )
    x_bias = x_bias + ( K_1 * x )

    XP_00 = XP_00 - ( K_0 * XP_00 )
    XP_01 = XP_01 - ( K_0 * XP_01 )
    XP_10 = XP_10 - ( K_1 * XP_00 )
    XP_11 = XP_11 - ( K_1 * XP_01 )

    return KFangleX


gyroXangle = 0.0
gyroYangle = 0.0
gyroZangle = 0.0
CFangleX = 0.0
CFangleY = 0.0
CFangleXFiltered = 0.0
CFangleYFiltered = 0.0
kalmanX = 0.0
kalmanY = 0.0
oldXMagRawValue = 0
oldYMagRawValue = 0
oldZMagRawValue = 0
oldXAccRawValue = 0
oldYAccRawValue = 0
oldZAccRawValue = 0

a = datetime.datetime.now()



#Setup the tables for the mdeian filter. Fill them all with '1' so we dont get devide by zero error
acc_medianTable1X = [1] * ACC_MEDIANTABLESIZE
acc_medianTable1Y = [1] * ACC_MEDIANTABLESIZE
acc_medianTable1Z = [1] * ACC_MEDIANTABLESIZE
acc_medianTable2X = [1] * ACC_MEDIANTABLESIZE
acc_medianTable2Y = [1] * ACC_MEDIANTABLESIZE
acc_medianTable2Z = [1] * ACC_MEDIANTABLESIZE
mag_medianTable1X = [1] * MAG_MEDIANTABLESIZE
mag_medianTable1Y = [1] * MAG_MEDIANTABLESIZE
mag_medianTable1Z = [1] * MAG_MEDIANTABLESIZE
mag_medianTable2X = [1] * MAG_MEDIANTABLESIZE
mag_medianTable2Y = [1] * MAG_MEDIANTABLESIZE
mag_medianTable2Z = [1] * MAG_MEDIANTABLESIZE

IMU.detectIMU()     #Detect if BerryIMU is connected.
if(IMU.BerryIMUversion == 99):
    print(" No BerryIMU found... exiting ")
    sys.exit()
IMU.initIMU()       #Initialise the accelerometer, gyroscope and compass

#intializing the pressure class 
bmp388 = BMP388()

while True:

    #Read the accelerometer,gyroscope and magnetometer values
    ACCx = IMU.readACCx()
    ACCy = IMU.readACCy()
    ACCz = IMU.readACCz()
    GYRx = IMU.readGYRx()
    GYRy = IMU.readGYRy()
    GYRz = IMU.readGYRz()
    MAGx = IMU.readMAGx()
    MAGy = IMU.readMAGy()
    MAGz = IMU.readMAGz()


    #Apply compass calibration
    MAGx -= (magXmin + magXmax) /2
    MAGy -= (magYmin + magYmax) /2
    MAGz -= (magZmin + magZmax) /2


    ##Calculate loop Period(LP). How long between Gyro Reads
    b = datetime.datetime.now() - a
    a = datetime.datetime.now()
    LP = b.microseconds/(1000000*1.0)
    outputString = "Loop Time %5.2f " % ( LP )



    ###############################################
    #### Apply low pass filter ####
    ###############################################
    MAGx =  MAGx  * MAG_LPF_FACTOR + oldXMagRawValue*(1 - MAG_LPF_FACTOR);
    MAGy =  MAGy  * MAG_LPF_FACTOR + oldYMagRawValue*(1 - MAG_LPF_FACTOR);
    MAGz =  MAGz  * MAG_LPF_FACTOR + oldZMagRawValue*(1 - MAG_LPF_FACTOR);
    ACCx =  ACCx  * ACC_LPF_FACTOR + oldXAccRawValue*(1 - ACC_LPF_FACTOR);
    ACCy =  ACCy  * ACC_LPF_FACTOR + oldYAccRawValue*(1 - ACC_LPF_FACTOR);
    ACCz =  ACCz  * ACC_LPF_FACTOR + oldZAccRawValue*(1 - ACC_LPF_FACTOR);

    oldXMagRawValue = MAGx
    oldYMagRawValue = MAGy
    oldZMagRawValue = MAGz
    oldXAccRawValue = ACCx
    oldYAccRawValue = ACCy
    oldZAccRawValue = ACCz

    #########################################
    #### Median filter for accelerometer ####
    #########################################
    # cycle the table
    for x in range (ACC_MEDIANTABLESIZE-1,0,-1 ):
        acc_medianTable1X[x] = acc_medianTable1X[x-1]
        acc_medianTable1Y[x] = acc_medianTable1Y[x-1]
        acc_medianTable1Z[x] = acc_medianTable1Z[x-1]

    # Insert the lates values
    acc_medianTable1X[0] = ACCx
    acc_medianTable1Y[0] = ACCy
    acc_medianTable1Z[0] = ACCz

    # Copy the tables
    acc_medianTable2X = acc_medianTable1X[:]
    acc_medianTable2Y = acc_medianTable1Y[:]
    acc_medianTable2Z = acc_medianTable1Z[:]

    # Sort table 2
    acc_medianTable2X.sort()
    acc_medianTable2Y.sort()
    acc_medianTable2Z.sort()

    # The middle value is the value we are interested in
    ACCx = acc_medianTable2X[int(ACC_MEDIANTABLESIZE/2)];
    ACCy = acc_medianTable2Y[int(ACC_MEDIANTABLESIZE/2)];
    ACCz = acc_medianTable2Z[int(ACC_MEDIANTABLESIZE/2)];



    #########################################
    #### Median filter for magnetometer ####
    #########################################
    # cycle the table
    for x in range (MAG_MEDIANTABLESIZE-1,0,-1 ):
        mag_medianTable1X[x] = mag_medianTable1X[x-1]
        mag_medianTable1Y[x] = mag_medianTable1Y[x-1]
        mag_medianTable1Z[x] = mag_medianTable1Z[x-1]

    # Insert the latest values
    mag_medianTable1X[0] = MAGx
    mag_medianTable1Y[0] = MAGy
    mag_medianTable1Z[0] = MAGz

    # Copy the tables
    mag_medianTable2X = mag_medianTable1X[:]
    mag_medianTable2Y = mag_medianTable1Y[:]
    mag_medianTable2Z = mag_medianTable1Z[:]

    # Sort table 2
    mag_medianTable2X.sort()
    mag_medianTable2Y.sort()
    mag_medianTable2Z.sort()

    # The middle value is the value we are interested in
    MAGx = mag_medianTable2X[int(MAG_MEDIANTABLESIZE/2)];
    MAGy = mag_medianTable2Y[int(MAG_MEDIANTABLESIZE/2)];
    MAGz = mag_medianTable2Z[int(MAG_MEDIANTABLESIZE/2)];



    #Convert Gyro raw to degrees per second
    rate_gyr_x =  GYRx * G_GAIN
    rate_gyr_y =  GYRy * G_GAIN
    rate_gyr_z =  GYRz * G_GAIN


    #Calculate the angles from the gyro.
    gyroXangle+=rate_gyr_x*LP
    gyroYangle+=rate_gyr_y*LP
    gyroZangle+=rate_gyr_z*LP

    #Convert Accelerometer values to degrees
    AccXangle =  (math.atan2(ACCy,ACCz)*RAD_TO_DEG)
    AccYangle =  (math.atan2(ACCz,ACCx)+M_PI)*RAD_TO_DEG


    #Change the rotation value of the accelerometer to -/+ 180 and
    #move the Y axis '0' point to up.  This makes it easier to read.
    if AccYangle > 90:
        AccYangle -= 270.0
    else:
        AccYangle += 90.0



    #Complementary filter used to combine the accelerometer and gyro values.
    CFangleX=AA*(CFangleX+rate_gyr_x*LP) +(1 - AA) * AccXangle
    CFangleY=AA*(CFangleY+rate_gyr_y*LP) +(1 - AA) * AccYangle

    #Kalman filter used to combine the accelerometer and gyro values.
    kalmanY = kalmanFilterY(AccYangle, rate_gyr_y,LP)
    kalmanX = kalmanFilterX(AccXangle, rate_gyr_x,LP)

    #Calculate heading
    heading = 180 * math.atan2(MAGy,MAGx)/M_PI

    #Only have our heading between 0 and 360
    if heading < 0:
        heading += 360

    ####################################################################
    ###################Tilt compensated heading#########################
    ####################################################################
    #Normalize accelerometer raw values.
    accXnorm = ACCx/math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)
    accYnorm = ACCy/math.sqrt(ACCx * ACCx + ACCy * ACCy + ACCz * ACCz)


    #Calculate pitch and roll
    pitch = math.asin(accXnorm)
    roll = -math.asin(accYnorm/math.cos(pitch))


    #Calculate the new tilt compensated values
    #The compass and accelerometer are orientated differently on the the BerryIMUv1, v2 and v3.
    #This needs to be taken into consideration when performing the calculations

    #X compensation
    if(IMU.BerryIMUversion == 1 or IMU.BerryIMUversion == 3):            #LSM9DS0 and (LSM6DSL & LIS2MDL)
        magXcomp = MAGx*math.cos(pitch)+MAGz*math.sin(pitch)
    else:                                                                #LSM9DS1
        magXcomp = MAGx*math.cos(pitch)-MAGz*math.sin(pitch)

    #Y compensation
    if(IMU.BerryIMUversion == 1 or IMU.BerryIMUversion == 3):            #LSM9DS0 and (LSM6DSL & LIS2MDL)
        magYcomp = MAGx*math.sin(roll)*math.sin(pitch)+MAGy*math.cos(roll)-MAGz*math.sin(roll)*math.cos(pitch)
    else:                                                                #LSM9DS1
        magYcomp = MAGx*math.sin(roll)*math.sin(pitch)+MAGy*math.cos(roll)+MAGz*math.sin(roll)*math.cos(pitch)





    #Calculate tilt compensated heading
    tiltCompensatedHeading = 180 * math.atan2(magYcomp,magXcomp)/M_PI

    if tiltCompensatedHeading < 0:
        tiltCompensatedHeading += 360


    ##################### END Tilt Compensation ########################
    #calculating the G forces on all axis
    yG = (ACCx * 0.244)/1000
    xG = (ACCy * 0.244)/1000
    zG = (ACCz * 0.244)/1000
    # retrieving the temp, alt and pressure
    temperature,pressure,altitude = bmp388.get_temperature_and_pressure_and_altitude()

    try:
        line = sio.readline()
        # ct stores current time 
        ct = datetime.datetime.now() 
        # print(ct) 
        # print(line)
        msg = pynmea2.parse(line)
        # print("**************** line ***************")
        # print(line)
        # print("**************** Msg ***************")
        # print(msg)
        
        if(line.find('RMC') > 0):
            # print("**************** RMC ***************")
            # print(msg)
            # print("Date : ", msg.datestamp)
            # print("Time : ", msg.timestamp)
            #oled.text(str(msg.datestamp) + str(msg.timestamp) , 3)  # Line 1
            # print("Latitude : ", msg.latitude)
            # print("Latitude Direction: ",msg.lat_dir)
            # print("Longitude : ", msg.longitude)
            # print("Longitude Direction : ",msg.lon_dir)

            #oled.text('{:.5}'.format(msg.latitude)+","+'{:.5}'.format(msg.longitude), 4)  # Line 2
            # print("Speed : ", msg.spd_over_grnd)
            RMC_speed = msg.spd_over_grnd
            if type(RMC_speed) is not float:
                RMC_speed = 0.0
            GPS_datestamp = str(msg.datestamp)
            GPS_timestamp = str(msg.timestamp)
            GPS_lat = msg.latitude
            GPS_lat_dir = msg.lat_dir
            GPS_lon = msg.longitude
            GPS_lon_dir = msg.lon_dir
            
        if(line.find('GGA') > 0):
            # print("**************** GGA ***************")
            # print(repr(msg.lat))
            # print("Timestamp: {0} -- Lat: {1} {2} -- Lon: {3} {4} -- Altitude: {5} {6} -- Satellites: {7}".format(msg.timestamp,msg.latitude,msg.lat_dir,msg.longitude,msg.lon_dir,msg.altitude,msg.altitude_units,msg.num_sats))
            GGA_altitude = msg.altitude
            GGA_sat_num =  msg.num_sats
        
        # oled.text("A:"+str(GGA_altitude)+"Sa:"+str(GGA_sat_num)+"Sp:"+str(RMC_speed), 5)  # Line 3
        gpsText = "A:"+str(GGA_altitude)+"Sa:"+str(GGA_sat_num)+"Sp:"+str(RMC_speed)
        # print(gpsText)
    except serial.SerialException as e:
        print('Device error: {}'.format(e))
        break
    except pynmea2.ParseError as e:
        print('Parse error: {}'.format(e))
        continue

    
    #sequence - timestamp,accelerometer, gyroscope, Complimentary filter, Compass heading, Kalman filter, G forces, Temp, pressure, altitide
    labels = "System timestamp,ACCX Angle,ACCY Angle,GRYX Angle,GYRY Angle,GYRZ Angle,CFangleX Angle,CFangleY Angle,HEADING,tiltCompensatedHeading,kalmanX,kalmanY,xG,yG,ZG,temp, pressure,altitude,GPS_datestamp,GPS_timestamp,GPS_lat,GPS_lat_dir,GPS_lon,GPS_lon_dir,RMC_speed"

    # outputString = "%5.2f,%5.2f,%5.2f,%5.2f,%5.2f,%5.2f,%5.2f,%5.2f,%5.2f,%5.2f,%5.2f,%f,%f,%f,%.1f,%.2f,%.2f" % (AccXangle, AccYangle,gyroXangle,gyroYangle,gyroZangle,CFangleX,CFangleY,heading,tiltCompensatedHeading,kalmanX,kalmanY,yG,xG,zG,temperature/100.0,pressure/100.0,altitude/100.0)
    #outputString2 = '{0:5.2f},{0:5.2f},{0:5.2f},{0:5.2f},{0:5.2f},{0:5.2f},{0:5.2f},{0:5.2f},{0:5.2f},{},{},{},{:.1f},{:.2f},{:.2f}'.format(AccXangle, AccYangle,gyroXangle,gyroYangle,gyroZangle,CFangleX,CFangleY,heading,tiltCompensatedHeading,kalmanX,kalmanY,yG,xG,zG,temperature/100.0,pressure/100.0,altitude/100.0)
    # outputStringNew = '{0:5.2f},{0:5.2f},'.format(AccXangle, AccYangle)
    # outputStringNew += '{0:5.2f},{0:5.2f},{0:5.2f},'.format(gyroXangle,gyroYangle,gyroZangle)
    # outputStringNew += '{0:5.2f},{0:5.2f},'.format(CFangleX,CFangleY)
    # outputStringNew += '{0:5.2f},{0:5.2f},'.format(heading,tiltCompensatedHeading)
    # outputStringNew += '{0:5.2f},{0:5.2f},'.format(kalmanX,kalmanY)
    # outputStringNew += '{},{},{},'.format(xG,yG,zG)
    # outputStringNew += '{:.1f},{:.2f},{:.2f},'.format(temperature/100.0,pressure/100.0,altitude/100.0)
    # outputStringNew += "{},{},{},{},{},{},{}".format(GPS_datestamp,GPS_timestamp,GPS_lat,GPS_lat_dir,GPS_lon,GPS_lon_dir,RMC_speed)
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    # print(timestamp+","+outputStringNew)    
    # print(timestamp,outputString)
    # logging.info(outputStringNew)

    #preparing for the influx entry
    recorded_timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f').isoformat()

    json_body = [
            {
                "measurement": "Car_GPS_IMU_Data",
                "tags": {
                    "trip_type": trip_type,
                    "vehicle_type": vehicle_type,
                    "model" : model,
                    "brand" : brand,
                    "seats" : seats,
                    "mode": mode,
                    "logger_location" : logger_location,
                    "owner":owner,
                    "tripID" : tripID,
                    "trip_desc" : trip_desc
                },
                "time": recorded_timestamp,#time.time_ns(), #int(recorded_timestamp.timestamp()*1000), #take system time stamp in dd-mm-yy h:m:s.ms format and convert into epocs i.e. time since 01 01 1970
                "fields": {
                    "ACCX_Angle" : float(AccXangle),
                    "ACCY_Angle" : float(AccYangle),
                    "GRYX_Angle" : float(gyroXangle),
                    "GYRY_Angle" : float(gyroYangle),
                    "GYRZ_Angle" : float(gyroZangle),
                    "CFangleX_Angle" : float(CFangleX),
                    "CFangleY_Angle" : float(CFangleY),
                    "HEADING" : float(heading),
                    "tiltCompensatedHeading" : float(tiltCompensatedHeading),
                    "kalmanX" : float(kalmanX),
                    "kalmanY" : float(kalmanY),
                    "xG" : float(xG),
                    "yG" : float(yG),
                    "ZG" : float(zG),
                    "temperature" : float(temperature/100.0), 
                    "pressure" : float(pressure/100.0),
                    "altitude" : float(altitude/100.0),
                    "GPS_datestamp" : GPS_datestamp,
                    "GPS_timestamp" : GPS_timestamp,
                    "GPS_lat" :float(GPS_lat),
                    "GPS_lat_dir" : GPS_lat_dir,
                    "GPS_lon" : float(GPS_lon),
                    "GPS_lon_dir" :GPS_lon_dir,
                    "RMC_speed" : float(RMC_speed)
                }
            }
        ]
    print(json_body)
    #writing record to influx db
    influx_client.write_points(json_body)
    #slow program down a bit, makes the output more readable
    # time.sleep(0.03)

