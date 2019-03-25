import time
import re
from libhttpcam import HttpCam, Action, Trigger, Response, Status, IRmode
from libhttpcam import NTP_SERVER, RESULT_CODE
import logging
# import xml.etree.ElementTree as ET

_LOGGER = logging.getLogger(__name__)

# params = [('key', 'value1'), ('key', 'value2')]
# async with session.get('http://httpbin.org/get',
#                        params=params) as r:
#     expect = 'http://httpbin.org/get?key=value2&key=value1'

# binary read: await resp.read()
# text read:   await resp.text()
# json read:   await resp.json()

ALARM_ACTION = {
    'audio':  1,
    'mail':   2,
    'pic':    4,
    'video':  8
}

CMD_PATH = 'cgi-bin/CGIProxy.fcgi'

LED_MODE_AUTO = 0
LED_MODE_MANUAL = 1


def motionSensitityMap(sensitivity):
    if (sensitivity < 20):      # lowest
        return 4
    if (sensitivity < 40):      # lower
        return 3
    if (sensitivity < 60):      # low
        return 0
    if (sensitivity < 80):      # medium
        return 1
    return '2'                  # high


class Foscam(HttpCam):
    """ http-based communication routines for FOSCAM cameras. """

    def __init__(self, url, port=None):
        if port is None:
            port = 88
        super(Foscam, self).__init__('Foscam', url, port)
        self.arm_cmd = None

    def _getQueryPath(self, cmd, paramStr):
        if len(paramStr) > 0:
            paramStr = '&' + paramStr
        return '%s?cmd=%s%s&usr=%s&pwd=%s' % (CMD_PATH, cmd, paramStr, self._usr, self._pwd)

    def _parseResult(self, result, params):
        p = re.compile(r'.*?<(?P<first>\S*?)>(\S*?)<\/(?P=first)>')
        d = dict(p.findall(result))
        code = RESULT_CODE[str(d['result'])]
        d.pop('result', None)
        if len(d) > 0:
            _LOGGER.debug('_parseResult  %s: %s', code, d)
        return (code, d)

    #
    # ------------------
    # Device configurations
    #
    async def async_reboot(self) -> Response:
        return await self._async_fetch('rebootSystem', [])

    async def async_set_system_time(self) -> Response:
        ''' Set system time '''
        _t = time.localtime()
        return await self._async_fetch('setSystemTime', [
            ('timeSource',    1),
            ('ntpServer',     NTP_SERVER[0]),
            ('dateFormat',    0),
            ('timeFormat',    1),
            ('timeZone',      time.timezone/3600),
            ('isDst',         _t[8]),
            ('dst',           1),
            ('year',          _t[0]),
            ('mon',           _t[1]),
            ('day',           _t[2]),
            ('hour',          _t[3]),
            ('minute',        _t[4]),
            ('sec',           _t[5])
        ])

    async def async_set_irled(self, status: Status) -> Response:
        ''' sets just the IR LED status: STATUS_ON, STATUS_OFF, STATUS_AUTO '''
        if status == Status.STATUS_AUTO:
            await self._async_fetch('setInfraLedConfig', [('mode', LED_MODE_AUTO)])
        else:   # STATUS_ON or STATUS_OFF
            await self._async_fetch('setInfraLedConfig', [('mode', LED_MODE_MANUAL)])
            if (status == Status.STATUS_ON):
                await self._async_fetch('openInfraLed', [])
            else:
                await self._async_fetch('closeInfraLed', [])

    async def async_set_night_mode(self, status: Status) -> Response:
        '''
        sets the camera's LED and Sensor to night mode: STATUS_ON, STATUS_OFF, STATUS_AUTO
        FOSCAMs don't provide separate settings for the LED and the night sensor
        --> pass through to the set_irled routine
        '''
        await self.async_set_irled(status)

    async def async_set_ftp_config(self, server, port, user, passwd) -> Response:
        ''' sets up the ftp settings on foscam '''
        params = [
            ('ftpAddr',  'ftp://%s/' % server),
            ('ftpPort',  port),
            ('mode',     0),
            ('userName', user),
            ('password', passwd)
        ]
        return await self._async_fetch('setFtpConfig', params)

    async def async_set_audio_volumes(self, audio_in=50, audio_out=50) -> Response:
        '''
        Set audio in/out volumes.
        - audio_in: 1-100
        - audio_out: 1-100
        '''
        return RESULT_CODE['-3'], {}

    #
    # ------------------
    # Device queries
    #
    async def async_get_model(self) -> str:
        ''' gets the camera's model '''
        result = await self._async_fetch('getProductModelName', [])
        self._model = result[1]['modelName']
        return self._model

    async def async_get_night_mode(self) -> IRmode:
        ''' 
        gets the camera's night mode setting.
        returns: 
        - bool IR-LED Status
        - bool IR Sensor Status
        Foscam does not publish a call for getting the current IR-LED status
        '''
        return IRmode(LED=False, Sensor=False)

    async def async_get_alarm_trigger(self) -> Trigger:
        """
        Return the current motion detection configuration.
        Fetch returns: ('Success', {
            'isEnable': '0', 'linkage': '13', 'snapInterval': '1',
            'sensitivity': '2', 'triggerInterval': '5', 'isMovAlarmEnable': '1',
            'isPirAlarmEnable': '1', 'schedule0': '281474976710655', 'schedule1': '281474976710655',
            'schedule2': '281474976710655', 'schedule3': '281474976710655', 'schedule4': '281474976710655',
            'schedule5': '281474976710655', 'schedule6': '281474976710655', 'area0': '1023', 'area1': '1023',
            'area2': '1023', 'area3': '1023', 'area4': '1023', 'area5': '1023', 'area6': '1023', 'area7': '1023',
            'area8': '1023', 'area9': '1023'})
        """
        result = await self._async_fetch('getMotionDetectConfig', [])
        # _LOGGER.warn('async_get_motion_detection %s\n%s', self._host, result)
        return Trigger(audio=False, motion=True if result[1]['isEnable'] == '1' else False)

    async def async_get_alarm_action(self) -> Action:
        """
        Return the current motion detection configuration.
        Fetch returns: ('Success', {
            'isEnable': '0', 'linkage': '13', 'snapInterval': '1',
            'sensitivity': '2', 'triggerInterval': '5', 'isMovAlarmEnable': '1',
            'isPirAlarmEnable': '1', 'schedule0': '281474976710655', 'schedule1': '281474976710655',
            'schedule2': '281474976710655', 'schedule3': '281474976710655', 'schedule4': '281474976710655',
            'schedule5': '281474976710655', 'schedule6': '281474976710655', 'area0': '1023', 'area1': '1023',
            'area2': '1023', 'area3': '1023', 'area4': '1023', 'area5': '1023', 'area6': '1023', 'area7': '1023',
            'area8': '1023', 'area9': '1023'})
        """
        result = await self._async_fetch('getMotionDetectConfig', [])
        # _LOGGER.warn('async_get_motion_detection %s\n%s', self._host, result)
        link = int(result[1]['linkage'])
        return Action(
            audio=True if link & ALARM_ACTION['audio'] else False,
            ftp_snap=True if link & ALARM_ACTION['pic'] else False,
            ftp_rec=True if link & ALARM_ACTION['video'] else False
        )

    async def async_get_alarm_triggered(self) -> bool:
        ''' returns True if the camera has detected an alarm. '''
        return False

    async def async_get_ftp_config(self) -> Response:
        ''' gets up the ftp settings on foscam '''
        return await self._async_fetch('getFtpConfig', [])

    async def async_get_record_list(self) -> Response:
        return await self._async_fetch('getRecordList', [])

    #
    # ------------------
    # Device actions
    #

    async def async_snap_picture(self):
        ''' Manually request snapshot. Returns raw JPEG data. '''
        return await self._async_fetch('snapPicture2', {}, raw=True)

    async def async_mjpeg_stream(self, request):
        return await self._async_fetch('GetMJStream', {}, raw=True)

    async def async_set_alarm(self, trigger: Trigger, action: Action) -> Response:
        ''' Get the current config and set the motion detection on or off '''

        # check if camera supports motion detection
        # code, result = await self.async_get_motion_detect_config()
        # if code != RESULT_CODE['0']:    # unsuccessful
        #     return (code, result)

        await self._async_fetch('setAlarmRecordConfig', [
            ('isEnablePreRecord',    1),
            ('preRecordSecs',        5),
            ('alarmRecordSecs',      30)
        ])
        if not self.arm_cmd:
            schedule = ''
            area = ''
            for i in range(7):
                schedule = schedule + ('&schedule%d=281474976710655' % i)
            for i in range(10):
                area = area + ('&area%d=1023' % i)
            self.arm_cmd = 'setMotionDetectConfig%s%s' % (schedule, area)

        arm = trigger.motion or trigger.audio
        pic = ALARM_ACTION['pic'] if action.ftp_snap else 0
        vid = ALARM_ACTION['video'] if action.ftp_rec else 0
        aud = ALARM_ACTION['audio'] if action.audio else 0
        link = pic + vid + aud

        params = [
            ('isEnable',         '1' if arm else '0'),
            ('linkage',          '%d' % link),
            ('sensitivity',      motionSensitityMap(self.motion_sensitivity)),    # low - high: 4, 3, 0, 1, 2
            ('snapInterval',     '1'),    # in seconds# in seconds
            ('triggerInterval',  '5')]    # in seconds
        return await self._async_fetch(self.arm_cmd, params)
