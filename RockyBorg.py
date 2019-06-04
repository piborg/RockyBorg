#!/usr/bin/env python
# coding: utf-8
"""
This module is designed to communicate with the RockyBorg

Use by creating an instance of the class, call the Init function, then command as desired, e.g.
import RockyBorg
RB = RockyBorg.RockyBorg()
RB.Init()
# User code here, use RB to control the board

Multiple boards can be used when configured with different I²C addresses by creating multiple instances, e.g.
import RockyBorg
RB1 = RockyBorg.RockyBorg()
RB2 = RockyBorg.RockyBorg()
RB1.i2cAddress = 0x15
RB2.i2cAddress = 0x1516
RB1.Init()
RB2.Init()
# User code here, use RB1 and RB2 to control each board separately

For explanations of the functions available call the Help function, e.g.
import RockyBorg
RB = RockyBorg.RockyBorg()
RB.Help()
See the website at www.piborg.org/rockyborg for more details
"""

# Import the libraries we need
import io
import fcntl
import types
import time
from sys import version_info

# Constant values
I2C_SLAVE                   = 0x0703
I2C_MAX_LEN                 = 4
MOTOR_PWM_MAX               = 255
DEFAULT_SERVO_PWM_MIN       = 1000  # Should be a 1 ms burst, typical servo minimum
DEFAULT_SERVO_PWM_MAX       = 2000  # Should be a 2 ms burst, typical servo maximum
DELAY_AFTER_EEPROM          = 0.01  # Time to wait after updating an EEPROM value before reading
PWM_UNSET                   = 0xFFFF

I2C_ID_ROCKYBORG            = 0x52

COMMAND_SET_LED             = 1     # Set the LED status
COMMAND_GET_LED             = 2     # Get the LED status
COMMAND_SET_A_FWD           = 3     # Set motor 1 PWM rate in a forwards direction
COMMAND_SET_A_REV           = 4     # Set motor 1 PWM rate in a reverse direction
COMMAND_GET_A               = 5     # Get motor 1 direction and PWM rate
COMMAND_SET_B_FWD           = 6     # Set motor 2 PWM rate in a forwards direction
COMMAND_SET_B_REV           = 7     # Set motor 2 PWM rate in a reverse direction
COMMAND_GET_B               = 8     # Get motor 2 direction and PWM rate
COMMAND_ALL_OFF             = 9     # Switch everything off
COMMAND_SET_ALL_FWD         = 10    # Set all motors PWM rate in a forwards direction
COMMAND_SET_ALL_REV         = 11    # Set all motors PWM rate in a reverse direction
COMMAND_SET_FAILSAFE        = 12    # Set the failsafe flag, turns the motors off if communication is interrupted
COMMAND_GET_FAILSAFE        = 13    # Get the failsafe flag
COMMAND_SET_SERVO           = 14    # Set the PWM duty cycle for the servo (16 bit)
COMMAND_GET_SERVO           = 15    # Get the PWM duty cycle for the servo (16 bit)
COMMAND_CALIBRATE_SERVO     = 16    # Set the PWM duty cycle for the servo (16 bit, ignores limit checks)
COMMAND_GET_SERVO_MIN       = 17    # Get the minimum allowed PWM duty cycle for the servo
COMMAND_GET_SERVO_MAX       = 18    # Get the maximum allowed PWM duty cycle for the servo
COMMAND_GET_SERVO_BOOT      = 19    # Get the startup PWM duty cycle for the servo
COMMAND_SET_SERVO_MIN       = 20    # Set the minimum allowed PWM duty cycle for the servo
COMMAND_SET_SERVO_MAX       = 21    # Set the maximum allowed PWM duty cycle for the servo
COMMAND_SET_SERVO_BOOT      = 22    # Set the startup PWM duty cycle for the servo
COMMAND_SET_MOTORS_EN       = 23    # Set if the main motors are enabled
COMMAND_GET_MOTORS_EN       = 25    # Get if the main motors are enabled

COMMAND_GET_ID              = 0x99  # Get the board identifier
COMMAND_SET_I2C_ADD         = 0xAA  # Set a new I²C address

