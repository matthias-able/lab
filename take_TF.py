'''
Attenuation Linearity Measurement System
Developed a Python script to measure and analyze the linearity of an attenuator device. The program interfaces with a digital multimeter (DMM) and a USB-controlled attenuator to collect voltage data across a range of attenuation settings. Key features include:

    - Automated communication with hardware devices (DMM and attenuator) using serial and custom libraries.

    - Calculation of attenuation factors and conversion from dB to voltage ratios.

    - Statistical analysis of measured data, including mean and standard deviation.

    - Visualization of results using matplotlib, comparing measured data to an ideal linear reference.

    - Data saving and plotting functionality for further analysis.
'''
import numpy as np
import matplotlib.pyplot as plt
import sys
from time import sleep
import serial

sys.path.append('/home/cta/TARGET_scripts/Devices')
import dmm6500 as dmm  #multimeter



# -------------------
#    User Defines
# -------------------

# output path for files
path = '/home/cta/TM_test/attenuator_usb/'

# Input voltage (DC)
# Note: Double the FGen setting because of voltage div in oszi
input_voltage = 0.8

# Output file for plot
output_file = path + f'TF_attenuator_linear_{input_voltage}V.npy'



# -------------------
#    DMM Connection
# -------------------
# Connect to DMM
DMM = dmm.DMM6500(remote_ip="10.202.33.106")

# Number of measurements for each attenuation setting
NMeas = 10

# Initialise measurement buffer
DMM.init_vped_meas(NMeas,0.01)



# -------------------
#    Attenuator
# -------------------

# Open communication with the attenuator
att=serial.Serial('/dev/ttyACM2',timeout=0.25)  #or ACM2, check via dmesg


# Stuff taken from Leon

dB_array = np.arange(0, 63.5, 0.25) # 127, and there are not only 0.5-steps possible (leon att) but 0.25 (usb att)

def convert_dB_to_attFactor(dB):
    return 10**((1/20)*dB)



# -------------------
#    Take data
# -------------------
def fetch_data():
    data = []


    for dB_factor in dB_array:

        #sets attenuation to dB_factor in format att-003.33\r\n
        att.write(f'att-{dB_factor:06.2F}\r\n'.encode())


        while att.readline().decode() != 'attOK':
            sleep(0.01)

        # Start measurement
        DMM.write(':TRAC:CLE "volt"')
        DMM.write(':TRAC:TRIG "volt"')

        # Wait until the measurement is done
        while int(DMM.query(':TRAC:ACT? "volt"')) != int(NMeas):
            time.sleep(.01)

        factor = convert_dB_to_attFactor(dB_factor)

        # Read back the voltage
        tmp = DMM.dev.query_ascii_values(':TRAC:DATA? 1,{},"volt"'.format(int(NMeas)))
        data.append([factor, np.mean(tmp), np.std(tmp, ddof=1)])

        # Provide the user with some output
        print(' '*80, end='\r')
        print(f'Attenuation: {data[-1][0]:.2f}\t' +
              f'Voltage is {data[-1][1]*1e+3:.2f}+-{data[-1][2]:.2f} mV', end='\r' )


    print('\n Done!')
    data = np.array(data)
    np.save(output_file, data)

fetch_data()
att.close()
DMM.close()


# -------------------
#   Plotting area
# -------------------
input_voltage = 0.8
output_file = 'TF_attenuator_linear_0.8V.npy'
data = np.load(output_file)

fig, ax = plt.subplots(figsize=(8,5), nrows=2)
# ax[0].set_title(f'USB Attenuation Linearity for {input_voltage*1e+3}mV DC input')

# Plot the measurement results
ax[0].plot(input_voltage/data[:,0],
        data[:,1],
        marker = '.',
        markersize = 3,
        c = 'black',
        lw = 0,
        label = 'Measurement')


# Plot ideal linear relationship
ax[0].plot(input_voltage/data[:,0],
        input_voltage/data[:,0],
        c = 'red',
        lw = 1,
        alpha = 1,
        label = 'Linear reference')


ax[1].plot(input_voltage/data[:,0], input_voltage/data[:,0] - data[:,1], 'x')

#plt.xscale('log')
#plt.yscale('log')
#plt.ylim(1,1e+3)
#plt.xlim(1,1e+3)


ax[1].set_xlabel('Input Voltage in [V]')
ax[0].set_ylabel('Output Voltage in [V]')
ax[1].set_ylabel('Absolute Difference in [V]')
ax[0].legend(shadow=True, fancybox=True)
plt.tight_layout()

# Save figure as pdf and as png
plt.savefig(output_file[:-4] + 'Voltage' + '.pdf', bbox_inches='tight')
plt.savefig(output_file[:-4] + 'Voltage' + '.png', bbox_inches='tight')
plt.show()
plt.close()
