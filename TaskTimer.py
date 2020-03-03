import tkinter
import tkinter.ttk
import time
import json


class TaskTimerApp(tkinter.Frame):
  def __init__(self, master=None):
    super().__init__(master)
    master.grid_rowconfigure(0, weight=1)
    master.grid_columnconfigure(0, weight=1)
    self.grid(column=0, row=0, sticky=tkinter.NSEW)

    self.currentTask = tkinter.ttk.Label(self, text='Pokus')
    self.currentTask.grid(column=0, row=0)


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


if __name__ == '__main__':
  root = tkinter.Tk()
  app = TaskTimerApp(master=root)
  app.mainloop()