COMMAND_VALUE_FWD           = 1     # I²C value representing forward
COMMAND_VALUE_REV           = 2     # I²C value representing reverse

COMMAND_VALUE_ON            = 1     # I²C value representing on
COMMAND_VALUE_OFF           = 0     # I²C value representing off


def ScanForRockyBorg(busNumber = 1):
    """
ScanForRockyBorg([busNumber])

Scans the I²C bus for a RockyBorg boards and returns a list of all usable addresses
The busNumber if supplied is which I²C bus to scan, 0 for Rev 1 boards, 1 for Rev 2 boards, if not supplied the default is 1
    """
    found = []
    print('Scanning I²C bus #%d' % (busNumber))
    bus = RockyBorg()
    for address in range(0x03, 0x78, 1):
        try:
            bus.InitBusOnly(busNumber, address)
            i2cRecv = bus.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
            if len(i2cRecv) == I2C_MAX_LEN:
                if i2cRecv[1] == I2C_ID_ROCKYBORG:
                    print('Found RockyBorg at %02X' % (address))
                    found.append(address)
                else:
                    pass
            else:
                pass
        except KeyboardInterrupt:
            raise
        except:
            pass
    if len(found) == 0:
        print('No RockyBorg boards found, is bus #%d correct (should be 0 for Rev 1, 1 for Rev 2)' % (busNumber))
    elif len(found) == 1:
        print('1 RockyBorg board found')
    else:
        print('%d RockyBorg boards found' % (len(found)))
    return found


def SetNewAddress(newAddress, oldAddress = -1, busNumber = 1):
    """
SetNewAddress(newAddress, [oldAddress], [busNumber])

Scans the I²C bus for the first RockyBorg and sets it to a new I²C address
If oldAddress is supplied it will change the address of the board at that address rather than scanning the bus
The busNumber if supplied is which I²C bus to scan, 0 for Rev 1 boards, 1 for Rev 2 boards, if not supplied the default is 1
Warning, this new I²C address will still be used after resetting the power on the device
    """
    if newAddress < 0x03:
        print('Error, I²C addresses below 3 (0x03) are reserved, use an address between 3 (0x03) and 119 (0x77)')
        return
    elif newAddress > 0x77:
        print('Error, I²C addresses above 119 (0x77) are reserved, use an address between 3 (0x03) and 119 (0x77)')
        return
    if oldAddress < 0x0:
        found = ScanForRockyBorg(busNumber)
        if len(found) < 1:
            print('No RockyBorg boards found, cannot set a new I²C address!')
            return
        else:
            oldAddress = found[0]
    print('Changing I²C address from %02X to %02X (bus #%d)' % (oldAddress, newAddress, busNumber))
    bus = RockyBorg()
    bus.InitBusOnly(busNumber, oldAddress)
    try:
        i2cRecv = bus.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
        if len(i2cRecv) == I2C_MAX_LEN:
            if i2cRecv[1] == I2C_ID_ROCKYBORG:
                foundChip = True
                print('Found RockyBorg at %02X' % (oldAddress))
            else:
                foundChip = False
                print('Found a device at %02X, but it is not a RockyBorg (ID %02X instead of %02X)' % (oldAddress, i2cRecv[1], I2C_ID_ROCKYBORG))
        else:
            foundChip = False
            print('Missing RockyBorg at %02X' % (oldAddress))
    except KeyboardInterrupt:
        raise
    except:
        foundChip = False
        print('Missing RockyBorg at %02X' % (oldAddress))
    if foundChip:
        bus.RawWrite(COMMAND_SET_I2C_ADD, [newAddress])
        time.sleep(0.1)
        print('Address changed to %02X, attempting to talk with the new address' % (newAddress))
        try:
            bus.InitBusOnly(busNumber, newAddress)
            i2cRecv = bus.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
            if len(i2cRecv) == I2C_MAX_LEN:
                if i2cRecv[1] == I2C_ID_ROCKYBORG:
                    foundChip = True
                    print('Found RockyBorg at %02X' % (newAddress))
                else:
                    foundChip = False
                    print('Found a device at %02X, but it is not a RockyBorg (ID %02X instead of %02X)' % (newAddress, i2cRecv[1], I2C_ID_ROCKYBORG))
            else:
                foundChip = False
                print('Missing RockyBorg at %02X' % (newAddress))
        except KeyboardInterrupt:
            raise
        except:
            foundChip = False
            print('Missing RockyBorg at %02X' % (newAddress))
    if foundChip:
        print('New I²C address of %02X set successfully' % (newAddress))
    else:
        print('Failed to set new I²C address...')


