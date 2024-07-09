import sys
import target_driver
import numpy as np
sys.path.append('/home/cta/Software/TargetIO/script/SSTCAM-TM')
sys.path.append('/home/cta/TARGET_scripts/Devices')
# import keysight33600a as key  #fgenerator


#Log:
#Need pulse trains of sinewaves to avoid memory effects
#figure that out with keysight

#########################################################################
# VtrimT Scan -> Phase Measurement                                      #
#             -> Sync Fgen with TARGET                                  #
#                                                                       #
# Two Modes available:                                                  #
# - Hardsync trigger -> Not need for DC TF later as artefacts are the   #
#   same for each fit/phase                                             #
# - External Trigger -> Can use pulse trains to avoid memory effects,   #
#   but need for DC TF                                                  #
#                                                                       #
#  Use small amplitudes as 30mV as shapers has a lot of gain at 50 MHz  #
#  Attenuator preferable                                                #
#########################################################################


module_name             = "0019R"
temp                    = 23
# operational_pedestal    = 1500          #1500 standard -> need negative swing
# HiResMode               = False
# hardsync                = True
# hardsync_phase          = 25

# power_cycle             = False
# warmup_time             = 0
duration                = 2
trigger_rate            = 600           # Needs to be around 600 (expected trigger rate in camera) | Baseline shifts with trigger rate!


savepath                = "/home/cta/ecap-l005/TM_test/matthias/basetimecalibration"
filename                = "{}_squarewave_run1".format(module_name)
# Vped_TF                 = np.loadtxt("/home/cta/Software/TargetIO/script/SSTCAM-TM/operation_files/{}/VPED_TF_{}.txt".format(module_name,module_name))


# take_pedestal           = True         #useful for hardsync mode
# pedestal_duration       = 3
# pedestal_name           = "{}{}_sinewaves_ped_vtrim_r0.tio".format(savepath,module_name)


# CHECK_SYNC              = False         #If you want to check the TARGET 10MHz clock signal on a scope
# SSToutFB_Delay_set      = 58            # 58 standard
# VtrimT_set              = 1200          # 1200 before tuning standard
# VtrimT_minmax           = 200
# VtrimT_steps            = 20
# TriggerDelay            = 330           # 330 standard



my_ip                   = "192.168.12.1 "#os.popen("hostname -I").read().strip()   #TARGET C "192.168.12.1"   #maybe 192.168.0.2
module_ip               = "192.168.12.123"              #"192.168.0.124" | SN0001 192.168.0.125              #TARGET C  "192.168.12.173"
initialize              = True



firmware_path           = "/home/cta/Software/TargetDriver/config/"
module_def              = "{}SSTCAM_MSA_FPGA_Firmware0xC000000B.def".format(firmware_path)
asic_def                = "{}CTC_ASIC.def".format(firmware_path)
trigger_asic_def        = "{}CT5TEA_ASIC.def".format(firmware_path)



#Communicate with TARGET
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



module.WriteSetting("TACK_EnableTrigger", 0x0)

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
    module.WriteASICSetting("Isel", asic, 2500, True)
    module.WriteASICSetting("Vdischarge", asic, 350, True)
    module.WriteASICSetting("VtrimT", asic, 1150, True)
    print("ASIC {}:".format(asic))
    # print("Isel {}".format(tuning_config[asic]))
    # print("Vdischarge {}".format(tuning_config[asic+4]))
    # print("VtrimT {}\n".format(tuning_config[asic+8]))

    module.WriteASICSetting("SSToutFB_Delay", asic, SSToutFB_Delay_set, True) # standard value: 58
    
    # Set Pedestals to 750mV??????
    for chn in range(16):
            module.WriteTriggerASICSetting("Vped_{}".format(chn), asic, 1200, True)



#Get 10MHz Clock out of trigger out socket to sync with FGen
module.WriteSetting("Select_TrigOut",5)


#additional settings to make everything as realistic as possible
module.WriteSetting("PowerUp4V7", 1)
module.WriteSetting("PowerUp5V2", 1)
module.WriteSetting("PowerUpBuffer", 1)
module.WriteSetting("PowerUpShaper", 1)

print ("\nEnable Slow ADCs")
module.WriteSetting("SlowADCEnable_Primary",1)
module.WriteSetting("SlowADCEnable_Aux",1)
module.WriteSetting("SlowADCEnable_Power",1)

