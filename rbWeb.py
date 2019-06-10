#!/usr/bin/env python
# coding: utf-8

# Creates a web-page interface for RockyBorg
#
# LED behaviour:
#   off      - Script not running, ended, or failed
#   flashing - Waiting for a connection or timed out
#   on       - Active connection

# Import library functions we need
import RockyBorg
import time
import sys
import threading
import picamera
import picamera.array
import cv2
import datetime
import textwrap
try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

# Settings for the web-page
webPort = 80                            # Port number for the web-page, 80 is what web-pages normally use
imageWidth = 240                        # Width of the captured image in pixels
imageHeight = 192                       # Height of the captured image in pixels
frameRate = 10                          # Number of images to capture per second
displayRate = 10                        # Number of images to request per second
photoDirectory = '/home/pi'             # Directory to save photos to
flippedCamera = False                   # Swap between True and False if the camera image is rotated by 180
jpegQuality = 80                        # JPEG quality level, smaller is faster, higher looks better (0 to 100)
watchdogTimeout = 1.5                   # Time in seconds before we decide we have lost contact
maximumWidth = 1000                     # Maximum pixel width for the web page

# Global values
global RB
global lastFrame
global lockFrame
global camera
global processor
global running
global watchdog
running = True

# Set up the RockyBorg
RB = RockyBorg.RockyBorg()
#RB.i2cAddress = 0x21                   # Uncomment and change the value if you have changed the board address
RB.Init()
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

# Enable the motors and disable the failsafe
RB.SetCommsFailsafe(False)
RB.MotorsOff()
RB.SetServoPosition(0)
RB.SetMotorsEnabled(True)
RB.SetLed(False)

# Power settings
voltageIn = 1.2 * 8                     # Total battery voltage to the RockyBorg
voltageOut = 6.0                        # Maximum motor voltage

# Setup the power limits
if voltageOut > voltageIn:
    maxPower = 1.0
else:
    maxPower = voltageOut / float(voltageIn)

# Timeout thread
class Watchdog(threading.Thread):
    def __init__(self):
        super(Watchdog, self).__init__()
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.timestamp = time.time()

    def run(self):
        timedOut = True
        # This method runs in a separate thread
        while not self.terminated:
            if timedOut:
                # Wait for a network event to be flagged for up to one second
                if self.event.wait(1):
                    # Connection
                    print('Reconnected...')
                    RB.SetLed(True)
                    timedOut = False
                    self.event.clear()
                else:
                    # Waiting for a connection
                    RB.SetLed(not RB.GetLed())
            else:
                # Wait for a network event to be flagged for up to the timeout time
                if self.event.wait(watchdogTimeout):
                    # Still connected
                    self.event.clear()
                    RB.SetLed(True)
                else:
                    # Timed out
                    print('Timed out...')
                    RB.SetLed(False)
                    timedOut = True
                    RB.MotorsOff()

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self):
        super(StreamProcessor, self).__init__()
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.begin = 0

    def run(self):
        global lastFrame
        global lockFrame
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and save globally
                    self.stream.seek(0)
                    if flippedCamera:
                        # Rotate counter-clockwise
                        rotatedArray = cv2.transpose(self.stream.array) # Swap X and Y
                        rotatedArray = cv2.flip(rotatedArray, 1)        # Flip image in X
                    else:
                        # Rotate clockwise
                        rotatedArray = cv2.flip(self.stream.array, 1)   # Flip image in X
                        rotatedArray = cv2.transpose(rotatedArray)      # Swap X and Y
                    retval, thisFrame = cv2.imencode('.jpg', rotatedArray, [cv2.IMWRITE_JPEG_QUALITY, jpegQuality])
                    del rotatedArray
                    lockFrame.acquire()
                    lastFrame = thisFrame
                    lockFrame.release()
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

