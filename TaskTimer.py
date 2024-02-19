import tkinter
import tkinter.ttk
import time
import json
import pathlib
import os
import sys
import sqlite3
import datetime
import win32gui
import win32process
import win32api
import win32con
import win32ts


class TaskTimerApp(tkinter.Frame):
  def __init__(self, master=None):
    super().__init__(master)
    self.db = TaskTimeDb('-bg' in sys.argv)
    self.initSessionWatch()
    self.configFile = DataFile('config.json')
    config = self.configFile.forLoad()
    if config is not None:
      self.master.geometry(json.load(config)['position'])
    
    self.master.title('Task Timer')
    self.master.grid_rowconfigure(0, weight=1)
    self.master.grid_columnconfigure(0, weight=1)
    self.grid(column=0, row=0, sticky=tkinter.NSEW)

    self.master.protocol('WM_DELETE_WINDOW', self.finish)

    self.dataFile = DataFile('tasksData.json')
    self.tasks = TasksData(self.dataFile.forLoad())
    self.workstationActive = True

    lastTask = self.tasks.getLastTask()
    self.currentTask = tkinter.StringVar()
    self.currentTask.set(lastTask)
    self.currentTaskLabel = tkinter.ttk.Label(self, textvariable=self.currentTask, font=('Helvetica', 16))
    self.currentTaskLabel.grid(column=0, row=0)
    self.currentTime = tkinter.StringVar()
    self.currentTimeLabel = tkinter.ttk.Label(self, textvariable=self.currentTime, font=('Helvetica', 14))
    self.currentTimeLabel.grid(column=1, row=0, columnspan=2)
    self.currentTimeFormat = TimeFormatter('hms', False)
    self.taskBox = tkinter.ttk.Combobox(self, values=self.tasks.getActiveTasks())
    self.taskBox.set(lastTask)
    self.taskBox.grid(column=0, row=1)
    self.setTaskButton = tkinter.Button(self, text='Set Selected Task', command=self.setTask)
    self.setTaskButton.grid(column=1, row=1, columnspan=2)
    self.copyTimeButton = tkinter.Button(self, text='Copy Time', command=self.copyTime)
    self.copyTimeButton.grid(column=1, row=2)
    self.deleteTaskButton = tkinter.Button(self, text='Delete Task', command=self.deleteTask)
    self.deleteTaskButton.grid(column=2, row=2)
    self.keepWhenClosedButton = tkinter.Button(self, text='Keep Timing When Closed', command=self.keepTiming, relief=self.getKeepTimingButtonRelief())
    self.keepWhenClosedButton.grid(column=0, row=2)

    self.repeatedRefresh()

  def initSessionWatch(self):
    hwnd = self.master.winfo_id()
    win32ts.WTSRegisterSessionNotification(hwnd, win32ts.NOTIFY_FOR_ALL_SESSIONS)
    self.defaultProc = win32gui.SetWindowLong(hwnd, win32con.GWL_WNDPROC, self.winProc)

  def winProc(self, hWnd, msg, wParam, lParam):
    WM_WTSSESSION_CHANGE = 0x2B1
    if msg == WM_WTSSESSION_CHANGE:
      self.db.addEvent(self.db.closeId if wParam == 7 else self.db.openId)
    return win32gui.CallWindowProc(self.defaultProc, hWnd, msg, wParam, lParam)
  
  def save(self):
    self.tasks.save(self.dataFile.forSave())

  def finish(self):
    self.db.close()
    self.save()
    with self.configFile.forSave() as config:
      json.dump({'position' : '+' + str(self.master.winfo_x()) + '+' + str(self.master.winfo_y())}, config)
    self.master.destroy()

  def refresh(self):
    self.currentTime.set(str(self.db.getTodayWorkTime() - self.db.getLunchTime()))

  def repeatedRefresh(self):
    self.checkLock()
    if self.workstationActive:
      self.refresh()
    self.after(1000, self.repeatedRefresh)

  def checkLock(self):
    if self.workstationActive == self.isWorkstationLocked():
      self.workstationActive = not self.workstationActive
      self.save()
      if self.workstationActive:
        self.tasks.continueLastTask()
        self.setKeepTimingButtonRelief()

  def setTask(self):
    newTask = self.taskBox.get()
    self.tasks.add(newTask)
    self.currentTask.set(newTask)
    self.taskBox['values'] = self.tasks.getActiveTasks()
    self.refresh()

  def copyTime(self):
    task = self.taskBox.get()
    taskTime = self.tasks.getTaskTime(task)
    self.tasks.updateTaskTime(task, taskTime)
    self.master.clipboard_clear()
    self.master.clipboard_append(TimeFormatter('dh', True).get(taskTime))

  def deleteTask(self):
    self.tasks.remove(self.taskBox.get())
    self.taskBox.set('')
    self.taskBox['values'] = self.tasks.getActiveTasks()
    self.refresh()

  def keepTiming(self):
    self.tasks.keepTimingWhenOff = not self.tasks.keepTimingWhenOff
    self.setKeepTimingButtonRelief()

  def getKeepTimingButtonRelief(self):
    return 'sunken' if self.tasks.keepTimingWhenOff else 'raised'

  def setKeepTimingButtonRelief(self):
    self.keepWhenClosedButton.config(relief=self.getKeepTimingButtonRelief())

  def isWorkstationLocked(self):
    windowId = win32gui.GetForegroundWindow()
    if windowId == 0:
      return True
    thrid, pid = win32process.GetWindowThreadProcessId(windowId)
    try:
      handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
      fileName = win32process.GetModuleFileNameEx(handle, 0)
      return'LockApp' in fileName
    except Exception:
      return False