# Class used to control RockyBorg
class RockyBorg:
    """
This module is designed to communicate with the RockyBorg

busNumber               I²C bus on which the RockyBorg is attached (Rev 1 is bus 0, Rev 2 is bus 1)
bus                     the smbus object used to talk to the I²C bus
i2cAddress              The I²C address of the RockyBorg chip to control
foundChip               True if the RockyBorg chip can be seen, False otherwise
printFunction           Function reference to call when printing text, if None "print" is used
    """

    # Shared values used by this class
    busNumber               = 1                     # Check here for Rev 1 vs Rev 2 and select the correct bus
    i2cAddress              = I2C_ID_ROCKYBORG      # I²C address, override for a different address
    foundChip               = False
    printFunction           = None
    i2cWrite                = None
    i2cRead                 = None

    # Default calibration adjustments to standard values
    SERVO_PWM_MIN           = DEFAULT_SERVO_PWM_MIN
    SERVO_PWM_MAX           = DEFAULT_SERVO_PWM_MAX


    def RawWrite(self, command, data):
        """
RawWrite(command, data)

Sends a raw command on the I²C bus to the RockyBorg
Command codes can be found at the top of RockyBorg.py, data is a list of 0 or more byte values

Under most circumstances you should use the appropriate function instead of RawWrite
        """
        if version_info[0] < 3:
            # Python 2 uses the character string type for I²C data
            rawOutput = chr(command)
            for singleByte in data:
                rawOutput += chr(singleByte)
        else:
            # Python 3 uses the bytes type for I²C data
            rawOutput = [command]
            rawOutput.extend(data)
            rawOutput = bytes(rawOutput)
        self.i2cWrite.write(rawOutput)


    def RawRead(self, command, length, retryCount = 3):
        """
RawRead(command, length, [retryCount])

Reads data back from the RockyBorg after sending a GET command
Command codes can be found at the top of RockyBorg.py, length is the number of bytes to read back

The function checks that the first byte read back matches the requested command
If it does not it will retry the request until retryCount is exhausted (default is 3 times)

Under most circumstances you should use the appropriate function instead of RawRead
        """
        while retryCount > 0:
            self.RawWrite(command, [])
            rawReply = self.i2cRead.read(length)
            reply = []
            for singleByte in rawReply:
                if version_info[0] < 3:
                    # In Python 2 we need to convert the character to its numeric value
                    singleByte = ord(singleByte)
                reply.append(singleByte)
            if command == reply[0]:
                break
            else:
                retryCount -= 1
        if retryCount > 0:
            return reply
        else:
            raise IOError('I²C read for command %d failed' % (command))


    def InitBusOnly(self, busNumber, address):
        """
InitBusOnly(busNumber, address)

Prepare the I²C driver for talking to a RockyBorg on the specified bus and I²C address
This call does not check the board is present or working, under most circumstances use Init() instead
        """
        self.busNumber = busNumber
        self.i2cAddress = address
        self.i2cRead = io.open("/dev/i2c-" + str(self.busNumber), "rb", buffering = 0)
        fcntl.ioctl(self.i2cRead, I2C_SLAVE, self.i2cAddress)
        self.i2cWrite = io.open("/dev/i2c-" + str(self.busNumber), "wb", buffering = 0)
        fcntl.ioctl(self.i2cWrite, I2C_SLAVE, self.i2cAddress)


    def Print(self, message):
        """
Print(message)

Wrapper used by the RockyBorg instance to print(messages, will call printFunction if set, print otherwise)
        """
        if self.printFunction == None:
            print(message)
        else:
            self.printFunction(message)


    def NoPrint(self, message):
        """
NoPrint(message)

Does nothing, intended for disabling diagnostic printout by using:
RB = RockyBorg.RockyBorg()
RB.printFunction = RB.NoPrint
        """
        pass


    def Init(self, tryOtherBus = False):
        """
Init([tryOtherBus])

Prepare the I²C driver for talking to the RockyBorg

If tryOtherBus is True, this function will attempt to use the other bus if the RockyBorg devices can not be found on the current busNumber
    This is only really useful for early Raspberry Pi models!
        """
        self.Print('Loading RockyBorg on bus %d, address %02X' % (self.busNumber, self.i2cAddress))

        # Open the bus
        self.i2cRead = io.open("/dev/i2c-" + str(self.busNumber), "rb", buffering = 0)
        fcntl.ioctl(self.i2cRead, I2C_SLAVE, self.i2cAddress)
        self.i2cWrite = io.open("/dev/i2c-" + str(self.busNumber), "wb", buffering = 0)
        fcntl.ioctl(self.i2cWrite, I2C_SLAVE, self.i2cAddress)

        # Check for RockyBorg
        try:
            i2cRecv = self.RawRead(COMMAND_GET_ID, I2C_MAX_LEN)
            if len(i2cRecv) == I2C_MAX_LEN:
                if i2cRecv[1] == I2C_ID_ROCKYBORG:
                    self.foundChip = True
                    self.Print('Found RockyBorg at %02X' % (self.i2cAddress))
                else:
                    self.foundChip = False
                    self.Print('Found a device at %02X, but it is not a RockyBorg (ID %02X instead of %02X)' % (self.i2cAddress, i2cRecv[1], I2C_ID_ROCKYBORG))
            else:
                self.foundChip = False
                self.Print('Missing RockyBorg at %02X' % (self.i2cAddress))
        except KeyboardInterrupt:
            raise
        except:
            self.foundChip = False
            self.Print('Missing RockyBorg at %02X' % (self.i2cAddress))

        # See if we are missing chips
        if not self.foundChip:
            self.Print('RockyBorg was not found')
            if tryOtherBus:
                if self.busNumber == 1:
                    self.busNumber = 0
                else:
                    self.busNumber = 1
                self.Print('Trying bus %d instead' % (self.busNumber))
                self.Init(False)
            else:
                self.Print('Are you sure your RockyBorg is properly attached, the correct address is used, and the I²C drivers are running?')
                self.bus = None
        else:
            self.Print('RockyBorg loaded on bus %d' % (self.busNumber))

        # Read the calibration settings from the RockyBorg
        self.SERVO_PWM_MIN = self.GetWithRetry(self.GetServoMinimum, 5)
        if self.SERVO_PWM_MIN is None:
            self.Print('Error: Failed reading servo minimum, using default!')
            self.SERVO_PWM_MIN = DEFAULT_SERVO_PWM_MIN
        self.SERVO_PWM_MAX = self.GetWithRetry(self.GetServoMaximum, 5)
        if self.SERVO_PWM_MAX is None:
            self.Print('Error: Failed reading servo maximum, using default!')
            self.SERVO_PWM_MAX = DEFAULT_SERVO_PWM_MAX


    def GetWithRetry(self, function, count):
        """
value = GetWithRetry(function, count)

Attempts to read a value multiple times before giving up
Pass a get function with no parameters
e.g.
distance = GetWithRetry(RB.GetServoMinimum, 5)
Will try RB.GetServoMinimum() upto 5 times, returning when it gets a value
Useful for ensuring a read is successful
        """
        value = None
        for i in range(count):
            okay = True
            try:
                value = function()
            except KeyboardInterrupt:
                raise
            except:
                okay = False
            if okay:
                break
        return value


    def SetWithRetry(self, setFunction, getFunction, value, count):
        """
worked = SetWithRetry(setFunction, getFunction, value, count)

Attempts to write a value multiple times before giving up
Pass a set function with one parameter, and a get function no parameters
The get function will be used to check if the set worked, if not it will be repeated
e.g.
worked = SetWithRetry(RB.SetServoMinimum, RB.GetServoMinimum, 2000, 5)
Will try RB.SetServoMinimum(2000) upto 5 times, returning when RB.GetServoMinimum returns 2000.
Useful for ensuring a write is successful
        """
        for i in range(count):
            okay = True
            try:
                setFunction(value)
                readValue = getFunction()
            except KeyboardInterrupt:
                raise
            except:
                okay = False
            if okay:
                if readValue == value:
                    break
                else:
                    okay = False
        return okay


    def SetMotor2(self, power):
        """
SetMotor2(power)

Sets the drive level for motor 2, from +1 to -1.
e.g.
SetMotor2(0)     -> motor 2 is stopped
SetMotor2(0.75)  -> motor 2 moving forward at 75% power
SetMotor2(-0.5)  -> motor 2 moving reverse at 50% power
SetMotor2(1)     -> motor 2 moving forward at 100% power
        """
        if power < 0:
            # Reverse
            command = COMMAND_SET_B_REV
            pwm = -int(MOTOR_PWM_MAX * power)
            if pwm > MOTOR_PWM_MAX:
                raise ValueError('Motor 2 power %f is below the +1.0 to -1.0 limits' % (power))
        else:
            # Forward / stopped
            command = COMMAND_SET_B_FWD
            pwm = int(MOTOR_PWM_MAX * power)
            if pwm > MOTOR_PWM_MAX:
                raise ValueError('Motor 2 power %f is above the +1.0 to -1.0 limits' % (power))

        try:
            self.RawWrite(command, [pwm])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motor 2 drive level!')


    def GetMotor2(self):
        """
power = GetMotor2()

Gets the drive level for motor 2, from +1 to -1.
e.g.
0     -> motor 2 is stopped
0.75  -> motor 2 moving forward at 75% power
-0.5  -> motor 2 moving reverse at 50% power
1     -> motor 2 moving forward at 100% power
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_B, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading motor 2 drive level!')
            return

        power = float(i2cRecv[2]) / float(MOTOR_PWM_MAX)

        if i2cRecv[1] == COMMAND_VALUE_FWD:
            return power
        elif i2cRecv[1] == COMMAND_VALUE_REV:
            return -power
        else:
            return


    def SetMotor1(self, power):
        """