# Image capture thread
class ImageCapture(threading.Thread):
    def __init__(self):
        super(ImageCapture, self).__init__()
        self.start()

    def run(self):
        global camera
        global processor
        print('Start the stream using the video port')
        camera.capture_sequence(self.TriggerStream(), format='bgr', use_video_port=True)
        print('Terminating camera processing...')
        processor.terminated = True
        processor.join()
        print('Processing terminated.')

    # Stream delegation loop
    def TriggerStream(self):
        global running
        while running:
            if processor.event.is_set():
                time.sleep(0.01)
            else:
                yield processor.stream
                processor.event.set()

# Class used to implement the web server
class WebServer(socketserver.BaseRequestHandler):
    def handle(self):
        global RB
        global lastFrame
        global watchdog
        # Let the watchdog know we received a request
        watchdog.event.set()
        # Get the HTTP request data
        reqData = self.request.recv(1024)
        if sys.version_info[0] > 2:
            reqData = reqData.decode()
        reqData = reqData.strip().split('\n')
        # Get the URL requested
        getPath = ''
        for line in reqData:
            if line.startswith('GET'):
                parts = line.split(' ')
                getPath = parts[1]
                break
        if getPath.startswith('/cam.jpg'):
            # Camera snapshot
            lockFrame.acquire()
            sendFrame = lastFrame
            lockFrame.release()
            if sendFrame is not None:
                self.sendImage(sendFrame)
        elif getPath.startswith('/set/'):
            # Drive setting: /set/speed/steering
            parts = getPath.split('/')
            # Get the power levels
            if len(parts) >= 4:
                try:
                    speed = float(parts[2])
                    steering = float(parts[3])
                except:
                    # Bad values
                    speed = 0.0
                    steering = 0.0
            else:
                # Bad request
                speed = 0.0
                steering = 0.0
            # Ensure settings are within limits
            if speed < -1:
                speed = -1
            elif speed > 1:
                speed = 1
            if steering < -1:
                steering = -1
            elif steering > 1:
                steering = 1
            # Determine the motor settings
            driveLeft = speed
            driveRight = speed
            if steering < -0.05:
                # Turning left
                driveLeft *= 1.0 + (0.5 * steering)
            elif steering > 0.05:
                # Turning right
                driveRight *= 1.0 - (0.5 * steering)
            # Set the outputs
            RB.SetMotor1(-driveLeft * maxPower)
            RB.SetMotor2(+driveRight * maxPower)
            RB.SetServoPosition(steering)
            # Report the current settings
            self.sendStatus()
        elif getPath.startswith('/photo'):
            # Save camera photo
            lockFrame.acquire()
            captureFrame = lastFrame
            lockFrame.release()
            if captureFrame is not None:
                photoName = '%s/Photo %s.jpg' % (photoDirectory, datetime.datetime.utcnow())
                try:
                    photoFile = open(photoName, 'wb')
                    photoFile.write(captureFrame)
                    photoFile.close()
                    statusText = 'Photo saved to %s' % (photoName)
                except:
                    statusText = 'Failed to take photo!'
            else:
                statusText = 'Failed to take photo!'
            httpText = '''\
            <html>
              <body>
                <center>
                  %s
                </center>
              </body>
            </html>
            ''' % (statusText)
            self.sendText(httpText)
        elif getPath == '/':
            # Main page, click buttons to move and to stop
            imageRatio = (100.0 * imageHeight) / imageWidth
            httpText = '''\
            <html>
              <head>
                <script language="JavaScript"><!--
                  function Drive() {
                    var iframe = document.getElementById("setDrive");
                    motors = speed.value / 100.0;
                    turn = steering.value / 100.0;
                    iframe.src = "/set/" + motors + "/" + turn;
                  }
                  function Steering(level) {
                    steering.value = level;
                    Drive();
                  }
                  function Speed(level) {
                    speed.value = level;
                    Drive();
                  }
                  function Photo() {
                    var iframe = document.getElementById("setDrive");
                    iframe.src = "/photo";
                  }
                //--></script>
                <style>
                  .slidecontainer { width: 100%%; }
                  .slider {
                    -webkit-appearance: none;
                    width: 100%%;
                    height: 80px;
                    border-radius: 25px;
                    background: #D8D8D8;
                    outline: none;
                  }
                  .slider::-webkit-slider-thumb {
                    -webkit-appearance: none;
                    appearance: none;
                    width: 35px;
                    height: 80px;
                    border-radius: 50%%;
                    background: #000000;
                  }
                  .slider::-moz-range-thumb {
                    width: 35px;
                    height: 80px;
                    border-radius: 50%%;
                    background: #000000;
                  }
                </style>
              </head>
              <body style="width:100%%; max-width:%ipx;">
                <div style="position:relative; padding-top:%f%%;">
                  <iframe src="/stream" style="position:absolute;top:0;left:0;width:100%%;height:100%%;" frameborder="0"></iframe>
                </div>
                <iframe id="setDrive" src="/set/0/0" width="100%%" height="30" frameborder="0"></iframe>
                <center>
                  <h2>Steering</h2>
                  <table width="100%%" border="0">
                    <tr>
                      <td width="33%%" align="left">left</td>
                      <td width="33%%" align="center">straight</td>
                      <td width="33%%" align="right">right</td>
                    </tr>
                    <tr>
                      <td colspan="3">
                        <input id="steering" type="range" min="-100" max="100" value="0" class="slider" oninput="Drive()" onchange="Drive()"/>
                      </td>
                    </tr>
                  </table>
                  <table width="100%%" border="0">
                    <tr>
                      <td width="20%%"><button onclick="Steering(-100)" style="width:100%%;height:80px;"><b>Hard left</b></button></td>
                      <td width="20%%"><button onclick="Steering(-50)" style="width:100%%;height:80px;"><b>Left</b></button></td>
                      <td width="20%%"><button onclick="Steering(0)" style="width:100%%;height:80px;"><b>Straight</b></button></td>
                      <td width="20%%"><button onclick="Steering(50)" style="width:100%%;height:80px;"><b>Right</b></button></td>
                      <td width="20%%"><button onclick="Steering(100)" style="width:100%%;height:80px;"><b>Hard right</b></button></td>
                    </tr>
                  </table>
                  <h2>Speed</h2>
                  <table width="100%%" border="0">
                    <tr>
                      <td width="33%%" align="left">reverse</td>
                      <td width="33%%" align="center">stopped</td>
                      <td width="33%%" align="right">forward</td>
                    </tr>
                    <tr>
                      <td colspan="3">
                        <input id="speed" type="range" min="-100" max="100" value="0" class="slider" oninput="Drive()" onchange="Drive()"/>
                      </td>
                    </tr>
                  </table>
                  <table width="100%%" border="0">
                    <tr>
                      <td width="20%%"><button onclick="Speed(-100)" style="width:100%%;height:80px;"><b>Reverse</b></button></td>
                      <td width="20%%"><button onclick="Speed(-50)" style="width:100%%;height:80px;"><b>Slow reverse</b></button></td>
                      <td width="20%%"><button onclick="Speed(0)" style="width:100%%;height:80px;"><b>Stop</b></button></td>
                      <td width="20%%"><button onclick="Speed(50)" style="width:100%%;height:80px;"><b>Slow forward</b></button></td>
                      <td width="20%%"><button onclick="Speed(100)" style="width:100%%;height:80px;"><b>Forward</b></button></td>
                    </tr>
                  </table>
                  <h2>Tools</h2>
                  <table width="100%%" border="0">
                    <tr>
                      <td width="40%%"></td>
                      <td width="20%%"><button onclick="Photo()" style="width:100%%;height:80px;"><b>Save Photo</b></button></td>
                      <td width="40%%"></td>
                    </tr>
                  </table>
                </center>
              </body>
            </html>
            ''' % (maximumWidth, imageRatio)
            self.sendText(httpText)
        elif getPath == '/stream':
            # Streaming frame, set a delayed refresh
            displayDelay = int(1000 / displayRate)
            imageRatio = 100.0 * (float(imageHeight ** 2) / float(imageWidth ** 2))
            httpText = '''\
            <html>
              <head>
                <script language="JavaScript"><!--
                  function refreshImage() {
                    if (!document.images) return;
                    document.images["rpicam"].src = "cam.jpg?" + Math.random();
                    setTimeout("refreshImage()", %d);
                  }
                //--></script>
              </head>
              <body style="margin:0" onLoad="setTimeout(\'refreshImage()\', %d)">
                <center>
                  <img src="/cam.jpg" style="width:%f%%;" name="rpicam" />
                </center>
              </body>
            </html>
            ''' % (displayDelay, displayDelay, imageRatio)
            self.sendText(httpText)
        else:
            # Unexpected page
            self.sendText('Path : "%s"' % (getPath))

    def sendStatus(self):
        global RB
        powerCorrection = 100.0 / maxPower
        leftMotor = RB.GetMotor2() * powerCorrection
        rightMotor = RB.GetMotor1() * powerCorrection
        servoPosition = RB.GetServoPosition() * 100.0
        httpText = '''\
        <html>
          <body style="margin:0">
            <center>
              <table width="75%%" border="0">
                <tr>
                  <td width="33%%" align="left">Servo: %.0f %%</td>
                  <td width="33%%" align="center">Left: %.0f %%</td>
                  <td width="33%%" align="right">Right: %.0f %%</td>
                </tr>
              </table>
            </center>
          </body>
        </html>
        ''' % (servoPosition, leftMotor, rightMotor)
        self.sendText(httpText)

    def sendText(self, content):
        content = textwrap.dedent(content)
        httpReply = 'HTTP/1.0 200 OK\n\n%s' % (content)
        if sys.version_info[0] > 2:
            httpReply = httpReply.encode()
        self.request.sendall(httpReply)

    def sendImage(self, content):
        if sys.version_info[0] > 2:
            httpReply = 'HTTP/1.0 200 OK\n\n'.encode() + bytes(content)
        else:
            httpReply = 'HTTP/1.0 200 OK\n\n%s' % (content.tostring())
        self.request.sendall(httpReply)


