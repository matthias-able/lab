import time
import binascii
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
import pyvisa as visa

class AWG4022:

    def __init__(self,remote_ip="10.202.33.23",reset=False):
        rm = visa.ResourceManager("@py")
        #rm = visa.ResourceManager()
        self.pg=rm.open_resource("TCPIP::{}::INSTR".format(remote_ip))
        #self.pg.read_termination="\n"
        #self.pg.write_termination="\n"
        #self.pg.timeout=2000 #0.5s
        self.pgID = self.query("*IDN?").strip()
        if (self.pgID != "ACTIVE TECHNOLOGIES,AT-AFG-RIDER-4022,255B0051,SCPI:99.0,SV:1.0.0.0"):
            print("Wrong device",self.pgID)
            sys.exit()
        else :
            #self.write("*RST")
            print("Connected to",self.pgID)
        self.pgAMP=[0.0,0.0]
        self.pgFREQ=[0.0,0.0]
        self.pgOFF=[0.0,0.0]
        self.pgAMP[0]=self.query("SOUR1:VOLT?").strip()[:-3]
        self.pgAMP[1]=self.query("SOUR2:VOLT?").strip()[:-3]
        self.pgOFF[0]=self.query("SOUR1:VOLT:OFFS?").strip()
        self.pgOFF[1]=self.query("SOUR2:VOLT:OFFS?").strip()
        self.pgFREQ[1]=self.query("SOUR1:FREQ?").strip()
        self.pgFREQ[1]=self.query("SOUR2:FREQ?").strip()
        print("Amplitude (V):",self.pgAMP)
        print("Offset (V):",self.pgOFF)
        print("Frequency (Hz):",self.pgFREQ)
        self.pgOP="STOP"
        self.write("AFGC: STOP")
        #if int(self.query("AFGC:STAT?").strip())!=0:
        #    print("AFG not stopped")
        #    sys.exit(-1)
        self.write("OUTP1:IMP 50")
        if int(self.query("OUTP1:IMP?").strip())!=50:
            print("Impedance not set correct")
            sys.exit(-1)
        self.write("OUTP2:IMP 50")
        if int(self.query("OUTP2:IMP?").strip())!=50:
            print("Impedance not set correct")
            sys.exit(-1)

    def close(self):
        self.pg.close()
        time.sleep(.3)
        return 1

    def query(self,cmd,delay=0):
        return self.pg.query(cmd,delay=delay)

    def write(self,cmd):
        return self.pg.write(cmd)

    def external_ref(self,enable='True',freq=10):
        if freq != 10:
            answ=input("Ref clock really not 10MHz? Y for continue: ")
            if answ !="Y":
                return -1
        if enable:
            self.write("ROSC:SOUR EXT")
            self.write("ROSC:FREQ {}".format(freq))
        else:
            self.write("ROSC:SOUR INT")
        return self.query("ROSC:SOUR?").strip()

    def set_pulse(self,chan=1,ampV=0.2,freq=25.,func="GAUS"):
        if chan > 2 or chan < 1:
            return -1
        if ampV < -5 or ampV > 5:
            return -1
        if freq < 0 or freq > 600:
            return -1
        self.write('SOUR{}:FUNC {}'.format(int(chan),func))
        self.write('SOUR{}:VOLT:HIGH {}'.format(int(chan),ampV))
        self.write('SOUR{}:VOLT:LOW {}'.format(int(chan),(-1)*ampV))
        self.pgAMP[chan-1]=ampV
        self.pgOFF[chan-1]=0.0
        self.write('SOUR{}:FREQ {}MHz'.format(int(chan),freq))
        self.pgFREQ[chan-1]=freq*1000000.
        return 1

    def set_sine(self,chan=1,ampV=0.2,offV=0.0,freq=25.,func="SIN"):
        if chan > 2 or chan < 1:
            return -1
        if ampV < -10 or ampV > 10:
            return -1
        if offV < -5 or offV > 5:
            return -1
        if freq < 0 or freq > 600:
            return -1

        self.write('SOUR{}:FUNC {}'.format(int(chan),func))
        self.write('SOUR{}:VOLT {}'.format(int(chan),ampV))
        self.write('SOUR{}:VOLT:OFFS {}'.format(int(chan),offV))
        self.pgAMP[chan-1]=ampV
        self.pgOFF[chan-1]=offV
        self.write('SOUR{}:FREQ {}MHz'.format(int(chan),freq))
        self.pgFREQ[chan-1]=freq*1000000.
        return 1

    def set_sine_train(self,chn=1,MHz=100,amp_mV=200,width_ns=400,rate_Hz=600, ncycles=10):
        self.pg_op("STOP")
        if chn > 2 or chn < 1:
            return -1
        if amp_mV < -5000 or amp_mV > 5000:
            return -1
        if MHz < 0 or MHz > 600:
            return -1
        self.write('SOUR{}:FUNC SIN'.format(int(chn)))
        self.write('SOUR{}:VOLT:HIGH {}'.format(int(chn),amp_mV*0.001))
        self.write('SOUR{}:VOLT:LOW {}'.format(int(chn),(-1)*amp_mV*0.001))
        self.pgAMP[chn-1]=amp_mV
        self.pgOFF[chn-1]=0.0
        self.write('SOUR{}:FREQ {}MHz'.format(int(chn),MHz))
        self.pgFREQ[chn-1]=MHz*1000000.

        self.write('SOUR{}:BURS:MODE TRIG'.format(chn))
        #ncycles = int(width_ns * MHz*0.001+0.5) + 1
        #print("ncycles: ", ncycles)
        self.write('SOUR{}:BURS:NCYC {}'.format(chn,ncycles))

        self.write('SOUR{}:BURS:STAT 1')
        print(self.query("SOUR{}:BURS:STAT?".format(chn)))

        self.write('TRIG:TIM {}s'.format(1/rate_Hz))
        self.write('TRIG:SOUR TIM')
        self.pg_op("START")
        return 1

    def set_trig_pulse(self,chn=2,amp_V=2.5,rate_Hz=600):
        self.write('SOUR{}:FUNC PULS'.format(int(chn)))
        self.write('SOUR{}:VOLT:HIGH {}'.format(int(chn),amp_V))
        self.write('SOUR{}:VOLT:LOW 0')

        self.write('SOUR{}:BURS:NCYC 1'.format(chn))

        self.write('SOUR{}:BURS ON')
        self.write('TRIG:TIM {}s'.format(1/rate_Hz))
        self.write('TRIG:SOUR TIM')
        return 1

    def set_pulsetirg(self):
        self.pg_op("STOP")
        self.write('SOUR1:BURS:MODE TRIG')
        #print(self.query('SOUR1:BURS:MODE?'))
        self.write('SOUR1:BURS:NCYC 1')
        #print(self.query('SOUR1:BURS:NCYC?'))
        self.write('SOUR1:BURS ON')
        #print(self.query('SOUR1:BURS?'))
        self.write('TRIG:TIM 100us')
        #print(self.query('TRIG:TIM?'))
        self.write('TRIG:SOUR TIM')
        #print(self.query('TRIG:SOUR?'))
        self.pg_op(self.pgOP)
        return 1

    def pg_op(self,startstop="START"):
        if startstop not in ["START","STOP"]:
            return -1
        self.pgOP=startstop
        return self.write('AFGC:{}'.format(startstop))

    def pg_out(self,chan=1,onoff="OFF"):
        if chan > 2 or chan < 1:
            return -1
        if onoff not in ["ON","OFF"]:
            return -1
        return self.write('OUTP{} {}'.format(int(chan),onoff))

    def set_freq(self,chan=1,freq=25.):
        if chan > 2 or chan < 1:
            return -1
        if freq < 0 or freq > 600:
            return -1
        self.pgFREQ[chan-1]=freq*1000000.
        self.write('SOUR{}:FREQ {}MHz'.format(int(chan),freq))
        #self.write('SOUR{}:VOLT:LOW {}'.format(int(chan),(-1)*self.pgAMP))
        #self.write('SOUR{}:VOLT:HIGH {}'.format(int(chan),self.pgAMP))

    def set_sinamp(self,chan=1,ampV=0.2,offV=0.0):
        if chan > 2 or chan < 1:
            return -1
        if ampV < -10 or ampV > 10:
            return -1
        if offV < -5 or offV > 5:
            return -1
        self.pgAMP[chan-1]=ampV
        self.pgOFF[chan-1]=offV
        self.write('SOUR{}:VOLT {}'.format(int(chan),ampV))
        self.write('SOUR{}:OFFS {}'.format(int(chan),offV))

    def set_pulseamp(self,chan=1,ampV=0.2):
        if chan > 2 or chan < 1:
            return -1
        if ampV < -5 or ampV > 5:
            return -1
        self.pgAMP[chan-1]=ampV
        self.write('SOUR{}:VOLT:LOW {}'.format(int(chan),(-1)*ampV))
        self.write('SOUR{}:VOLT:HIGH {}'.format(int(chan),ampV))

    def set_freq(self,MHz,chn=1):
        self.write('SOUR{}:FREQ {}MHz'.format(int(chn),MHz))
        return 1
#
# instr = AWG4022()
#
# instr.set_sine_train()
# instr.set_trig_pulse()
# instr.pg_op("START")
# chn =2
# print(instr.query("SOUR{}:BURS:STAT?".format(chn)))
# instr.query("SOUR{}:BURS:STAT?".format(chn))
# time.sleep(1)
# instr.pg_op("STOP")
# instr.close()
