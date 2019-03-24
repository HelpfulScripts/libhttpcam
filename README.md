# Web Cam Access via HTTP REST-API

A library that unified acess to various web cams with integrated HTTP servers.

## Installation
    pip3 install libhttpcam

## Usage
Use `createCam` to create a camera instance.

    from libhttpcam import createCam

    model = 'foscam'
    ip = '10.0.0.30'
    cam, port = createCam('foscam', ip)  # use model's default port

Next, you might want to set credentials for the camera:

    user = 'me'
    password = 'youllneverguess'
    cam.set_credentials(user, password)

## Support
Currently, only `Foscam` and `Wansview` cameras are supported.
- Foscam C1
- Wansview K2
- Wansview Q3S (X Series)

## API
#### createCam(brand:str, ip:str, port:int=None) -> (HttpCam, int)
creates a HttpCam instance for the supplied `brand`, `ip` address, and `port`.
If `port` is omitted, the camera brand's default port will be used.

returns the camera instance and the port used as a tuple

### Device API
#### Cam(brand, host, port)
Constructor; typically does not get called directly but via the `createCam`


### Device Properties
#### Cam.brand
returns the camera instance's brand

#### Cam.model:
returns the camera instance's model
Note: for `Wansview` cameras this call returns `'unknown'`

#### Cam.host
returns the camera instance's ip address

#### Cam.port
returns the camera instance's port


### Device Configuration
#### Cam.set_credentials(user='', password='')
sets the credentials used to access the camera. 

#### Cam.set_sensitivities(motion=0, audio=0)
Sets the sensitivities for motion detection and audio detection. Both take values between 0 (off) and 100 (sensitive).

#### async def async_reboot(self) -> Response:
reboots the camera. 

#### async def async_set_system_time(self) -> Response:
sets the current local time on the camera. This is used for overlays in the snapshots and feeds.

#### async def async_set_irled(self, status: Status) -> Response:
sets the status of the active infrared light on the camera. Valid settings are `Status.ON', `Status.OFF`, and `Status.AUTO`

#### async def async_set_night_mode(self, status: Status) -> Response:
sets the status of the passive infrered sensor. Valid settings are `Status.ON', `Status.OFF`, and `Status.AUTO`

#### async def async_set_ftp_config(self, server, port, user, passwd) -> Response:
configures the ftp client to allow snapshots and recordings to be stored on a server via FTP.

#### async def async_set_audio_volumes(self, audio_in=50, audio_out=50) -> Response:
configures audio volumes for the camera:
- audio_in: microphone volume
- audio_out: speaker and alert volume

### Device Queries
#### async def async_get_model(self) -> str:
queries and returns the brand's model number as a string

#### async def async_get_night_mode(self) -> IRmode:
queries and returns the sensor night mode setting:
- bool result.LED
- bool result.Sensor

#### async def async_get_alarm_trigger(self) -> Trigger:
queries and returns the alarm trigger setting:
- bool result.motion
- bool result.audio

#### async def async_get_alarm_action(self) -> Action:
queries and returns the alarm action setting:
- bool result.audio    - sound the siren
- bool result.ftp_snap - store snapshots to FTP server
- bool result.ftp_rec  - store recordings to FTP server

#### async def async_get_alarm_triggered(self) -> bool:
queries and returns `True` if an alram was detected.

*Currently not implemented, returns `False`*

#### async def async_get_ftp_config(self):
queries and returns the current FTP configuration


### Device Actions
#### async def async_snap_picture(self):
snaps a picture and returns the byte array

#### async def async_mjpeg_stream(self, request):
requests and returns a motion JPEG stream

#### async def async_set_alarm(self, trigger: Trigger, action: Action) -> Response:
Arms or disarms the camera by7 setting the `trigger` and `action` settings 

#### async def async_ptz_preset(self, preset_pos:int):
moves the camera to the specified preprogrammed position if PTX is available
