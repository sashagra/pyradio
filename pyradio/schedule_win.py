from sys import exit
from datetime import date, datetime, timedelta
from calendar import monthrange
import curses
import logging

from .simple_curses_widgets import DisabledWidget, SimpleCursesCheckBox, SimpleCursesPushButton, SimpleCursesTime
from .cjkwrap import cjklen, cjkslices
from .schedule import PyRadioScheduleItem, PyRadioTime

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

class PyRadioSimpleScheduleWindow(object):

    _X = _Y = _maxY = maxX = 0
    _widgets = _win = None
    _global_functions = {}
    _showed = False

    _up = (10, 0, 7, 11, 12, 1, 5, 2, 3, 4, 6, 8, 9)
    _down = (1, 5, 7, 8, 9, 6, 10, 2, 11, 12, 0, 3, 4)

    _tips = (
        'Enable Start Timer (time to start playback).',
        'Absolute time to start playback.',
        'Absolute time to start playback.',
        'Start playback XX:XX:XX after the time "OK" is pressed',
        'Start playback XX:XX:XX after the time "OK" is pressed',
        'Enable Stop Timer (time to stop playback).',
        'Absolute time to stop playback.',
        'Absolute time to stop playback.',
        'Stop playback XX:XX:XX after the time "OK" is pressed.',
        'Stop playback XX:XX:XX after the time "OK" is pressed.',
        'Remove this schedule.',
        'Save changes to this schedule item.',
        'Cancel changes to this schedule item.'
    )
    def __init__(
            self, parent,
            playlist=None, station=None,
            schedule_item=None,
            global_functions={}
    ):
        self._playlist = playlist
        self._station = station
        self._maxX = 60
        self._displacement = 3
        self._maxY = 14
        self._global_functions = global_functions
        self._get_parent(parent)
        self._focus = 9
        if schedule_item is None:
            pl = self._playlist
            if pl is None:
                pl = ''
            st = self._station
            if st is None:
                st = ''
            ''' create a schedule item '''
            a_date = datetime.now() + timedelta(hours=1)
            a_date_str = a_date.strftime('%Y-%m-%d %H:%M:%S')
            logger.error('a_date_str = "{}"'.format(a_date_str))
            it_str = 'E`|`' + a_date_str + '`|`A`|`' + a_date_str + '`|`A`|`'  + pl + '`|`' + st
            logger.error('{}'.format(it_str))
            self._schedule_item = PyRadioScheduleItem()
            self._schedule_item.set_item(it_str)
            self._focus = 6
            self._remove_enabled = False
        else:
            self._schedule_item = schedule_item
            self._remove_enabled = True

        ''' parse and assign values '''

    def _move_widgets(self):
        self._widgets[0].move(3 + self._Y, 5 + self._X)
        self._widgets[1].move(4 + self._Y, 9 + self._X)
        self._widgets[2].move(3 + self._Y, self._widgets[1].X + self._widgets[1].width)
        self._widgets[3].move(4 + self._Y, self._widgets[2].X + self._widgets[2].width + 4)
        self._widgets[4].move(3 + self._Y, self._widgets[3].X + self._widgets[3].width)
        self._widgets[5].move(6 + self._Y, 5 + self._X)
        self._widgets[6].move(4 + self._displacement + self._Y, 9 + self._X)
        self._widgets[7].move(3 + self._displacement + self._Y, self._widgets[6].X + self._widgets[6].width)
        self._widgets[8].move(4 + self._displacement + self._Y, self._widgets[7].X + self._widgets[7].width + 4)
        self._widgets[9].move(3 + self._displacement + self._Y, self._widgets[8].X + self._widgets[8].width)
        self._widgets[10].move(6 + self._displacement + self._Y, self._X + 2)
        self._widgets[11].move(self._widgets[10].Y, self._X + self._maxX - 19)
        self._widgets[12].move(self._widgets[10].Y, self._X + self._maxX - (len(self._widgets[12].caption) + 6))

    def _get_parent(self, parent):
        self._parent = parent
        self._parent_maxY, self._parent_maxX = parent.getmaxyx()
        new_Y = int((self._parent_maxY - self._maxY) / 2) + 1
        new_X = int((self._parent_maxX - self._maxX) / 2)
        if self._Y != new_Y or self._X != new_X:
            self._Y = new_Y
            self._X = new_X
        self._win = curses.newwin(self._maxY, self._maxX, self._Y, self._X)
        self._init_win()

    def _init_win(self):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        self._print_header()

    def _print_header(self):
        msg = ' Simple Scheduling '
        self._win.addstr(
            0, int((self._maxX - len(msg)) / 2),
            msg, curses.color_pair(11)
        )

    def move(self, new_Y=None, new_X=None):
        if new_Y:
            self._Y = new_Y
        if new_X:
            self._X = new_X
        if self._win:
            self._win.mvwin(self._Y, self._X)

    def show(self, parent=None):
        if parent:
            self._get_parent(parent)
            if self._showed:
                self._move_widgets()

        if self._widgets == None:
            self._widgets = []
            ''' id 0 start check box '''
            self._widgets.append(
                SimpleCursesCheckBox(
                    3 + self._Y, 5 + self._X, 'Start playback: ',
                    curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
                )
            )
            self._widgets[-1].w_id = 0

            ''' id 1 start at check box '''
            self._widgets.append(
                SimpleCursesCheckBox(
                    4 + self._Y, 9 + self._X, 'At: ',
                    curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
                )
            )
            self._widgets[-1].w_id = 1

            ''' id 2 start at time '''
            self._widgets.append(
                SimpleCursesTime(
                    Y=3 + self._Y, X=self._widgets[-1].X + self._widgets[-1].width,
                    window=self._win,
                    color=curses.color_pair(10),
                    show_am_pm=True,
                    color_focused=curses.color_pair(9),
                    next_widget_func=self._next_widget,
                    previous_widget_func=self._previous_widget,
                    global_functions=self._global_functions
                )
            )
            self._widgets[-1].w_id = 2

            ''' id 3 start in check box '''
            self._widgets.append(
                SimpleCursesCheckBox(
                    4 + self._Y,
                    self._widgets[-1].X + self._widgets[-1].width + 4, 'In: ',
                    curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
                )
            )
            self._widgets[-1].w_id = 3

            ''' id 4 start in time '''
            self._widgets.append(
                SimpleCursesTime(
                    Y=3 + self._Y, X=self._widgets[-1].X + self._widgets[-1].width,
                    window=self._win,
                    color=curses.color_pair(10),
                    color_focused=curses.color_pair(9),
                    next_widget_func=self._next_widget,
                    previous_widget_func=self._previous_widget,
                    global_functions=self._global_functions,
                    string='00:00:00'
                )
            )
            self._widgets[-1].w_id = 4

            ''' id 5 stop check box '''
            self._widgets.append(
                SimpleCursesCheckBox(
                    6 + self._Y, 5 + self._X, 'End playback: ',
                    curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
                )
            )
            self._widgets[-1].w_id = 5

            ''' id 6 stop at check box '''
            self._widgets.append(
                SimpleCursesCheckBox(
                    4 + self._displacement + self._Y, 9 + self._X, 'At: ',
                    curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
                )
            )
            self._widgets[-1].w_id = 6

            ''' id 7 stop at time '''
            self._widgets.append(
                SimpleCursesTime(
                    Y=3 + self._displacement + self._Y,
                    X=self._widgets[-1].X + self._widgets[-1].width,
                    window=self._win,
                    show_am_pm=True,
                    color=curses.color_pair(10),
                    color_focused=curses.color_pair(9),
                    next_widget_func=self._next_widget,
                    previous_widget_func=self._previous_widget,
                    global_functions=self._global_functions,
                    string=PyRadioTime.pyradio_time_to_string(self._schedule_item.end_time)
                )
            )
            self._widgets[-1].w_id = 7

            ''' id 8 stop in check box '''
            self._widgets.append(
                SimpleCursesCheckBox(
                    4 + self._displacement + self._Y,
                    self._widgets[-1].X + self._widgets[-1].width + 4, 'In: ',
                    curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
                )
            )
            self._widgets[-1].w_id = 8

            ''' id 9 stop in time '''
            self._widgets.append(
                SimpleCursesTime(
                    Y=3 + self._displacement + self._Y,
                    X=self._widgets[-1].X + self._widgets[-1].width,
                    window=self._win,
                    color=curses.color_pair(10),
                    color_focused=curses.color_pair(9),
                    next_widget_func=self._next_widget,
                    previous_widget_func=self._previous_widget,
                    global_functions=self._global_functions,
                    string='01:00:00'
                )
            )
            self._widgets[-1].w_id = 9

            ''' id 10 cancel scheduling button '''
            cap = 'Remove Schedule'
            self._widgets.append(SimpleCursesPushButton(
                Y=6 + self._displacement + self._Y,
                X=self._X + 2,
                caption=cap,
                color_focused=curses.color_pair(9),
                color=curses.color_pair(11),
                bracket_color=curses.color_pair(10),
                parent=self._parent))
            self._widgets[-1].w_id = 10

            ''' id 11 ok button '''
            cap = 'OK'
            self._widgets.append(SimpleCursesPushButton(
                Y=6 + self._displacement + self._Y,
                X=self._X + self._maxX - 19,
                caption=cap,
                color_focused=curses.color_pair(9),
                color=curses.color_pair(11),
                bracket_color=curses.color_pair(10),
                parent=self._parent))
            self._widgets[-1].w_id = 11

            ''' id 12 cancel button '''
            cap = 'Cancel'
            self._widgets.append(SimpleCursesPushButton(
                Y=6 + self._displacement + self._Y,
                X=self._X + self._maxX - (len(cap) + 6),
                caption=cap,
                color_focused=curses.color_pair(9),
                color=curses.color_pair(11),
                bracket_color=curses.color_pair(10),
                parent=self._parent))
            self._widgets[-1].w_id = 12

        try:
            self._win.addstr(self._maxY-3, 2, '─' * (self._maxX - 4), curses.color_pair(3))
        except:
            self._win.addstr(self._maxY-3, 2, '─'.encode('utf-8') * (self._maxX - 4), curses.color_pair(3))
        self._win.addstr(self._maxY-3, 3, ' Tip ', curses.color_pair(11))
        disp_msg = self._tips[self._focus]
        if self._focus in (4, 9) and \
                not self._stop_only():
            disp_msg = self._tips[self._focus].replace('the time "OK" is pressed.', 'starting playback.')
        self._win.addstr(self._maxY-2, 2, disp_msg.ljust(self._maxX-4), curses.color_pair(10))


        self._win.refresh()
        if self._widgets:
            if not self._showed:
                self._dummy_enable()
            self._fix_focus()
            for n, i in enumerate(self._widgets):
                try:
                    i.show(self._parent)
                except:
                    i.show()

        self._win.addstr(1, 2, 'Playlist: ', curses.color_pair(10))
        stop_only = self._stop_only()
        occupied = self._maxX -4 - len('Playlist: ')
        if stop_only:
            disp_playlist = 'Any Playlist'
        else:
            disp_playlist = cjkslices(self._playlist, occupied)[0]
        self._win.addstr(disp_playlist.ljust(occupied), curses.color_pair(11))

        occupied = self._maxX -4 - len('Station: ')
        self._win.addstr(2, 2, 'Station: ', curses.color_pair(10))
        if self._stop_only():
            disp_station = 'Any Station'
        else:
            if self._station:
                disp_station = cjkslices(self._station, occupied)[0]
            else:
                disp_station = 'Any Station'
        self._win.addstr(disp_station.ljust(occupied), curses.color_pair(11))
        self._win.refresh()

        self._showed = True

    def _dummy_enable(self):
        if self._schedule_item.type == 'E':
            self._widgets[0].enabled = True
            self._widgets[0].checked = False
            self._widgets[5].enabled = True
            self._widgets[5].checked = True
            for i in range(1, 5):
                self._widgets[i].enabled = False
            for i in range(6, 10):
                self._widgets[i].enabled = True
            if self._schedule_item.end_type == 'A':
                self._widgets[6].checked = True
                self._focus = 6
            else:
                self._widgets[9].checked = True
                self._focus = 9
            self._widgets[10].enabled = self._remove_enabled
        else:
            self._widgets[0].checked = True
            self._widgets[1].checked = True
            self._widgets[4].enabled = False

            self._widgets[5].checked = True
            self._widgets[8].checked = True
            self._widgets[7].enabled = False

            self._widgets[10].enabled = False

    def _stop_only(self):
        if ((not self._widgets[0].checked) and \
                self._widgets[5].checked) or \
                (not (self._widgets[0].checked and self._widgets[5].checked)):
            return True
        return False

    def _fix_focus(self):
        for i in (0, 5):
            for k in range(1, 5):
                self._widgets[i+k].enabled = self._widgets[i].checked

        self._widgets[-2].enabled = self._widgets[0].checked or self._widgets[5].checked

        for i in (1, 3, 6, 8):
            if self._widgets[i].enabled:
                self._widgets[i+1].enabled = self._widgets[i].checked

        for i in range(0, len(self._widgets)):
            if self._focus == i:
                self._widgets[i].focused = True
            else:
                self._widgets[i].focused = False

    def _next_widget(self):
        old_focus = self._focus
        self._focus += 1
        if self._focus >= len(self._widgets):
            self._focus = 0

        while(not self._widgets[self._focus].enabled):
            self._focus += 1

        if self._focus in (2, 4, 7, 9):
            self._widgets[self._focus].reset_selection()
        self.show()

    def _previous_widget(self):
        self._focus -= 1
        if self._focus < 0:
            self._focus = len(self._widgets) - 1

        while(not self._widgets[self._focus].enabled):
            self._focus -= 1
            if self._focus == -1:
                self._focus = len(self._widgets) -1

        if self._focus in (2, 4, 7, 9):
            self._widgets[self._focus].reset_selection(last=True)
        self.show()

    def keypress(self, char):
        '''
        PyRadioSimpleScheduleWindow keypress

        Return
        ======
            -1: Cancel
             0: Continue
             1: Get result
             2: Remove Schedule
             2: Show Help
        '''
        if char in self._global_functions.keys():
            self._global_functions[char]()
            return 0

        elif char == ord('?'):
            return 2

        elif char in (curses.KEY_EXIT, ord('q'), 27):
            return -1

        elif char in (ord('j'), curses.KEY_UP):
            self._focus = self._up[self._focus]
            while not self._widgets[self._focus].enabled:
                self._focus = self._up[self._focus]
            if self._focus in (2, 4, 7, 9):
                self._widgets[self._focus].reset_selection()

        elif char in (ord('k'), curses.KEY_DOWN):
            self._focus = self._down[self._focus]
            while not self._widgets[self._focus].enabled:
                self._focus = self._down[self._focus]
            if self._focus in (2, 4, 7, 9):
                self._widgets[self._focus].reset_selection()

        elif char in (9, ord('L')):
            if self._widgets[self._focus].w_id in (2, 4, 7, 9):
                self._widgets[self._focus].keypress(char)
            else:
                self._next_widget()

        elif char in (curses.KEY_BTAB, ord('H')):
            if self._widgets[self._focus].w_id in (2, 4, 7, 9):
                self._widgets[self._focus].keypress(char)
            else:
                self._previous_widget()

        else:
            ret = self._widgets[self._focus].keypress(char)
            if self._widgets[self._focus].w_id == 12 \
                    and not ret:
                ''' Cancel '''
                return -1
            elif self._widgets[self._focus].w_id == 11 \
                    and not ret:
                ''' OK '''
                return 1
            elif self._widgets[self._focus].w_id == 10 \
                    and not ret:
                ''' Remove schedule '''
                return 2
            elif self._widgets[self._focus].w_id in (2, 4, 7, 9):
                ''' Time
                      -1: Cancel
                       0: Continue
                       1: Show help
                '''
                pass

            else:
                ''' Check Boxes '''
                if self._widgets[self._focus].checked:
                    if self._focus == 1:
                        self._widgets[3].checked = False
                    elif self._focus == 3:
                        self._widgets[1].checked = False
                    elif self._focus == 6:
                        self._widgets[8].checked = False
                    elif self._focus == 8:
                        self._widgets[6].checked = False
                else:
                    if self._focus == 1:
                        self._widgets[3].checked = True
                    elif self._focus == 3:
                        self._widgets[1].checked = True
                    elif self._focus == 6:
                        self._widgets[8].checked = True
                    elif self._focus == 8:
                        self._widgets[6].checked = True

        self.show()
        return 0

if __name__ == '__main__':

    pass
    # x = PyRadioTime.pyradio_time_diference_in_seconds(
    #     [1, 10, 15], [1, 12, 20]
    # )
    # print(x)
    # print(PyRadioTime.seconds_to_sting(x))
    # exit()

    # old = datetime.now()
    # now = old + timedelta(seconds=1*60 + 10)

    # import time
    # import os
    # while True:
    #     d = now - old
    #     old = datetime.now()
    #     os.system('clear')
    #     print('Remaining:', PyRadioTime.delta_to_sting(d))
    #     if old >= now:
    #         break
    #     time.sleep(.5)

