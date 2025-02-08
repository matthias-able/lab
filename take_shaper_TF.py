'''
 Python script that controls and collects data from various devices (an oscilloscope and a function generator) to measure and save waveform data across different voltage ranges for a specific channel on a given test module. Here's a compact summary of its functionality:

    The script initializes communication with an oscilloscope (TEK_MSO64B) and a function generator (Keysight 33600A) based on specified IP addresses and serial numbers.
    It sets up communication with a target module (connected to a test system) for device configuration and data acquisition.
    The user provides a channel number through command-line arguments, which is used to configure the oscilloscope and function generator for measurement.
    The script captures waveform data in three different voltage ranges: low, middle, and high, using the oscilloscope's readout capabilities while controlling the function generator's output.
    The data is saved in a specific directory based on the channel number, and the script generates plots for each voltage range, saving the data in .npy format.
'''
import numpy as np
import matplotlib.pyplot as plt
import sys
sys.path.append("/home/cta/Software/devices/Tektronix/MSO64B")
import mso64b
sys.path.append("/home/cta/Software/devices/Keysight/Keysight_33600A")
import keysight33600a
import time
import argparse
import os
import target_driver
import target_io


# Input Parameter: type channel you want to measure
parser = argparse.ArgumentParser()
parser.add_argument('channel', type=int)
args = parser.parse_args()	# Write all arguments to args
channel = str(args.channel)
print('channel: ' + channel)


# change name here!!
module_name             = "0020R"


"""
Presettings:
Ozi
50 Ohm DC coupling
250 MHz Bandwidth

Fkt Gen
Bust mode
arb wave
"""


# create data directory and set path to it
path = f'/home/cta/TM_test/matthias/shaper_TF/data/{module_name}'
try:
    path = os.path.join(path, channel)
    os.mkdir(path)
except:
    # path = path #overwrite files
    print('Channel already exists!!!')
    exit()
path += '/'


# Connect devices
oszi = mso64b.TEK_MSO64B(ip_address="10.202.33.43")
fkt_gen = keysight33600a.KEY33600A(myserial="MY59000990")


# ----------------------
# Communicate with TARGET
# ----------------------


my_ip                   = "192.168.12.1"#os.popen("hostname -I").read().strip()   #TARGET C "192.168.12.1"   #maybe 192.168.0.2
module_ip               = "192.168.12.173"              #"192.168.0.124" | SN0001 192.168.0.125              #TARGET C  "192.168.12.173"
initialize              = True

firmware_path           = "/home/cta/Software/TargetDriver/config/"
module_def              = "{}SSTCAM_MSA_FPGA_Firmware0xC0000009.def".format(firmware_path)
asic_def                = "{}CTC_ASIC.def".format(firmware_path)
trigger_asic_def        = "{}CT5TEA_ASIC.def".format(firmware_path)


module = target_driver.TargetModule(module_def, asic_def, trigger_asic_def, 0)

if initialize == True:
    ret=module.EstablishSlowControlLink(my_ip, module_ip)
    print("EstablishSlowControlLink",ret,"(should be 0)")

    if ret!=0:
        print("That did not work...")
        sys.exit()

    module.Initialise()
    module.EnableDLLFeedback()
    print ("module initialized")

else:
    ret=module.ReconnectToServer(my_ip, 8200, module_ip, 8105)
    print("ReconnectToServer",ret,"(should be 0)")

    if ret!=0:
        print("That did not work...")
        sys.exit()


ret, fw = module.ReadRegister(0)
print ("Firmware version: {:x}".format(fw))

ret, lsw = module.ReadSetting("SerialNumLSW")
ret, msw = module.ReadSetting("SerialNumMSW")
print("serial number Pri: {:x} {:x}".format(msw,lsw))

ret, lsw_aux = module.ReadSetting("SerialNumLSW_Aux")
ret, msw_aux = module.ReadSetting("SerialNumMSW_Aux")
print("serial number Aux: {:x} {:x}".format(msw_aux,lsw_aux))

ret, lsw_pow = module.ReadSetting("SerialNumLSW_Pow")
ret, msw_pow = module.ReadSetting("SerialNumLSW_Pow")
print("serial number Power: {:x} {:x}".format(msw_pow,lsw_pow))


#Package Management
nblocks = 4
kNPacketsPerEvent = 4	#4     8
kBufferDepth =  1000      #50000

module.WriteSetting("NumberOfBlocks", nblocks-1)
module.WriteSetting("MaxChannelsInPacket", int(64 /kNPacketsPerEvent))
kPacketSize = target_driver.DataPacket_CalculatePacketSizeInBytes(int(64/kNPacketsPerEvent), 32 * (nblocks))
print("nblocks: ",nblocks,"kNPacketsPerEvent: ",kNPacketsPerEvent,"kBufferDepth: ",kBufferDepth)