# Create the image buffer frame
lastFrame = None
lockFrame = threading.Lock()

# Startup sequence
print('Setup camera')
camera = picamera.PiCamera()
camera.resolution = (imageWidth, imageHeight)
camera.framerate = frameRate

print('Setup the stream processing thread')
processor = StreamProcessor()

print('Wait ...')
time.sleep(2)
captureThread = ImageCapture()

print('Setup the watchdog')
watchdog = Watchdog()

# Run the web server until we are told to close
try:
    httpServer = None
    httpServer = socketserver.TCPServer(("0.0.0.0", webPort), WebServer)
except:
    # Failed to open the port, report common issues
    print('')
    print('Failed to open port %d' % (webPort))
    print('Make sure you are running the script with sudo permissions')
    print('Other problems include running another script with the same port')
    print('If the script was just working recently try waiting a minute first')
    print('')
    # Flag the script to exit
    running = False
try:
    print('Press CTRL+C to terminate the web-server')
    while running:
        httpServer.handle_request()
except KeyboardInterrupt:
    # CTRL+C exit
    print('\nUser shutdown')
finally:
    # Turn the motors off under all scenarios
    RB.MotorsOff()
    print('Motors off')
# Tell each thread to stop, and wait for them to end
if httpServer is not None:
    httpServer.server_close()
running = False
captureThread.join()
processor.terminated = True
watchdog.terminated = True
processor.join()
watchdog.join()
del camera
RB.SetLed(False)
RB.MotorsOff()
print('Web-server terminated.')