SetMotor1(power)

Sets the drive level for motor 1, from +1 to -1.
e.g.
SetMotor1(0)     -> motor 1 is stopped
SetMotor1(0.75)  -> motor 1 moving forward at 75% power
SetMotor1(-0.5)  -> motor 1 moving reverse at 50% power
SetMotor1(1)     -> motor 1 moving forward at 100% power
        """
        if power < 0:
            # Reverse
            command = COMMAND_SET_A_REV
            pwm = -int(MOTOR_PWM_MAX * power)
            if pwm > MOTOR_PWM_MAX:
                raise ValueError('Motor 1 power %f is below the +1.0 to -1.0 limits' % (power))
        else:
            # Forward / stopped
            command = COMMAND_SET_A_FWD
            pwm = int(MOTOR_PWM_MAX * power)
            if pwm > MOTOR_PWM_MAX:
                raise ValueError('Motor 1 power %f is above the +1.0 to -1.0 limits' % (power))

        try:
            self.RawWrite(command, [pwm])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motor 1 drive level!')


    def GetMotor1(self):
        """
power = GetMotor1()

Gets the drive level for motor 1, from +1 to -1.
e.g.
0     -> motor 1 is stopped
0.75  -> motor 1 moving forward at 75% power
-0.5  -> motor 1 moving reverse at 50% power
1     -> motor 1 moving forward at 100% power
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_A, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading motor 1 drive level!')
            return

        power = float(i2cRecv[2]) / float(MOTOR_PWM_MAX)

        if i2cRecv[1] == COMMAND_VALUE_FWD:
            return power
        elif i2cRecv[1] == COMMAND_VALUE_REV:
            return -power
        else:
            return


    def SetMotors(self, power):
        """
SetMotors(power)

Sets the drive level for all motors, from +1 to -1.
e.g.
SetMotors(0)     -> all motors are stopped
SetMotors(0.75)  -> all motors are moving forward at 75% power
SetMotors(-0.5)  -> all motors are moving reverse at 50% power
SetMotors(1)     -> all motors are moving forward at 100% power
        """
        if power < 0:
            # Reverse
            command = COMMAND_SET_ALL_REV
            pwm = -int(MOTOR_PWM_MAX * power)
            if pwm > MOTOR_PWM_MAX:
                raise ValueError('Motor power %f is below the +1.0 to -1.0 limits' % (power))
        else:
            # Forward / stopped
            command = COMMAND_SET_ALL_FWD
            pwm = int(MOTOR_PWM_MAX * power)
            if pwm > MOTOR_PWM_MAX:
                raise ValueError('Motor power %f is above the +1.0 to -1.0 limits' % (power))

        try:
            self.RawWrite(command, [pwm])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending all motors drive level!')


    def MotorsOff(self):
        """
MotorsOff()

Sets all motors to stopped, useful when ending a program
        """
        try:
            self.RawWrite(COMMAND_ALL_OFF, [0])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motors off command!')


    def SetLed(self, state):
        """
SetLed(state)

Sets the current state of the LED, False for off, True for on
        """
        if state:
            level = COMMAND_VALUE_ON
        else:
            level = COMMAND_VALUE_OFF

        try:
            self.RawWrite(COMMAND_SET_LED, [level])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending LED state!')


    def GetLed(self):
        """
state = GetLed()

Reads the current state of the LED, False for off, True for on
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_LED, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading LED state!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def SetCommsFailsafe(self, state):
        """
