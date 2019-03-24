import time
import math
import re
from libhttpcam import HttpCam, cmdConcat, Response, Action, Trigger, Status, IRmode
from libhttpcam import NTP_SERVER, RESULT_CODE
import logging
import requests
from requests.auth import HTTPDigestAuth

_LOGGER = logging.getLogger(__name__)

CMD_PATH = 'hy-cgi'
LED_BRIGHTNESS = 20     # 1...100
NIGHT_START = '19:00:00'
NIGHT_END = '07:00:00'
ALERT_LENGTH = 5        # seconds of audio alert (5 or more)

JOINT_TRIGGER = 'off'   # 'on' | 'off' = independent trigger


class Wansview(HttpCam):
    """ http-based communication routines for WANSVIEW cameras. """

    def __init__(self, url, port=None):
        if port is None:
            port = 80
        super(Wansview, self).__init__('Wansview', url, port)

    def _getQueryPath(self, cmd, paramStr):
        return '%s/%s?%s' % (CMD_PATH, cmd, paramStr)

    def _parseResult(self, result, params):
        # p = re.compile(r'(((?:var .*;\n)+)|.+\s*)')
        p = re.compile(r'(((?:var .*.\n?)+)|.+\s*)')
        # v = re.compile(r'var (\w*?)=(.*?);\s*')
        v = re.compile(r'var (\w*?)=\'?(.*?)\'?(?:;|\s)')

        def allButSuccess(s):
            return True if s['r'] != 'Success' else False

        def resultCheck(s, prev):
            # 'Success' response?
            if s['r'] == 'Success':
                return prev
            # detailed 'var ...' response?
            elif s['r'].startswith('var'):
                return (prev[0], dict(v.findall(s['r'])))
            # error response:
            else:
                _LOGGER.warn("*** '%s' for '%s'", s['r'], cmdConcat(s['cmd']))
                return (s['r'], cmdConcat(s['cmd']))

        success = [{'r': x[0].strip().replace('\n', ' '.replace('"', '')),
                    'cmd': params[i]} for i, x in enumerate(p.findall(result))]
        pr = (RESULT_CODE['0'], '')
        for s in filter(allButSuccess, success):
            pr = resultCheck(s, pr)
        if len(pr[1]) > 0:
            _LOGGER.debug("_parseResult '%s': '%s", pr[0], pr[1])
        return pr

    async def _async_get(self, url, raw):
        _LOGGER.debug('async get %s', url)
        response = requests.get(url, auth=self._auth)
        return response.content if raw else response.text

    #
    # ------------------
    # Device configurations
    #

    def set_credentials(self, user='', password=''):
        super(Wansview, self).set_credentials(user, password)
        self._auth = HTTPDigestAuth(self._usr, self._pwd)

    async def async_get_model(self) -> str:
        ''' gets the camera's model '''
        self._model = 'unknown'
        return self._model

    async def async_reboot(self) -> Response:
        return await self._async_fetch('device.cgi', [
            ('cmd', 'sysreboot')
        ])

    async def async_set_system_time(self) -> Response:
        ''' Set system time '''
        _t = time.localtime()
        time_zone = time.timezone/3600
        year = _t[0]
        mon = _t[1]
        day = _t[2]
        hour = _t[3]
        minute = _t[4]
        sec = _t[5]
        # is_dst = _t[8]

        ntp_server = NTP_SERVER[0]

        stime = '{}-{:02d}-{:02d};{:02d}:{:02d}:{:02d}'.format(year, mon, day, hour, minute, sec)
        return await self._async_fetch('device.cgi', [
            # [('cmd', 'setsystime'), ('stime', stime), ('timezone', time_zone+is_dst)],
            [('cmd', 'setsystime'), ('stime', stime), ('timezone', time_zone)],
            [('cmd', 'setntpattr'), ('ntpenable', '0'), ('ntpinterval', '1'), ('ntpserver', ntp_server)]
        ])

    async def async_set_irled(self, status: Status) -> Response:
        ''' sets just the IR LED status: STATUS_ON, STATUS_OFF, STATUS_AUTO '''
        STATUS = {
            Status.STATUS_ON:      'open',
            Status.STATUS_OFF:     'close',
            Status.STATUS_AUTO:    'auto'
        }
        led = STATUS[status]   # open | close | auto
        brightness = LED_BRIGHTNESS                 # 1...100
        return await self._async_fetch('irctrl.cgi', [
            [('cmd', 'setinfrared'), ('infraredstatus', led)],
            [('cmd', 'setirparams'), ('irparams', brightness)]
        ])

    async def async_set_night_mode(self, status: Status) -> None:
        ''' sets the camera's LED and Sensor to night mode: STATUS_ON, STATUS_OFF, STATUS_AUTO '''
        ctrl = 'auto' if status == Status.STATUS_AUTO else 'manual'        # manual | auto | timing
        ircutstatus = 'open' if status == Status.STATUS_ON else 'close'    # open = night mode | close = day mode
        start = NIGHT_START
        end = NIGHT_END

        if status == Status.STATUS_OFF:
            await self.async_set_irled(status)

        if ctrl == 'auto':
            return await self._async_fetch('irctrl.cgi', [
                [('cmd', 'setircutctrl'), ('ircutctrlstatus', ctrl)]
            ])
        else:
            return await self._async_fetch('irctrl.cgi', [
                [('cmd', 'setircutctrl'), ('ircutctrlstatus', ctrl)],
                [('cmd', 'setircutstatus'), ('ircutstatus', ircutstatus)],
                [('cmd', 'setircuttime'), ('starttime', start), ('endtime', end)]
            ])
        await self.async_set_irled(status)

    async def async_set_ftp_config(self, server, port, user, passwd) -> Response:
        ''' sets up the ftp settings on foscam '''
        return await self._async_fetch('ftp.cgi', [
            [('cmd', 'setftpattr'),
                ('ft_server',    server),
                ('ft_port',      port),
                ('ft_username',  user),
                ('ft_password',  passwd),
                ('ft_dirname',   './')]
        ])

    # async def async_set_alarm_action(self, action: Action) -> Response:
    #     ''' Set recording and pre-recording parameters. '''
    #     ftp_snap = 'on' if action.ftp_snap else 'off'
    #     ftp_rec = 'on' if action.ftp_rec else 'off'
    #     audio = 'on' if action.audio else 'off'
    #     return await self._async_fetch('alarm.cgi', [
    #         [('cmd', 'setalarmact'), ('aname', 'ftpsnap'), ('switch', ftp_snap)],
    #         [('cmd', 'setalarmact'), ('aname', 'ftprec'), ('switch', ftp_rec)],
    #         [('cmd', 'setalarmact'), ('aname', 'type'), ('switch', JOINT_TRIGGER)],
    #         [('cmd', 'setalarmact'), ('aname', 'emailsnap'), ('switch', 'off')],
    #         [('cmd', 'setalarmact'), ('aname', 'snap'), ('switch', 'off')],
    #         [('cmd', 'setalarmact'), ('aname', 'record'), ('switch', 'off')],
    #         [('cmd', 'setalarmact'), ('aname', 'relay'), ('switch', 'off')],
    #         [('cmd', 'setalarmact'), ('aname', 'preset'), ('switch', 'off')],
    #         [('cmd', 'setrelayattr'), ('time', '5')],
    #         [('cmd', 'setmotorattr'), ('alarmpresetindex', '1')],
    #         [('cmd', 'setalarmact'), ('aname', 'alarmbeep'), ('switch', audio)],
    #         [('cmd', 'setalarmbeepattr'), ('audiotime', ALERT_LENGTH)]
    #     ])

    async def async_set_audio_volumes(self, audio_in=50, audio_out=50) -> Response:
        '''
        Set audio in/out volumes.
        - audio_in: 1-100
        - audio_out: 1-100
        '''
        return await self._async_fetch('av.cgi', [
            [('cmd', 'setaudioinvolume'), ('aivolume', audio_in)],
            # [('cmd', 'setaudiooutflag')],
            [('cmd', 'setaudiooutvolume'), ('aovolume', audio_out)]
        ])

    #
    # ------------------
    # Device queries
    #
    async def async_get_night_mode(self) -> IRmode:
        ''' 
        gets the camera's night mode setting.
        returns: 
        - bool IR-LED Status
        - bool IR Sensor Status
        '''
        result = await self._async_fetch('irctrl.cgi', [
            [('cmd', 'getinfrared')],       # 'infraredstatus': 'close'
            [('cmd', 'getirparams')],       # 'irparams': '20' - brighness
            [('cmd', 'getircutctrl')],      # 'ircutctrlstatus': 'manual'
            [('cmd', 'getircuttime')],      # 'starttime': '19:00:00', 'endtime': '07:00:00'
            [('cmd', 'getircutstatus')]     # 'ircutstatus: 'close'
        ])
        return IRmode(LED=result[1]['getinfrared'], Sensor=result[1]['getircutstatus'])

    async def async_get_alarm_trigger(self) -> Trigger:
        '''
        gets the camera's motion detection settings
        fetch returns: ('Success', {
            'enable_0': "'1'", 'left_0': "'0'", 'top_0': "'0'", 'right_0': "'1920'", 'bottom_0': "'1080'",
            'sensitivity_0': "'90'", 'name_0': "'MD0'",
            'enable_1': "'0'", 'left_1': "'1568'", 'top_1': "'32'", 'right_1': "'1856'", 'bottom_1': "'352'",
            'sensitivity_1': "'50'", 'name_1': "'MD1'",
            'enable_2': "'0'", 'left_2': "'32'", 'top_2': "'728'", 'right_2': "'352'", 'bottom_2': "'1048'",
            'sensitivity_2': "'50'", 'name_2': "'MD2'",
            'enable_3': "'0'", 'left_3': "'1568'", 'top_3': "'728'", 'right_3': "'1856'", 'bottom_3': "'1048'",
            'sensitivity_3': "'50'", 'name_3': "'MD3'",
            'aa_enable': '1', 'aa_value': '0'})
        '''
        result = await self._async_fetch('alarm.cgi', [
            [('cmd', 'getmdattr'), ('cmd', 'getaudioalarmattr')]
        ])
        # _LOGGER.warn('async_get_alarm_trigger %s\n%s', self._host, result)
        return Trigger(
            motion=True if result[1]['enable_0'] == '1' else False,
            audio=True if result[1]['aa_enable'] == '1' else False
        )

    async def async_get_alarm_action(self) -> Action:
        """
        Return the current motion detection configuration.
        Fetch returns: ('Success', {
            'act_ftpsnap_switch': 'on', 'act_ftprec_switch': 'on', 'act_alarm_type': 'off',
            'act_emailsnap_switch': 'off', 'act_snap_switch': 'off', 'act_record_switch': 'off',
            'act_relay_switch': 'off', 'act_preset_switch': 'off', 'time': '5',
            'alarmpresetindex': '1', 'act_alarmbeep_switch': 'off', 'audiotime': '5'
        })
        """
        result = await self._async_fetch('alarm.cgi', [
            [('cmd', 'getalarmact'), ('aname', 'ftpsnap')],
            [('cmd', 'getalarmact'), ('aname', 'ftprec')],
            [('cmd', 'getalarmact'), ('aname', 'type')],
            [('cmd', 'getalarmact'), ('aname', 'emailsnap')],
            [('cmd', 'getalarmact'), ('aname', 'snap')],
            [('cmd', 'getalarmact'), ('aname', 'record')],
            [('cmd', 'getalarmact'), ('aname', 'relay')],
            [('cmd', 'getalarmact'), ('aname', 'preset')],
            [('cmd', 'getrelayattr'), ('time', '5')],
            [('cmd', 'getmotorattr')],
            [('cmd', 'getalarmact'), ('aname', 'alarmbeep')],
            [('cmd', 'getalarmbeepattr')]
        ])
        # _LOGGER.warn('async_get_alarm_action %s\n%s', self._host, result)
        return Action(
            audio=True if result[1]['act_alarmbeep_switch'] == 'on' else False,
            ftp_snap=True if result[1]['act_ftpsnap_switch'] == 'on' else False,
            ftp_rec=True if result[1]['act_ftprec_switch'] == 'on' else False
        )

    async def async_get_alarm_triggered(self) -> bool:
        ''' returns True if the camera has detected an alarm. '''
        return False

    async def async_get_ftp_config(self) -> Response:
        ''' gets the camera's ftp configuration '''
        return await self._async_fetch('ftp.cgi', [
            [('cmd', 'getftpattr')]
        ])

    #
    # ------------------
    # Device actions
    #
    async def async_snap_picture(self):
        ''' Manually request snapshot. Returns raw JPEG data. '''
        code, path = await self._async_fetch('av.cgi', [
            [('cmd', 'manualsnap'), ('chn', 0)]
        ])
        if code != RESULT_CODE['0']:
            _LOGGER.warn('received "%s" getting snap path')
        if isinstance(path, dict):
            imgurl = 'http://%s:%s%s' % (self._host, self._port, path['picpath'])
            return (RESULT_CODE['0'], await self._async_get(imgurl, raw=True))
        else:
            return (RESULT_CODE['-3'], '')

    async def async_set_alarm(self, trigger: Trigger, action: Action) -> Response:
        ''' Get the current config and set the motion detection on or off '''
        md = 1 if trigger.motion else 0
        ad = 1 if trigger.audio else 0
        sensitivity = math.floor(self.audio_sensitivity/10)
        ftp_snap = 'on' if action.ftp_snap else 'off'
        ftp_rec = 'on' if action.ftp_rec else 'off'
        audio = 'on' if action.audio else 'off'
        return await self._async_fetch('alarm.cgi', [
            [('cmd', 'setmdattr'), ('enable', md), ('sensitivity', self.motion_sensitivity),
                ('left', 0), ('top', 0), ('right', 1920), ('bottom', 1080), ('index', 0), ('name', 'MD0')],
            [('cmd', 'setaudioalarmattr'), ('aa_enable', ad), ('aa_value', sensitivity)],
            [('cmd', 'setalarmact'), ('aname', 'ftpsnap'), ('switch', ftp_snap)],
            [('cmd', 'setalarmact'), ('aname', 'ftprec'), ('switch', ftp_rec)],
            [('cmd', 'setalarmact'), ('aname', 'type'), ('switch', JOINT_TRIGGER)],
            [('cmd', 'setalarmact'), ('aname', 'emailsnap'), ('switch', 'off')],
            [('cmd', 'setalarmact'), ('aname', 'snap'), ('switch', 'off')],
            [('cmd', 'setalarmact'), ('aname', 'record'), ('switch', 'off')],
            [('cmd', 'setalarmact'), ('aname', 'relay'), ('switch', 'off')],
            [('cmd', 'setalarmact'), ('aname', 'preset'), ('switch', 'off')],
            [('cmd', 'setrelayattr'), ('time', '5')],
            [('cmd', 'setmotorattr'), ('alarmpresetindex', '1')],
            [('cmd', 'setalarmact'), ('aname', 'alarmbeep'), ('switch', audio)],
            [('cmd', 'setalarmbeepattr'), ('audiotime', ALERT_LENGTH)]
        ])

    async def async_ptz_preset(self, preset_pos:int) -> Response:
        ''' set to predefined PTZ position '''
        if preset_pos is not None:
            return await self._async_fetch('ptz.cgi', [
                [('cmd',  'setmotorattr'),
                    ('tiltscan',     1),
                    ('panscan',      1),
                    ('tiltspeed',    3),    # 1 low, 2: med, 3: fast
                    ('panspeed',     3),
                    ('movehome',     'on'),
                    ('ptzalarmmask', 'on'),
                    ('selfdet',      'on'),
                    ('homegopos',    1)],
                [('cmd',  'setptztour'),
                    ('tour_enable',   0),
                    ('tour_index',    ''),
                    ('tour_interval', '')],
                [('cmd',  'setrealtimeptzpos'),
                    ('realTimeposenable',  0)],
                [('cmd',      'preset'),
                    ('act',      'goto'),
                    ('number',   preset_pos)]
            ])
        else:
            return (RESULT_CODE['0'], '')