if HiResMode == True:
    module.WriteSetting('SSTIN_disable', 1)
else:
    module.WriteSetting('SSTIN_disable', 0)


module.WriteSetting("WilkinsonClockFreq", 3)




#trigger settings
module.WriteSetting("TriggerDelay", TriggerDelay)
module.WriteSetting("TACK_TriggerType", 0x0)
module.WriteSetting("TACK_TriggerMode", 0x0)
if hardsync == True:
    module.WriteSetting("ExtTriggerDirection", 0x1) # 1: hardsync
    module.WriteSetting("Hardsync_Phase",hardsync_phase)        # 600Hz = 1/((406+1) *4096ns)




# ### Take pedestals ###
# if take_pedestal:
#     if not os.path.isfile(pedestal_name):
#         print("Taking pedestal events")
#         # ## function gen off ##
#         # dev_f.out1off()

#         ## Create DataListener and Writer
#         listener = target_io.DataListener(kBufferDepth, kNPacketsPerEvent, kPacketSize)
#         listener.AddDAQListener(my_ip)
#         listener.StartListening()

#         ## Create writer and start watching ##
#         writer = target_io.EventFileWriter(pedestal_name, kNPacketsPerEvent, kPacketSize)
#         buf = listener.GetEventBuffer()
#         writer.StartWatchingBuffer(buf)

#         ## hardsync trigger ##
#         module.WriteSetting("ExtTriggerDirection", 1)
#         module.WriteSetting("TACK_EnableTrigger", 0x10000)
#         ## wait for data ##
#         time.sleep(pedestal_duration) # wait some time to accumulate data
#         ## stop taking data ##
#         writer.StopWatchingBuffer()
#         module.WriteSetting("TACK_EnableTrigger", 0)
#         module.WriteSetting("ExtTriggerDirection", 0)
#         writer.Close()
#         buf.Flush()
#         buf.ClearEvents()
# print("\n")






# ### Take and save sinewave data ###
# print("Taking sinewave events")

# # ## turn function gen on ##
# # dev_f.out1on()


#   ## Scan VtrimT ##
# print("Scanning VtrimT")
# for ivtrimt in range(VtrimT_set - VtrimT_minmax, VtrimT_set + VtrimT_minmax , VtrimT_steps):

#     print("Setting VtrimT to " + str(ivtrimt))
#     for asic in range(4):
#         module.WriteASICSetting("VtrimT", asic, ivtrimt, True) # standard value: 1100


#     ## Create DataListener and Writer ##
#     listener = target_io.DataListener(kBufferDepth, kNPacketsPerEvent, kPacketSize)
#     listener.AddDAQListener(my_ip)
#     listener.StartListening()
#     ## Create writer and start watching ##

#     writer = target_io.EventFileWriter("{}{}_{}_r0.tio".format(savepath,filename,ivtrimt), kNPacketsPerEvent, kPacketSize)
#     buf = listener.GetEventBuffer()
#     writer.StartWatchingBuffer(buf)
#     ## hardsync trigger ##
#     module.WriteSetting("ExtTriggerDirection", 1)
#     module.WriteSetting("TACK_EnableTrigger", 0x10000)
#     ## wait for data ##
#     time.sleep(duration) # wait some time to accumulate data
#     ## stop taking data ##
#     writer.StopWatchingBuffer()
#     module.WriteSetting("TACK_EnableTrigger", 0)
#     module.WriteSetting("ExtTriggerDirection", 0)
#     writer.Close()
#     buf.Flush()
#     buf.ClearEvents()
#     listener.StopListening()



# ### Turn everything off ###
# dev_f.out1off()

# module.CloseSockets()

# ### Pedestal correction ###
# if take_pedestal:
#     print("Apply pedestal correction")
#     generate_ped_checs = "generate_ped"
#     apply_calibration = "apply_calibration"
#     ## Generate pedestal file ##
#     sys_command = generate_ped_checs + " -i " + pedestal_name
#     print(sys_command)
#     os.system(sys_command)
#     ## Apply calibration ##
#     filenames = glob.glob("{}{}_*_r0.tio".format(savepath,filename))
#     for files in filenames:
#         sys_command = apply_calibration + " -i " + files + " -p " + pedestal_name[:-6] + "ped.tcal"
#         print(sys_command)
#         os.system(sys_command)

# print("Finished")