SetCommsFailsafe(state)

Sets the system to enable or disable the communications failsafe
The failsafe will turn the motors off unless it is commanded at least once every 1/4 of a second
Set to True to enable this failsafe, set to False to disable this failsafe
The failsafe is disabled at power on
        """
        if state:
            level = COMMAND_VALUE_ON
        else:
            level = COMMAND_VALUE_OFF

        try:
            self.RawWrite(COMMAND_SET_FAILSAFE, [level])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending communications failsafe state!')


    def GetCommsFailsafe(self):
        """
state = GetCommsFailsafe()

Read the current system state of the communications failsafe, True for enabled, False for disabled
The failsafe will turn the motors off unless it is commanded at least once every 1/4 of a second
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_FAILSAFE, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading communications failsafe state!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def GetServoPosition(self):
        """
position = GetServoPosition()

Gets the drive position for the servo
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_SERVO, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo output!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        powerOut = (float(pwmDuty) - self.SERVO_PWM_MIN) / (self.SERVO_PWM_MAX - self.SERVO_PWM_MIN)
        return (2.0 * powerOut) - 1.0


    def SetServoPosition(self, position):
        """
SetServoPosition(position)

Sets the drive position for the servo
0 is central, -1 is maximum left, +1 is maximum right
e.g.
0     -> Central
0.5   -> 50% to the right
1     -> 100% to the right
-0.75 -> 75% to the left
        """
        if (position < -1.0) or (position > +1.0):
            raise ValueError('Servo position %f is outside the +1.0 to -1.0 limits' % (position))
        powerOut = (position + 1.0) / 2.0
        pwmDuty = int((powerOut * (self.SERVO_PWM_MAX - self.SERVO_PWM_MIN)) + self.SERVO_PWM_MIN)
        pwmDutyLow = pwmDuty & 0xFF
        pwmDutyHigh = (pwmDuty >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_SERVO, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo output!')


    def GetServoMinimum(self):
        """