class TaskTimeDb:
  def __init__(self, background, dbName = 'TaskTimer.db'):
    self.openId = 'open'
    self.closeId = 'close'
    self.lunchId = 'lunch'
    if dbName == ':memory:':
      self.dataConn = sqlite3.connect(dbName)
    else:
      dataDir = pathlib.Path('data')
      if not dataDir.exists():
        os.mkdir(dataDir)
      self.dataConn = sqlite3.connect(dataDir / dbName)
    curs = self.dataConn.cursor()
    noEventTable = curs.execute('SELECT * FROM sqlite_master WHERE type = "table" AND name = "Event"').fetchone() is None
    if noEventTable:
      curs.execute('CREATE TABLE Event(id TEXT, time TEXT)')
    self.addEvent(self.closeId if background else self.openId)

  def close(self):
    self.addEvent(self.closeId)
  
  def addEvent(self, id):
    lastId = self.dataConn.cursor().execute('SELECT id, time, rowid FROM Event ORDER BY time DESC, rowid DESC').fetchone()
    if lastId is not None and lastId[0] != id or lastId is None and id != self.closeId:
      self.dataConn.cursor().execute('INSERT INTO Event(id, time) VALUES(:id, datetime("now", "localtime"))', {'id' : id})
      self.dataConn.commit()
      self.setLunchTime()

  def getTodayWorkTime(self):
    curs = self.dataConn.cursor()
    lastData = curs.execute('SELECT id, time, datetime("now", "localtime") FROM Event ORDER BY time DESC').fetchone()
    if lastData is None:
      return datetime.timedelta(0)
    lastTime = lastData[1] if lastData[0] == self.closeId else lastData[2]
    startTime = curs.execute('SELECT time FROM Event WHERE date(time) = date(:last) AND id != :closeId ORDER BY time',
      {'last' : lastTime, 'closeId' : self.closeId}).fetchone()
    if startTime is None:
      return datetime.timedelta(0)
    return datetime.datetime.fromisoformat(lastTime) - datetime.datetime.fromisoformat(startTime[0])

  def getDayWorkTime(self, day):
    curs = self.dataConn.cursor()
    startTime = curs.execute('SELECT time FROM Event WHERE date(time) = :day AND id != :closeId ORDER BY time',
      {'day' : day.isoformat(), 'closeId' : self.closeId}).fetchone()
    lastTime = curs.execute('SELECT time FROM Event WHERE date(time) = :day AND id = :closeId ORDER BY time DESC',
      {'day' : day.isoformat(), 'closeId' : self.closeId}).fetchone()
    if startTime is None or lastTime is None:
      return datetime.timedelta(0)
    return datetime.datetime.fromisoformat(lastTime[0]) - datetime.datetime.fromisoformat(startTime[0])

  def getLunchTime(self, day=None):
    if day is None:
      day = datetime.date.today()
    curs = self.dataConn.cursor()
    startTime = curs.execute('SELECT time FROM Event WHERE date(time) = :day AND id = :lunchId ORDER BY time',
      {'day' : day.isoformat(), 'lunchId' : self.lunchId}).fetchone()
    if startTime is not None:
      lastTime = curs.execute('SELECT time FROM Event WHERE time > :lunchTime ORDER BY time',
        {'lunchTime' : startTime[0]}).fetchone()
      if lastTime is not None:
        return datetime.datetime.fromisoformat(lastTime[0]) - datetime.datetime.fromisoformat(startTime[0])
    return datetime.timedelta(0)

  def setLunchTime(self):
    lunchStartTime = datetime.date.today().isoformat() + ' 11:00:00'
    curs = self.dataConn.cursor()
    lunchData = curs.execute('SELECT id, time FROM Event WHERE time >= :lunchTime ORDER BY time', {'lunchTime' : lunchStartTime}).fetchone()
    if lunchData is not None:
      lunchTime = None
      if lunchData[0] == self.closeId:
        lunchTime = lunchData[1]
      else:
        lunchData = curs.execute('SELECT id, time FROM Event WHERE time < :lunchTime ORDER BY time DESC', {'lunchTime' : lunchStartTime}).fetchone()
        if lunchData is not None and lunchData[0] == self.closeId:
          lunchTime = lunchData[1]
      if lunchTime is not None:
        curs.execute('UPDATE Event SET id = :lunchId WHERE id = :closeId AND time = :time',
          {'lunchId' : self.lunchId, 'closeId' : self.closeId, 'time' : lunchTime})
    self.dataConn.commit()


