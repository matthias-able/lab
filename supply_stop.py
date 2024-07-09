import sys
sys.path.append('/home/cta/TARGET_scripts/Devices')
import keysight33600a as key 

# -------------------------------
#  Configure function generator
# -------------------------------
dev_f=key.KEY33600A()

dev_f.out1off()
dev_f.out2off()