pwmLevel = GetServoMinimum()

Gets the minimum PWM level for the servo
This corresponds to position -1
The value is an integer where 1000 represents a 1 ms servo burst
e.g.
1000  -> 1 ms servo burst, typical shortest burst
2000  -> 2 ms servo burst, typical longest burst
1500  -> 1.5 ms servo burst, typical centre
2500  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_SERVO_MIN, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo minimum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoMaximum(self):
        """
pwmLevel = GetServoMaximum()

Gets the maximum PWM level for the servo
This corresponds to position +1
The value is an integer where 1000 represents a 1 ms servo burst
e.g.
1000  -> 1 ms servo burst, typical shortest burst
2000  -> 2 ms servo burst, typical longest burst
1500  -> 1.5 ms servo burst, typical centre
2500  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_SERVO_MAX, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo maximum burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def GetServoStartup(self):
        """
pwmLevel = GetServoStartup()

Gets the startup PWM level for the servo
This can be anywhere in the minimum to maximum range
The value is an integer where 2000 represents a 1 ms servo burst
e.g.
1000  -> 1 ms servo burst, typical shortest burst
2000  -> 2 ms servo burst, typical longest burst
1500  -> 1.5 ms servo burst, typical centre
2500  -> 2.5 ms servo burst, higher than typical longest burst 
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_SERVO_BOOT, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading servo startup burst!')
            return

        return (i2cRecv[1] << 8) + i2cRecv[2]


    def CalibrateServoPosition(self, pwmLevel):
        """
CalibrateServoPosition(pwmLevel)

Sets the raw PWM level for the servo
This value can be set anywhere from 0 for a 0% duty cycle to 20000 for a 100% duty cycle.
Larger values will also produce a 100% duty cycle.

Setting values outside the range of the servo for extended periods of time can damage the servo
NO LIMIT CHECKING IS PERFORMED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition / GetServoPosition

The value is an integer where 1000 represents a 1ms servo burst, 5% duty cycle
e.g.
1000  -> 1 ms servo burst, typical shortest burst, 5% duty cycle
2000  -> 2 ms servo burst, typical longest burst, 10% duty cycle
1500  -> 1.5 ms servo burst, typical centre, 12.5% duty cycle
2500  -> 2.5 ms servo burst, higher than typical longest burst, 22.5% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_CALIBRATE_SERVO, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending calibration servo output!')


    def GetRawServoPosition(self):
        """
