import tkinter
import tkinter.ttk
import time
import json
import math


class TaskTimerApp(tkinter.Frame):
  def __init__(self, master=None):
    super().__init__(master)
    master.grid_rowconfigure(0, weight=1)
    master.grid_columnconfigure(0, weight=1)
    self.grid(column=0, row=0, sticky=tkinter.NSEW)

    self.dataFile = DataFile('tasksData.json')
    self.tasks = TasksData(self.dataFile.forLoad())

    lastTask = self.tasks.getLastTask()
    self.currentTask = tkinter.StringVar()
    self.currentTask.set(lastTask)
    self.currentTaskLabel = tkinter.ttk.Label(self, textvariable=self.currentTask, font=('Helvetica', 16))
    self.currentTaskLabel.grid(column=0, row=0)
    self.currentTime = tkinter.StringVar()
    self.currentTimeLabel = tkinter.ttk.Label(self, textvariable=self.currentTime, font=('Helvetica', 14))
    self.currentTimeLabel.grid(column=1, row=0)
    self.taskBox = tkinter.ttk.Combobox(self, values=self.tasks.getActiveTasks())
    self.taskBox.set(lastTask)
    self.taskBox.grid(column=0, row=1)
    self.setTaskButton = tkinter.Button(self, text='Set', command=self.setTask)
    self.setTaskButton.grid(column=1, row=1)

    self.repeatedRefresh()

  def finish(self):
    self.tasks.add(None)
    self.tasks.save(self.dataFile.forSave())

  def refresh(self):
    format = TimeFormatter('dhms')
    self.currentTime.set(format.get(self.tasks.getTaskTimeTillNow(self.currentTask.get())))

  def repeatedRefresh(self):
    self.refresh()
    self.after(1000, self.repeatedRefresh)

  def setTask(self):
    newTask = self.taskBox.get()
    self.tasks.add(newTask)
    self.currentTask.set(newTask)
    self.refresh()


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
  def __init__(self, data):
    if isinstance(data, dict):
      self.name = data['name']
      self.time = time.struct_time(tuple(data['time']))
    else:
      self.name = data
      self.time = time.localtime()

  def getTime(self):
    return time.mktime(self.time)


class TasksData(object):
  def __init__(self, dataFile=None):
    if dataFile is None:
      self.tasks = []
      self.times = []
    else:
      with dataFile as source:
        data = json.load(source)
        self.tasks = [TaskState(item) for item in data['tasks']]
        self.times = [TaskTime(item) for item in data['times']]
        lastTask = self.getLastTask()
        if lastTask != '' and self.times[-1].name is None:
          self.add(lastTask)

  def save(self, dataFile):
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
  def __init__(self, format, trimRight):
    self.units = []
    self.order = []
    self.trimRight = trimRight
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
    first = -1
    last = len(values)
    for item in enumerate(values):
      if item[1][0] > 0:
        if first < 0:
          first = item[0]
        if self.trimRight:
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
  app.finish()