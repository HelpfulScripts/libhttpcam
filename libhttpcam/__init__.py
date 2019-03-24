import aiohttp
import logging
from typing import Tuple
from collections import namedtuple
from enum import Enum

name = "libhhttpcam"

_LOGGER = logging.getLogger(__name__)

RESULT_CODE = {
    '0': 'Success',
    '-1': 'CGI request string format error',
    '-2': 'Username or password error',
    '-3': 'Access denied or unsupported',
    '-4': 'CGI execute fail',
    '-5': 'Timeout',
    '-6': 'Reserved',
    '-7': 'Unknown Error',
    '-8': 'Disconnected or not a camera'
}

NTP_SERVER = [
    'time.nist.gov',
    'time.kriss.re.kr',
    'time.windows.com',
    'time.nuri.net',
]


class Status(Enum):
    STATUS_ON = 1
    STATUS_OFF = 0
    STATUS_AUTO = -1


Trigger = namedtuple('Trigger', ['motion', 'audio'])
Action = namedtuple('Action', ['audio', 'ftp_snap', 'ftp_rec'])

Response = Tuple[str, str]


def createCam(model, ip, port):
    if model.lower() == 'foscam':
        from custom_components.libhttpcam.foscam import Foscam
        Cam = Foscam(ip, port)
        return (Cam, Cam.port)
    if model.lower() == 'wansview':
        from custom_components.libhttpcam.wansview import Wansview
        Cam = Wansview(ip, port)
        return (Cam, Cam.port)
    raise HttpCamError("unknown camera model {} @{}".format(model, ip))


def cmdConcat(p):
    if isinstance(p, list):
        return '&'.join(cmdConcat(e) for e in p)
    elif isinstance(p, tuple):
        return '='.join(str(e) for e in p)


class HttpCamError(Exception):
    def __init__(self, message, Cam=None):
        self.message = message
        self.cam = Cam

    def __str__(self):
        return 'HTTP Cam {} error: {}'.format(self.cam._model if self.cam else "", self.message)


class HttpCam():
    """ http-based communication routines for FOSCAM cameras. """

    def __init__(self, model, host, port):
        self._model = model
        self._host = host
        self._port = port
        self._session = aiohttp.ClientSession()
        self.set_credentials()
        self.set_sensitivities(motion=50, audio=50)
        _LOGGER.info('HttpCam %s @%s:%s', model, host, port)

    @property
    def model(self):
        return self._model

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    def set_credentials(self, user='', password=''):
        self._usr = user
        self._pwd = password

    def set_sensitivities(self, motion=0, audio=0):
        self.motion_sensitivity = motion
        self.audio_sensitivity = audio

    def getQueryPath(self, cmd, paramStr) -> str:
        '''
        a camera model-specific construction of a query URL for the
        specified cmd and paramStr.
        '''
        return ''

    def getQueryURL(self, cmd, paramStr) -> str:
        '''
        a camera model-specific construction of a query URL for the
        specified cmd and paramStr.
        '''
        paramstr = self.getQueryPath(cmd, paramStr)
        # paramstr = urllib.parse.quote_plus(paramStr)
        return 'http://%s:%s/%s' % (self._host, self._port, paramstr)

    async def async_get(self, url, raw=False):
        '''
        asyncronously sends a GET command for the supplied URL and
        if raw == True, returns the raw result, else returns a a text result
        '''
        if self._session is None:
            self._session = aiohttp.ClientSession()
        _LOGGER.debug('async get %s', url)
        response = await self._session.get(url)
        result = response.read() if raw else response.text()
        return await result

    async def async_fetch(self, cmd, params, raw=False) -> Response:
        '''
        asyncronously fetches the response to the command and
        returns a tuple containing
        - a textual result code
        - and a dictionary of results
        '''
        # _LOGGER.warn(params)
        code = RESULT_CODE['0']
        paramstr = cmdConcat(params) if params else ''

        cmdurl = self.getQueryURL(cmd, paramstr)
        result = await self.async_get(cmdurl, raw)
        if isinstance(result, str):
            (code, result) = self.parseResult(result, params)
        return (code, result)

    def parseResult(self, result, params):
        return (RESULT_CODE['-7'], result)

    #
    # ------------------
    # Device configurations
    #
    async def async_reboot(self) -> Response:
        raise HttpCamError('async_reboot not available', self)

    async def async_set_system_time(self) -> Response:
        raise HttpCamError('async_set_system_time not available', self)

    async def async_set_irled(self, status: Status) -> Response:
        ''' sets just the IR LED status: STATUS_ON, STATUS_OFF, STATUS_AUTO '''
        raise HttpCamError('async_set_night_mode not available', self)

    async def async_set_night_mode(self, status: Status) -> Response:
        ''' sets the camera's LED and Sensor to night mode: STATUS_ON, STATUS_OFF, STATUS_AUTO '''
        raise HttpCamError('async_set_night_mode not available', self)

    async def async_set_ftp_config(self, server, port, user, passwd) -> Response:
        raise HttpCamError('async_set_ftp_config not available', self)

    async def async_set_alarm_action(self, snapToFTP=True, audioAlarm=True) -> Response:
        raise HttpCamError('async_set_alarm_action not available', self)

    async def async_set_audio_volumes(self, audio_in=50, audio_out=50) -> Response:
        raise HttpCamError('async_set_audio_volumes not available', self)

    #
    # ------------------
    # Device queries
    #
    async def async_get_night_mode(self) -> bool:
        ''' gets the camera's night mode setting '''
        raise HttpCamError('async_get_night_mode not available', self)

    async def async_get_alarm_trigger(self) -> Trigger:
        ''' gets the camera's motion and audio detection settings '''
        raise HttpCamError('async_get_alarm_trigger not available', self)

    async def async_get_alarm_action(self) -> Action:
        ''' gets the camera's alarm action settings '''
        raise HttpCamError('async_get_alarm_action not available', self)

    async def async_get_alarm_triggered(self) -> bool:
        ''' returns True if the camera has detected an alarm. '''
        raise HttpCamError('async_get_alarm_triggered not available', self)

    async def async_get_ftp_config(self):
        ''' gets the camera's ftp configuration '''
        raise HttpCamError('async_get_ftp_config not available', self)

    #
    # ------------------
    # Device actions
    #
    async def async_snap_picture(self):
        raise HttpCamError('async_snap_picture not available', self)

    async def async_mjpeg_stream(self, request):
        raise HttpCamError('async_mjpeg_stream not available', self)

    async def async_set_alarm(self, trigger: Trigger, action: Action) -> (Response, Response):
        raise HttpCamError('async_set_alarm not available', self)

    async def async_ptz_preset(self, preset_pos):
        raise HttpCamError('async_ptz_preset not available', self)