pwmLevel = GetRawServoPosition()

Gets the raw PWM level for the servo
This value can be set anywhere from 0 for a 0% duty cycle to 20000 for a 100% duty cycle.
Larger values will also produce a 100% duty cycle.

This value requires interpreting into an actual servo position, this is already done by GetServoPosition
We recommend using the tuning GUI for setting the servo limits for SetServoPosition / GetServoPosition

The value is an integer where 1000 represents a 1ms servo burst, 5% duty cycle
e.g.
1000  -> 1 ms servo burst, typical shortest burst, 5% duty cycle
2000  -> 2 ms servo burst, typical longest burst, 10% duty cycle
1500  -> 1.5 ms servo burst, typical centre, 12.5% duty cycle
2500  -> 2.5 ms servo burst, higher than typical longest burst, 22.5% duty cycle
        """
        try:
            i2cRecv = self.RawRead(COMMAND_GET_SERVO, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading raw servo output!')
            return

        pwmDuty = (i2cRecv[1] << 8) + i2cRecv[2]
        return pwmDuty


    def SetServoMinimum(self, pwmLevel):
        """
SetServoMinimum(pwmLevel)

Sets the minimum PWM level for the servo
This corresponds to position -1
This value can be set anywhere from 0 for a 0% duty cycle to 20000 for a 100% duty cycle.
Larger values will also produce a 100% duty cycle.

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition / GetServoPosition

The value is an integer where 1000 represents a 1ms servo burst, 5% duty cycle
e.g.
1000  -> 1 ms servo burst, typical shortest burst, 5% duty cycle
2000  -> 2 ms servo burst, typical longest burst, 10% duty cycle
1500  -> 1.5 ms servo burst, typical centre, 12.5% duty cycle
2500  -> 2.5 ms servo burst, higher than typical longest burst, 22.5% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_SERVO_MIN, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending the servo minimum limit!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.SERVO_PWM_MIN = self.GetServoMinimum()


    def SetServoMaximum(self, pwmLevel):
        """
SetServoMaximum(pwmLevel)

Sets the maximum PWM level for the servo
This corresponds to position +1
This value can be set anywhere from 0 for a 0% duty cycle to 20000 for a 100% duty cycle.
Larger values will also produce a 100% duty cycle.

Setting values outside the range of the servo for extended periods of time can damage the servo
LIMIT CHECKING IS ALTERED BY THIS COMMAND!
We recommend using the tuning GUI for setting the servo limits for SetServoPosition / GetServoPosition

The value is an integer where 1000 represents a 1ms servo burst, 5% duty cycle
e.g.
1000  -> 1 ms servo burst, typical shortest burst, 5% duty cycle
2000  -> 2 ms servo burst, typical longest burst, 10% duty cycle
1500  -> 1.5 ms servo burst, typical centre, 12.5% duty cycle
2500  -> 2.5 ms servo burst, higher than typical longest burst, 22.5% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF

        try:
            self.RawWrite(COMMAND_SET_SERVO_MAX, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending the servo maximum limit!')
        time.sleep(DELAY_AFTER_EEPROM)
        self.SERVO_PWM_MAX = self.GetServoMaximum()


    def SetServoStartup(self, pwmLevel):
        """
