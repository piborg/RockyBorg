#!/usr/bin/env python
# coding: utf-8

# Import library functions we need 
import RockyBorg
import sys
if sys.version_info[0] < 3:
    # Python 2 only imports
    import Tkinter
else:
    # Python 3 only imports
    import tkinter as Tkinter

# Power settings
voltageIn = 1.2 * 8             # Total battery voltage to the RockyBorg
voltageOut = 6.0                # Maximum motor voltage

# Setup the power limits
if voltageOut > voltageIn:
    maxPower = 1.0
else:
    maxPower = voltageOut / float(voltageIn)

# Setup the RockyBorg
global RB
RB = RockyBorg.RockyBorg()      # Create a new RockyBorg object
#RB.i2cAddress = 0x52           # Uncomment and change the value if you have changed the board address
RB.Init()                       # Set the board up (checks the board is connected)
RB.SetMotorsEnabled(True)       # Enable motor power
if not RB.foundChip:
    boards = RockyBorg.ScanForRockyBorg()
    if len(boards) == 0:
        print('No RockyBorg found, check you are attached :)')
    else:
        print('No RockyBorg at address %02X, but we did find boards:' % (RB.i2cAddress))
        for board in boards:
            print('    %02X (%d)' % (board, board))
        print('If you need to change the I²C address change the setup line so it is correct, e.g.')
        print('RB.i2cAddress = 0x%02X' % (boards[0]))
    sys.exit()

# Class representing the GUI dialog
class RockyBorg_tk(Tkinter.Tk):
    # Constructor (called when the object is first created)
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.protocol("WM_DELETE_WINDOW", self.OnExit) # Call the OnExit function when user closes the dialog
        self.Initialise()

    # Initialise the dialog
    def Initialise(self):
        global RB
        self.title('RockyBorg Example GUI')
        # Add 2 sliders which command each motor output, plus a stop button for both motors
        self.grid()
        self.sld1 = Tkinter.Scale(self, from_ = +100, to = -100, orient = Tkinter.VERTICAL, command = self.sld1_move)
        self.sld1.set(0)
        self.sld1.grid(column = 1, row = 0, rowspan = 1, columnspan = 1, sticky = 'NSEW')
        self.sld2 = Tkinter.Scale(self, from_ = +100, to = -100, orient = Tkinter.VERTICAL, command = self.sld2_move)
        self.sld2.set(0)
        self.sld2.grid(column = 2, row = 0, rowspan = 1, columnspan = 1, sticky = 'NSEW')
        self.butOff = Tkinter.Button(self, text = 'All Off', command = self.butOff_click)
        self.butOff['font'] = ("Arial", 20, "bold")
        self.butOff.grid(column = 0, row = 1, rowspan = 1, columnspan = 4, sticky = 'NSEW')
        # Add a slider for the servo position
        self.sldServo = Tkinter.Scale(self, from_ = -100, to = +100, orient = Tkinter.HORIZONTAL, command = self.sldServo_move)
        self.sldServo.set(0)
        self.sldServo.grid(column = 0, row = 2, rowspan = 1, columnspan = 4, sticky = 'NSEW')
        # Setup the grid scaling
        self.grid_columnconfigure(0, weight = 1)
        self.grid_columnconfigure(1, weight = 1)
        self.grid_columnconfigure(2, weight = 1)
        self.grid_columnconfigure(3, weight = 1)
        self.grid_rowconfigure(0, weight = 4)
        self.grid_rowconfigure(1, weight = 1)
        self.grid_rowconfigure(2, weight = 1)
        # Set the size of the dialog
        self.resizable(True, True)
        self.geometry('500x600')
        # Setup the initial motor state
        RB.MotorsOff()

    # Called when the user closes the dialog
    def OnExit(self):
        global RB
        # Turn drives off and end the program
        RB.MotorsOff()
        self.quit()

    # Called when sld1 is moved
    def sld1_move(self, value):
        global RB
        RB.SetMotor1((float(value) / 100.0) * maxPower)

    # Called when sld2 is moved
    def sld2_move(self, value):
        global RB
        RB.SetMotor2((float(value) / 100.0) * maxPower)

    # Called when sldServo is moved
    def sldServo_move(self, value):
        global RB
        RB.SetServoPosition(float(value) / 100.0)

    # Called when butOff is clicked
    def butOff_click(self):
        global RB
        RB.MotorsOff()
        self.sld1.set(0)
        self.sld2.set(0)

# if we are the main program (python was passed a script) load the dialog automatically
if __name__ == "__main__":
    app = RockyBorg_tk(None)
    app.mainloop()