#Set Modul
for asic in range(4):
    module.WriteSetting("EnableChannelsASIC{}".format(asic), 0xffff)


#Power for Shaper
module.WriteSetting("PowerUp4V7", 1)
module.WriteSetting("PowerUp5V2", 1)
module.WriteSetting("PowerUpBuffer", 1)
module.WriteSetting("PowerUpShaper", 1)
module.WriteSetting("DoneSignalSpeedUp",0)


print ("\nEnable Slow ADCs")
module.WriteSetting("SlowADCEnable_Primary",1)
module.WriteSetting("SlowADCEnable_Aux",1)
module.WriteSetting("SlowADCEnable_Power",1)

#Set Pedestral
for asic in range(1):
        for chn in range(16):
            module.WriteTriggerASICSetting("Vped_{}".format(chn), asic, 1200, True)


#----------------
# methods for data aqisition
#----------------

def aquire_low_range():

    amplitude = np.arange(105, 310, 10)

    # config oszilloscope
    oszi.config(channels=[1,0,1,0])
    oszi.set_average(samples=50)
    oszi.set_trigger(channel=3,trgV=2)
    # asic 0
    if int(channel) < 16:
        oszi.set_readout(channel=1, xdiv=40e-9, xoffs=0., ydiv=.02, yoffs=-.73, datawidth=2)
        # oszi.set_readout(channel=1, xdiv=40e-9, xoffs=0., ydiv=.02, yoffs=-.63, datawidth=2) # module 0020R

    else:
    # asic 1
        oszi.set_readout(channel=1, xdiv=40e-9, xoffs=0., ydiv=.02, yoffs=-.85, datawidth=2)

    data = []

    for i in amplitude:
        # config function generator (set amplitude, waveform is pre defined)
        fkt_gen.ampl1(high=-.1,low=-i*1e-3)
        fkt_gen.sync()
        fkt_gen.out2on()
        fkt_gen.out1on()
        time.sleep(.05)

        data.append(oszi.read_aver_wave(channel=1))
        plt.plot(np.linspace(0,2500, 2500), np.array(data[-1]), label = i)

    plt.legend()
    plt.savefig(f'{path}chn_{channel}_VoltageRangeLow')
    plt.close()
    data = np.array(data)
    np.save(f'{path}chn_{channel}_VoltageRangeLow', data)
    print("low voltage range data saved")
    print(data.shape)
    return 1


def aquire_middle_range():

    amplitude = np.arange(320, 2020, 20)
    # config oszilloscope
    oszi.config(channels=[1,0,1,0])
    oszi.set_average(samples=50)
    oszi.set_trigger(channel=3,trgV=2)
    oszi.set_readout(channel=1, xdiv=40e-9, xoffs=0., ydiv=.2, yoffs=-1.4, datawidth=2)

    data = []

    for i in amplitude:
        # config function generator (set amplitude, waveform is pre defined)
        fkt_gen.ampl1(high=-.1,low=-i*1e-3)
        fkt_gen.sync()
        fkt_gen.out2on()
        fkt_gen.out1on()
        time.sleep(.05)

        data.append(oszi.read_aver_wave(channel=1))
        plt.plot(np.linspace(0,2500, 2500), np.array(data[-1]), label = i)


    plt.legend()
    plt.savefig(f'{path}chn_{channel}_VoltageRangeMiddle')
    plt.close()
    data = np.array(data)
    np.save(f'{path}chn_{channel}_VoltageRangeMiddle', data)
    print("middle voltage range data saved")
    return 1


def aquire_high_range():

    #amplitude = np.arange(2050, 5000, 50) since splitter TF only up to 3V
    amplitude = np.arange(2050, 3000, 50)

    # config oszilloscope
    oszi.config(channels=[1,0,1,0])
    oszi.set_average(samples=50)
    oszi.set_trigger(channel=3,trgV=2)
    oszi.set_readout(channel=1, xdiv=40e-9, xoffs=0., ydiv=.2, yoffs=-1.4, datawidth=2)

    data = []

    for i in amplitude:
        # config function generator (set amplitude, waveform is pre defined)
        fkt_gen.ampl1(high=-.1,low=-i*1e-3)
        fkt_gen.sync()
        fkt_gen.out2on()
        fkt_gen.out1on()
        time.sleep(.05)

        data.append(oszi.read_aver_wave(channel=1))
        plt.plot(np.linspace(0,2500, 2500), np.array(data[-1]), label = i)


    plt.legend()
    plt.savefig(f'{path}chn_{channel}_VoltageRangeHigh')
    data = np.array(data)
    np.save(f'{path}chn_{channel}_VoltageRangeHigh', data)
    print("high voltage range data saved")
    return 1


aquire_low_range()
aquire_middle_range()
aquire_high_range()

fkt_gen.close()
oszi.close()