SetServoStartup(pwmLevel)

Sets the startup PWM level for the servo
This value can be set anywhere from 0 for a 0% duty cycle to 20000 for a 100% duty cycle.
Larger values will also produce a 100% duty cycle.

We recommend using the tuning GUI for setting the servo limits for SetServoPosition / GetServoPosition
This value is checked against the current servo limits before setting

The value is an integer where 1000 represents a 1ms servo burst, 5% duty cycle
e.g.
1000  -> 1 ms servo burst, typical shortest burst, 5% duty cycle
2000  -> 2 ms servo burst, typical longest burst, 10% duty cycle
1500  -> 1.5 ms servo burst, typical centre, 12.5% duty cycle
2500  -> 2.5 ms servo burst, higher than typical longest burst, 22.5% duty cycle
        """
        pwmDutyLow = pwmLevel & 0xFF
        pwmDutyHigh = (pwmLevel >> 8) & 0xFF
        inRange = True

        if self.SERVO_PWM_MIN < self.SERVO_PWM_MAX:
            # Normal direction
            if pwmLevel < self.SERVO_PWM_MIN:
                inRange = False
            elif pwmLevel > self.SERVO_PWM_MAX:
                inRange = False
        else:
            # Inverted direction
            if pwmLevel > self.SERVO_PWM_MIN:
                inRange = False
            elif pwmLevel < self.SERVO_PWM_MAX:
                inRange = False
        if pwmLevel == PWM_UNSET:
            # Force to unset behaviour (central)
            inRange = True

        if not inRange:
            raise ValueError('Servo startup position %d is outside the limits of %d to %d' % (pwmLevel, self.SERVO_PWM_MIN, self.SERVO_PWM_MAX))

        try:
            self.RawWrite(COMMAND_SET_SERVO_BOOT, [pwmDutyHigh, pwmDutyLow])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending servo startup position!')
        time.sleep(DELAY_AFTER_EEPROM)


    def SetMotorsEnabled(self, state):
        """
SetMotorsEnabled(state)

Sets if the system is powering the motor drive pins
If True all of the motor pins are either low, high, or PWMed (powered)
If False all of the motor pins are tri-stated (unpowered)
        """
        if state:
            level = COMMAND_VALUE_ON
        else:
            level = COMMAND_VALUE_OFF

        try:
            self.RawWrite(COMMAND_SET_MOTORS_EN, [level])
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed sending motor drive enabled state!')


    def GetMotorsEnabled(self):
        """
state = GetMotorsEnabled()

Gets if the system is powering the motor drive pins
If True all of the motor pins are either low, high, or PWMed (powered)
If False all of the motor pins are tri-stated (unpowered)
        """ 
        try:
            i2cRecv = self.RawRead(COMMAND_GET_MOTORS_EN, I2C_MAX_LEN)
        except KeyboardInterrupt:
            raise
        except:
            self.Print('Failed reading motor drive enabled state!')
            return

        if i2cRecv[1] == COMMAND_VALUE_OFF:
            return False
        else:
            return True


    def Help(self):
        """
Help()

Displays the names and descriptions of the various functions and settings provided
        """
        funcList = [RockyBorg.__dict__.get(a) for a in dir(RockyBorg) if isinstance(RockyBorg.__dict__.get(a), types.FunctionType)]
        funcListSorted = sorted(funcList, key = lambda x: x.func_code.co_firstlineno)

        print(self.__doc__)
        print
        for func in funcListSorted:
            print('=== %s === %s' % (func.func_name, func.func_doc))

