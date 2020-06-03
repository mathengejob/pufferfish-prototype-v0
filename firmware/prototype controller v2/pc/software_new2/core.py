# set QT_API environment variable
import os 
os.environ["QT_API"] = "pyqt5"
import qtpy

# qt libraries
from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy.QtGui import *

import utils as utils
from _def import *

from queue import Queue
import time
import numpy as np
import pyqtgraph as pg
from datetime import datetime
from pathlib import Path

class ValveController(QObject):

    xPos = Signal(float)
    yPos = Signal(float)

    def __init__(self,microcontroller):
        QObject.__init__(self)
        self.microcontroller = microcontroller
        self.x_pos = 0
        self.y_pos = 0

    def move_x(self,delta):
        self.microcontroller.move_x(delta)
        self.x_pos = self.x_pos + delta
        self.xPos.emit(self.x_pos)
        QApplication.processEvents()
        #print(self.x_pos)

    def move_y(self,delta):
        self.microcontroller.move_y(delta)
        self.y_pos = self.y_pos + delta
        self.yPos.emit(self.y_pos)
        QApplication.processEvents()

    def open_valve_1(self):
        self.microcontroller.toggle_valve_1(1)

    def open_valve_2(self):
        self.microcontroller.toggle_valve_2(1)

    def close_valve_1(self):
        self.microcontroller.toggle_valve_1(0)

    def close_valve_2(self):
        self.microcontroller.toggle_valve_2(0)

class VentController(QObject):
    def __init__(self,microcontroller):
        QObject.__init__(self)
        self.microcontroller = microcontroller
        self.Vt = MicrocontrollerDef.Vt_DEFAULT
        self.Ti = MicrocontrollerDef.Ti_DEFAULT
        self.RR = MicrocontrollerDef.RR_DEFAULT
        self.PEEP = MicrocontrollerDef.PEEP_DEFAULT


    def setVT(self,value):
        self.microcontroller.set_parameter(MicrocontrollerDef.CMD_Vt,value/MicrocontrollerDef.VT_FS)
        self.Vt = value

    def setTi(self,value):
        self.microcontroller.set_parameter(MicrocontrollerDef.CMD_Ti,value/MicrocontrollerDef.TI_FS)
        self.Ti = value

    def setRR(self,value):
        self.microcontroller.set_parameter(MicrocontrollerDef.CMD_RR,value/MicrocontrollerDef.RR_FS)
        self.RR = value

    def setPEEP(self,value):
        self.microcontroller.set_parameter(MicrocontrollerDef.CMD_PEEP,value/MicrocontrollerDef.PEEP_FS)
        self.PEEP = value

    def setFlow(self,value):
        self.microcontroller.set_parameter(MicrocontrollerDef.CMD_Flow,value/MicrocontrollerDef.VALVE_POS_OPEN_STEPS_FS)

    # def setFlowDeceleratingSlope(self,value):
    #     self.microcontroller.set_parameter(MicrocontrollerDef.CMD_FlowDeceleratingSlope,value/100)

    def setPinsp(self,value):
        print('setting P_insp')
        self.microcontroller.set_parameter(MicrocontrollerDef.CMD_Pinsp,value/MicrocontrollerDef.PAW_FS)

    def setRiseTime(self,value):
        self.microcontroller.set_parameter(MicrocontrollerDef.CMD_RiseTime,value/MicrocontrollerDef.PC_RISE_TIME_MS_FS)

    def setPID_P(self,value):
        self.microcontroller.set_parameter(MicrocontrollerDef.CMD_PID_P,value/MicrocontrollerDef.PID_COEFFICIENT_P_FS)

    def setPID_I_frac(self,value):
        self.microcontroller.set_parameter(MicrocontrollerDef.CMD_PID_I_frac,value/MicrocontrollerDef.PID_COEFFICIENT_I_FRAC_FS)


