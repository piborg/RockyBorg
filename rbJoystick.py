#!/usr/bin/env python

###
#
# rbJoystick.py: a script for the RockyBorg, for motor control using a joystick.
#
# 2019-01-08
#
###

# Load library functions we want
import time
import os
import sys
import pygame
import RockyBorg

# Re-direct our output to standard error, we need to ignore standard out to hide some nasty print statements from pygame
sys.stdout = sys.stderr

# Set up the RockyBorg
RB = RockyBorg.RockyBorg()
#RB.i2cAddress = 0x21                  # Uncomment and change the value if you have changed the board address
RB.Init()
if not RB.foundChip:
    boards = RockyBorg.ScanForRockyBorg()
    if len(boards) == 0:
        print('No RockyBorg found, check you are attached :)')
    else:
        print('No RockyBorg at address %02X, but we did find boards:' % (RB.i2cAddress))
        for board in boards:
            print('    %02X (%d)' % (board, board))
        print('If you need to change the I2C address change the set-up line so it is correct, e.g.')
        print('RB.i2cAddress = 0x%02X' % (boards[0]))
    sys.exit()

# Enable the motors and disable the failsafe
RB.SetCommsFailsafe(False)
RB.MotorsOff()
RB.SetMotorsEnabled(True)

# Settings for the joystick
axisUpDown = 1                          # Joystick axis to read for up / down position
axisUpDownInverted = False              # Set this to True if up and down appear to be swapped
axisLeftRight = 3                       # Joystick axis to read for left / right position
axisLeftRightInverted = True            # Set this to True if left and right appear to be swapped
buttonSlow = 6                          # Joystick button number for driving slowly whilst held (L2)
slowFactor = 0.5                        # Speed to slow to when the drive slowly button is held, e.g. 0.5 would be half speed
interval = 0.00                         # Time between updates in seconds, smaller responds faster but uses more processor time

# Power settings
voltageIn = 12.0                        # Total battery voltage to the RockyBorg
voltageOut = 12.0                       # Maximum motor voltage

# Set up the power limits
if voltageOut > voltageIn:
    maxPower = 1.0
else:
    maxPower = voltageOut / float(voltageIn)

# Set up pygame and wait for the joystick to become available
RB.SetLed(True)
os.environ["SDL_VIDEODRIVER"] = "dummy" # Removes the need to have a GUI window
pygame.init()
#pygame.display.set_mode((1,1))
print('Waiting for joystick... (press CTRL+C to abort)')
while True:
    try:
        try:
            pygame.joystick.init()
            # Attempt to set up the joystick
            if pygame.joystick.get_count() < 1:
                pygame.joystick.quit()
            else:
                # We have a joystick, attempt to initialise it!
                joystick = pygame.joystick.Joystick(0)
                break
        except pygame.error:
            pygame.joystick.quit()
    except KeyboardInterrupt:
        # CTRL+C exit, give up
        print('\nUser aborted')
        RB.SetLed(False)
        RB.SetCommsFailsafe(False)
        sys.exit()
    RB.SetLed(True)
    time.sleep(0.2)
    RB.SetLed(False)

print('Joystick found')
joystick.init()
try:
    RB.SetLed(False)
    print('Press CTRL+C to quit')
    driveLeft = 0.0
    driveRight = 0.0
    servoPosition = 0.0
    running = True
    hadEvent = False
    upDown = 0.0
    leftRight = 0.0
    # Loop indefinitely
    while running:
        # Get the latest events from the system
        hadEvent = False
        events = pygame.event.get()
        # Handle each event individually
        for event in events:
            if event.type == pygame.QUIT:
                # User exit
                running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                # A button on the joystick just got pushed down
                hadEvent = True
            elif event.type == pygame.JOYAXISMOTION:
                # A joystick has been moved
                hadEvent = True
            if hadEvent:
                # Read axis positions (-1 to +1)
                if axisUpDownInverted:
                    upDown = -joystick.get_axis(axisUpDown)
                else:
                    upDown = joystick.get_axis(axisUpDown)
                if axisLeftRightInverted:
                    leftRight = -joystick.get_axis(axisLeftRight)
                else:
                    leftRight = joystick.get_axis(axisLeftRight)
                # Determine the drive power levels
                driveLeft = -upDown
                driveRight = -upDown
                servoPos = -leftRight
                if leftRight < -0.05:
                    # Turning left
                    driveLeft *= 1.0 + (0.5 * leftRight)
                elif leftRight > 0.05:
                    # Turning right
                    driveRight *= 1.0 - (0.5 * leftRight)
                # Check for button presses
                if joystick.get_button(buttonSlow):
                    driveLeft *= slowFactor
                    driveRight *= slowFactor
                # Set the motors to the new speeds
                RB.SetMotor1(driveRight * maxPower)
                RB.SetMotor2(driveLeft * maxPower)
                RB.SetServoPosition(servoPos)
        # Wait for the interval period
        time.sleep(interval)
    # Disable all drives
    RB.MotorsOff()
except KeyboardInterrupt:
    # CTRL+C exit, disable all drives
    RB.MotorsOff()
    RB.SetCommsFailsafe(False)
    RB.SetLed(False)
print('')
