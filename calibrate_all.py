import os
import glob


#18,20,23,24
data_path = '/home/cta/mountpoints/ecap-l055/home/cta/Documents/matthias/sine_data/'   #if pi4025 /home/cta/pi4082/
cal_path  = '/home/cta/mountpoints/ecap-l005/home/cta/Software/TargetIO/script/SSTCAM-TM/ecap_qcam/calib_results/0019R/DC_TF/'
pedestal  = '0019R_amplitude_1500_ped.fits'
dc_tf     = '0019R_DC_TF_1500mV_ped.fits'
for filename in glob.glob(f'{data_path}/*r0.tio'):
    print(filename)

    os.system(f'apply_calibration -i {filename} -p {cal_path}{pedestal} --tf {cal_path}{dc_tf}')