# class DataLogger(QObject):
#     def __init__(self,microcontroller):
#         QObject.__init__(self)
#         self.file = open("~/Downloads/" + datetime.now().strftime('%Y-%m-%d %H-%M-%-S.%f') + ".csv", "w")

#     def log_data(self,time,paw,flow,volume):
#         self.file.write(str(time)+','+str(paw)+','+str(flow)+','+str(volume))

#     def close(self):
#         self.file.close()

class Waveforms(QObject):

    signal_Paw = Signal(float,float)
    signal_Volume = Signal(float,float)
    signal_Flow = Signal(float,float)

    signal_updatePlot = Signal()

    def __init__(self,microcontroller,ventController):
        QObject.__init__(self)
        self.file = open(str(Path.home()) + "/Downloads/" + datetime.now().strftime('%Y-%m-%d %H-%M-%-S.%f') + ".csv", "w+")
        self.file.write('Time (s),Paw (cmH2O),Flow (l/min),Volume (ml),Vt (ml),Ti (s),RR (/min),PEEP (cmH2O)\n')
        self.microcontroller = microcontroller
        self.ventController = ventController
        self.Paw = 0
        self.Volume = 0
        self.Flow = 0
        self.time = 0
        self.timer_update_waveform = QTimer()
        self.timer_update_waveform.setInterval(WAVEFORMS.UPDATE_INTERVAL_MS)
        self.timer_update_waveform.timeout.connect(self.update_waveforms)
        self.timer_update_waveform.start()

        self.time_now = 0
        self.time_diff = 0
        self.time_prev = time.time()

        self.counter_display = 0
        self.counter_file_flush = 0

    def update_waveforms(self):
        # self.time = self.time + (1/1000)*WAVEFORMS.UPDATE_INTERVAL_MS

        # Use the processor clock to determine elapsed time since last function call
        self.time_now = time.time()
      
        if SIMULATION:
            self.Paw = (self.Paw + 0.2)%5
            self.Volume = (self.Volume + 0.2)%5
            self.Flow = (self.Flow + 0.2)%5
            self.file.write(str(self.time_now)+','+str(self.Paw)+','+str(self.Flow)+','+str(self.Volume)+'\n')

        else:
            readout = self.microcontroller.read_received_packet_nowait()
            if readout is not None:
                self.Paw = (utils.unsigned_to_signed(readout[0:2],MicrocontrollerDef.N_BYTES_DATA)/(65536/2))*MicrocontrollerDef.PAW_FS 
                self.Flow = (utils.unsigned_to_signed(readout[2:4],MicrocontrollerDef.N_BYTES_DATA)/(65536/2))*MicrocontrollerDef.FLOW_FS
                self.Volume = (utils.unsigned_to_unsigned(readout[4:6],MicrocontrollerDef.N_BYTES_DATA)/65536)*MicrocontrollerDef.VOLUME_FS
                # self.time = float(utils.unsigned_to_unsigned(readout[6:8],MicrocontrollerDef.N_BYTES_DATA))*MicrocontrollerDef.TIMER_PERIOD_ms/1000
                self.file.write(str(self.time_now)+','+str(self.Paw)+','+str(self.Flow)+','+str(self.Volume)+','+str(self.ventController.Vt)+','+str(self.ventController.Ti)+','+str(self.ventController.RR)+','+str(self.ventController.PEEP) +'\n')
        
        # reduce display refresh rate
        self.counter_display = self.counter_display + 1
        if self.counter_display>=1:
            self.time_diff = self.time_now - self.time_prev
            self.time_prev = self.time_now
            self.time += self.time_diff
            self.counter_display = 0
            self.signal_Paw.emit(self.time,self.Paw)
            self.signal_Flow.emit(self.time,self.Flow)
            self.signal_Volume.emit(self.time,self.Volume)
            self.signal_updatePlot.emit()

        # file flushing
        self.counter_file_flush = self.counter_file_flush + 1
        if self.counter_file_flush>=500:
            self.counter_file_flush = 0
            self.file.flush()

    def close(self):
        self.file.close()
