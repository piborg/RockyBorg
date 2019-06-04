#!/usr/bin/env python
# coding: utf-8

# Import library functions we need 
import RockyBorg
import sys
if sys.version_info[0] < 3:
    # Python 2 only imports
    import Tkinter
    import Tix
else:
    # Python 3 only imports
    import tkinter as Tkinter
    from tkinter import tix as Tix

# Start the RockyBorg
global RB
RB = RockyBorg.RockyBorg()      # Create a new RockyBorg object
RB.Init()                       # Set the board up (checks the board is connected)

# Calibration settings
CAL_PWM_MIN = 0                 # Minimum selectable calibration burst (1000 = 1 ms)
CAL_PWM_MAX = 3000              # Maximum selectable calibration burst (1000 = 1 ms)
CAL_PWM_START = 1500            # Startup value for the calibration burst (1000 = 1 ms)

# Class representing the GUI dialog
class RockyBorgTuning_tk(Tkinter.Tk):
    # Constructor (called when the object is first created)
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)
        self.tk.call('package', 'require', 'Tix')
        self.parent = parent
        self.protocol("WM_DELETE_WINDOW", self.OnExit) # Call the OnExit function when user closes the dialog
        self.Initialise()

    # Initialise the dialog
    def Initialise(self):
        global RB
        self.title('RockyBorg Tuning GUI')

        # Setup a grid of 4 sliders which command each servo output, plus 4 readings for the servo positions and distances
        self.grid()

        # The heading labels
        self.lblHeadingTask = Tkinter.Label(self, text = 'Task to perform')
        self.lblHeadingTask['font'] = ('Arial', 18, 'bold')
        self.lblHeadingTask.grid(column = 0, row = 0, columnspan = 1, rowspan = 1, sticky = 'NSEW')
        self.lblHeadingServo = Tkinter.Label(self, text = 'Servo')
        self.lblHeadingServo['font'] = ('Arial', 18, 'bold')
        self.lblHeadingServo.grid(column = 1, row = 0, columnspan = 2, rowspan = 1, sticky = 'NSEW')

        # The task descriptions
        self.lblTaskMaximum = Tkinter.Label(self, text = 
                'Hover over the buttons\n' + 
                'for more help\n\n' +
                'Set the servo maximum\n(turning right)')
        self.lblTaskMaximum['font'] = ('Arial', 14, '')
        self.lblTaskMaximum.grid(column = 0, row = 1, columnspan = 1, rowspan = 2, sticky = 'NEW')
        self.lblTaskStartup = Tkinter.Label(self, text = 'Set the servo startup position\n(central)')
        self.lblTaskStartup['font'] = ('Arial', 14, '')
        self.lblTaskStartup.grid(column = 0, row = 3, columnspan = 1, rowspan = 2, sticky = 'NSEW')
        self.lblTaskMinimum = Tkinter.Label(self, text = 'Set the servo minimum\n(turning left)')
        self.lblTaskMinimum['font'] = ('Arial', 14, '')
        self.lblTaskMinimum.grid(column = 0, row = 5, columnspan = 1, rowspan = 2, sticky = 'NSEW')
        self.lblTaskCurrent = Tkinter.Label(self, text = 'Current servo position')
        self.lblTaskCurrent['font'] = ('Arial', 18, 'bold')
        self.lblTaskCurrent.grid(column = 0, row = 7, columnspan = 1, rowspan = 1, sticky = 'NSEW')

        # The servo slider
        self.sld = Tkinter.Scale(self, from_ = CAL_PWM_MAX, to = CAL_PWM_MIN, orient = Tkinter.VERTICAL, command = self.sld_move, showvalue = 0)
        self.sld.set(CAL_PWM_START)
        self.sld.grid(column = 1, row = 1, rowspan = 6, columnspan = 1, sticky = 'NSE')

        # The servo maximum
        self.lblServoMaximum = Tkinter.Label(self, text = '-')
        self.lblServoMaximum['font'] = ('Arial', 14, '')
        self.lblServoMaximum.grid(column = 2, row = 1, columnspan = 1, rowspan = 1, sticky = 'SW')
        self.butServoMaximum = Tkinter.Button(self, text = 'Save\nmaximum', command = self.butServoMaximum_click)
        self.butServoMaximum['font'] = ('Arial', 12, '')
        self.butServoMaximum.grid(column = 2, row = 2, columnspan = 1, rowspan = 1, sticky = 'NW')

        # The servo startup
        self.lblServoStartup = Tkinter.Label(self, text = '-')
        self.lblServoStartup['font'] = ('Arial', 14, '')
        self.lblServoStartup.grid(column = 2, row = 3, columnspan = 1, rowspan = 1, sticky = 'SW')
        self.butServoStartup = Tkinter.Button(self, text = 'Save\nstartup', command = self.butServoStartup_click)
        self.butServoStartup['font'] = ('Arial', 12, '')
        self.butServoStartup.grid(column = 2, row = 4, columnspan = 1, rowspan = 1, sticky = 'NW')

        # The servo minimum
        self.lblServoMinimum = Tkinter.Label(self, text = '-')
        self.lblServoMinimum['font'] = ('Arial', 14, '')
        self.lblServoMinimum.grid(column = 2, row = 5, columnspan = 1, rowspan = 1, sticky = 'SW')
        self.butServoMinimum = Tkinter.Button(self, text = 'Save\nminimum', command = self.butServoMinimum_click)
        self.butServoMinimum['font'] = ('Arial', 12, '')
        self.butServoMinimum.grid(column = 2, row = 6, columnspan = 1, rowspan = 1, sticky = 'NW')

        # The servo value (read from the controller)
        self.lblServo = Tkinter.Label(self, text = '-')
        self.lblServo['font'] = ('Arial', 18, '')
        self.lblServo.grid(column = 2, row = 7, columnspan = 1, rowspan = 1, sticky = 'NSW')

        # The major operations
        self.butReset = Tkinter.Button(self, text = 'Reset and save all to default values', command = self.butReset_click)
        self.butReset['font'] = ("Arial", 20, "bold")
        self.butReset.grid(column = 0, row = 8, rowspan = 1, columnspan = 3, sticky = 'NSEW')

        # Balloon help pop-up
        self.tipStatus = Tix.Balloon(self)
        self.servoSliderHelp = ('Use this slider to move the servo.\n' +
                                'Hover over each button for more help.\n' +
                                'The current position of the servo is shown at the bottom.')
        self.servoMaxHelp = ('Set the maximum for the servo.\n' + 
                             'Slowly move the servo slider up until the servo stops moving,\n' + 
                             'then move the slider back down slightly to where it moves again.\n' +
                             'This will become +100%.')
        self.servoStartupHelp = ('Set the startup position for the servo.\n' +
                                 'When RockyBorg powers up, the servo will move to this position.\n' + 
                                 'This position must be between the set maximum and minimum.\n' +
                                 'If unset then 0% is used instead.')
        self.servoMinHelp = ('Set the minimum for the servo.\n' + 
                             'Slowly move the servo slider down until the servo stops moving,\n' + 
                             'then move the slider back up slightly to where it moves again.\n' +
                             'This will become -100%.')
        self.tipStatus.bind_widget(self.sld,             balloonmsg = self.servoSliderHelp)
        self.tipStatus.bind_widget(self.butServoMaximum, balloonmsg = self.servoMaxHelp)
        self.tipStatus.bind_widget(self.butServoStartup, balloonmsg = self.servoStartupHelp)
        self.tipStatus.bind_widget(self.butServoMinimum, balloonmsg = self.servoMinHelp)

        # The grid sizing
        self.grid_columnconfigure(0, weight = 1)
        self.grid_columnconfigure(1, weight = 1)
        self.grid_columnconfigure(2, weight = 2)
        self.grid_rowconfigure(0, weight = 1)
        self.grid_rowconfigure(1, weight = 1)
        self.grid_rowconfigure(2, weight = 1)
        self.grid_rowconfigure(3, weight = 1)
        self.grid_rowconfigure(4, weight = 1)
        self.grid_rowconfigure(5, weight = 1)
        self.grid_rowconfigure(6, weight = 1)
        self.grid_rowconfigure(7, weight = 1)
        self.grid_rowconfigure(8, weight = 1)

        # Set the size of the dialog
        self.resizable(True, True)
        self.geometry('600x700')

        # Read the current settings for each servo
        self.ReadAllCalibration()

        # Start polling for readings
        self.poll()

    # Polling function
    def poll(self):
        global RB

        # Read the servo position
        servo = RB.GetRawServoPosition()
        self.lblServo['text'] = '%d' % (servo)

        # Prime the next poll
        self.after(200, self.poll)

    # Reads all of the current calibration settings
    def ReadAllCalibration(self):
        self.SetLabelValue(self.lblServoMaximum, RB.SERVO_PWM_MAX)
        self.SetLabelValue(self.lblServoMinimum, RB.SERVO_PWM_MIN)
        self.SetLabelValue(self.lblServoStartup, RB.GetWithRetry(RB.GetServoStartup, 5))

    # Takes a label and PWM drive level for display
    def SetLabelValue(self, label, pwmLevel):
        if pwmLevel == None:
            label['text'] = 'Unset'
        elif pwmLevel == 0x0000:
            label['text'] = 'Unset'
        elif pwmLevel == RockyBorg.PWM_UNSET:
            label['text'] = 'Unset'
        else:
            label['text'] = '%d' % (pwmLevel)

    # Takes a label and returns a PWM drive level or 0
    def GetLabelValue(self, label):
        try:
            return int(label['text'])
        except:
            return 0

    # Called when the user closes the dialog
    def OnExit(self):
        # End the program
        self.quit()

    # Called when sld is moved
    def sld_move(self, value):
        global RB
        RB.CalibrateServoPosition(int(value))

    # Called when butReset is clicked
    def butReset_click(self):
        global RB
        # Set all values back to standard
        RB.SetWithRetry(RB.SetServoMaximum, RB.GetServoMaximum, RockyBorg.DEFAULT_SERVO_PWM_MAX, 5)
        RB.SetWithRetry(RB.SetServoMinimum, RB.GetServoMinimum, RockyBorg.DEFAULT_SERVO_PWM_MIN, 5)
        RB.SetWithRetry(RB.SetServoStartup, RB.GetServoStartup, RockyBorg.PWM_UNSET, 5)

        # Move back to centre
        self.sld.set(CAL_PWM_START)

        # Re-read calibration settings
        self.ReadAllCalibration()

    # Called when butServoMaximum is clicked
    def butServoMaximum_click(self):
        global RB
        pwmLevel = self.GetLabelValue(self.lblServo)
        if pwmLevel == 0:
            self.lblServoMaximum['text'] = '%d\nCannot save!' % (pwmLevel)
            self.lblServoMaximum['fg'] = '#A00000'
        else:
            okay = RB.SetWithRetry(RB.SetServoMaximum, RB.GetServoMaximum, pwmLevel, 5)
            if okay:
                self.lblServoMaximum['text'] = '%d\nSaved' % (pwmLevel)
                self.lblServoMaximum['fg'] = '#000000'
            else:
                self.lblServoMaximum['text'] = '%d\nSave failed!' % (pwmLevel)
                self.lblServoMaximum['fg'] = '#A00000'

    # Called when butServoMinimum is clicked
    def butServoMinimum_click(self):
        global RB
        pwmLevel = self.GetLabelValue(self.lblServo)
        if pwmLevel == 0:
            self.lblServoMinimum['text'] = '%d\nCannot save!' % (pwmLevel)
            self.lblServoMinimum['fg'] = '#A00000'
        else:
            okay = RB.SetWithRetry(RB.SetServoMinimum, RB.GetServoMinimum, pwmLevel, 5)
            if okay:
                self.lblServoMinimum['text'] = '%d\nSaved' % (pwmLevel)
                self.lblServoMinimum['fg'] = '#000000'
            else:
                self.lblServoMinimum['text'] = '%d\nSave failed!' % (pwmLevel)
                self.lblServoMinimum['fg'] = '#A00000'

    # Called when butServoStartup1 is clicked
    def butServoStartup_click(self):
        global RB
        pwmLevel = self.GetLabelValue(self.lblServo)
        if pwmLevel == 0:
            self.lblServoStartup1['text'] = '%d\nCannot save!' % (pwmLevel)
            self.lblServoStartup1['fg'] = '#A00000'
        else:
            okay = RB.SetWithRetry(RB.SetServoStartup, RB.GetServoStartup, pwmLevel, 5)
            if okay:
                self.lblServoStartup['text'] = '%d\nSaved' % (pwmLevel)
                self.lblServoStartup['fg'] = '#000000'
            else:
                self.lblServoStartup['text'] = '%d\nSave failed!' % (pwmLevel)
                self.lblServoStartup['fg'] = '#A00000'

# if we are the main program (python was passed a script) load the dialog automatically
if __name__ == "__main__":
    app = RockyBorgTuning_tk(None)
    app.mainloop()

