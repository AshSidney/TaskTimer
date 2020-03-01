import tkinter
import time
import json


class TaskTimerApp(tkinter.Frame):
  def __init__(self, master=None):
    super().__init__(master)
    self.pack()
    self.currentButton = tkinter.Button(self, text='Pokus')
    self.currentButton.pack()


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
      data = json.load(dataFile)
      self.tasks = [TaskState(item) for item in data['tasks']]
      self.times = [TaskTime(item) for item in data['times']]

  def save(self, data):
    json.dump({ 'tasks' : [item.__dict__ for item in self.tasks], 'times' : [item.__dict__ for item in self.times] }, data)

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

if __name__ == '__main__':
  root = tkinter.Tk()
  app = TaskTimerApp(master=root)
  app.mainloop()