class TaskState(object):
  def __init__(self, data):
    if isinstance(data, dict):
      self.name = data['name']
      self.reportedTime = data['reportedTime']
      self.active = data['active']
    else:
      self.name = data
      self.reportedTime = 0.0
      self.active = True


class TaskTime(object):
  timeProvider = time.localtime

  def __init__(self, data):
    if isinstance(data, dict):
      self.name = data['name']
      self.time = time.struct_time(tuple(data['time']))
    else:
      self.name = data
      self.time = TaskTime.timeProvider()

  def getTime(self):
    return time.mktime(self.time)


class TasksData(object):
  def __init__(self, dataFile=None):
    self.keepTimingWhenOff = False
    if dataFile is None:
      self.tasks = []
      self.times = []
    else:
      with dataFile as source:
        data = json.load(source)
        self.tasks = [TaskState(item) for item in data['tasks']]
        self.times = [TaskTime(item) for item in data['times']]
        self.continueLastTask()

  def save(self, dataFile):
    if self.keepTimingWhenOff:
      self.keepTimingWhenOff = False
    else:
      self.add(None)
    with dataFile as target:
      json.dump({ 'tasks' : [item.__dict__ for item in self.tasks], 'times' : [item.__dict__ for item in self.times] }, target)

  def find(self, task):
    for item in self.tasks:
      if item.name == task:
        return item
    return None

  def add(self, task):
    if task is not None and self.find(task) is None:
      self.tasks.append(TaskState(task))
    self.times.append(TaskTime(task))

  def remove(self, task):
    item = self.find(task)
    if item is not None:
      item.active = False

  def getLastTask(self):
    for index in range(len(self.times) - 1, -1, -1):
      if self.times[index].name is not None:
        item = self.find(self.times[index].name)
        if item is not None and item.active:
          return item.name
        break
    return ''

  def continueLastTask(self):
    lastTask = self.getLastTask()
    if lastTask != '' and self.times[-1].name is None:
      self.add(lastTask)

  def getActiveTasks(self):
    return [item.name for item in self.tasks if item.active]

  def getTaskTime(self, task):
    item = self.find(task)
    sumTime = -item.reportedTime if item is not None else 0.0
    for previous, current in zip(self.times[:-1], self.times[1:]):
      if previous.name == task:
        sumTime += current.getTime() - previous.getTime()
    return sumTime

  def getTaskTimeTillNow(self, task):
    sumTime = self.getTaskTime(task)
    if len(self.times) > 0 and self.times[-1].name == task:
      sumTime += time.time() - self.times[-1].getTime()
    return sumTime

  def updateTaskTime(self, task, time):
    item = self.find(task)
    if item is not None:
      item.reportedTime += time


class DataFile(object):
  def __init__(self, fileName):
    self.fileName = fileName

  def forLoad(self):
    try:
      return open(self.fileName, 'r')
    except:
      return None

  def forSave(self):
    return open(self.fileName, 'w')


class TimeFormatter(object):
  def __init__(self, format, trimZeros):
    self.units = []
    self.order = []
    self.trimZeros = trimZeros
    for unit in (('d', 8 * 3600), ('h', 3600), ('m', 60), ('s', 1)):
      index = format.find(unit[0])
      if index >= 0:
        self.units.append(unit)
        self.order.append(index)

  def round(self, value):
    divisor = self.units[-1][1]
    return value if value % divisor == 0 else (int(value / divisor) + 1) * divisor

  def split(self, value):
    values = []
    for unit in self.units:
      unitValue = int(value / unit[1])
      value -= unitValue * unit[1]
      values.append((unitValue, unit[0]))
    return values

  def trim(self, values):
    first = -1 if self.trimZeros else 0
    last = len(values)
    for item in enumerate(values):
      if item[1][0] > 0:
        if first < 0:
          first = item[0]
        if self.trimZeros:
          last = item[0] + 1
    return values[first:last], first

  def get(self, timeValue):
    values, offset = self.trim(self.split(self.round(timeValue)))
    sortedValues = sorted(zip(self.order[offset:], values), key=lambda item : item[0])
    return ' '.join(str(item[1][0]) + item[1][1] for item in sortedValues)


if __name__ == '__main__':
  root = tkinter.Tk()
  app = TaskTimerApp(master=root)
  app.mainloop()
