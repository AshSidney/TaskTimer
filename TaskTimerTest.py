import unittest
from TaskTimer import *
import time
import io


class Test_TaskTimerTest(unittest.TestCase):
  def test_TaskStateFromString(self):
    task = TaskState('SDC-012')
    self.assertEqual(task.name, 'SDC-012')
    self.assertEqual(task.reportedTime, 0.0)
    self.assertTrue(task.active)

  def test_TaskStateFromDict(self):
    task1 = TaskState({'name' : 'SDC-023', 'reportedTime' : 12300.0, 'active' : True})
    self.assertEqual(task1.name, 'SDC-023')
    self.assertEqual(task1.reportedTime, 12300.0)
    self.assertTrue(task1.active)
    task2 = TaskState({'name' : 'SDC-055', 'reportedTime' : 0.0, 'active' : False})
    self.assertEqual(task2.name, 'SDC-055')
    self.assertEqual(task2.reportedTime, 0.0)
    self.assertFalse(task2.active)

  def test_TaskStateToDict(self):
    task = TaskState({'name' : 'SDC-987', 'reportedTime' : 345.0, 'active' : True})
    self.assertEqual(task.__dict__, {'name' : 'SDC-987', 'reportedTime' : 345.0, 'active' : True})

  def test_TaskTimeFromString(self):
    timeBefore = time.time()
    task1 = TaskTime('SDC-099')
    time.sleep(2)
    task2 = TaskTime('SDC-001')
    time.sleep(2)
    idle = TaskTime(None)
    self.assertEqual(task1.name, 'SDC-099')
    self.assertEqual(task2.name, 'SDC-001')
    self.assertEqual(idle.name, None)
    self.assertLess(task1.time, task2.time)
    self.assertLess(task2.time, idle.time)

  def test_TaskTimeFromDict(self):
    task1 = TaskTime({'name' : 'SDC-987', 'time' : [2020, 2, 25, 8, 12, 0, 1, 56, -1]})
    self.assertEqual(task1.name, 'SDC-987')
    self.assertEqual(task1.time, time.struct_time((2020, 2, 25, 8, 12, 0, 1, 56, -1)))
    task2 = TaskTime({'name' : None, 'time' : [2020, 2, 25, 11, 3, 0, 1, 56, -1]})
    self.assertEqual(task2.name, None)
    self.assertEqual(task2.time, time.struct_time((2020, 2, 25, 11, 3, 0, 1, 56, -1)))
    self.assertEqual(task2.getTime() - task1.getTime(), 3 * 3600 - 9 * 60)

  def test_TaskTimeToDict(self):
    task = TaskTime({'name' : 'SDC-987', 'time' : [2020, 2, 25, 8, 12, 0, 1, 56, -1]})
    self.assertEqual(task.__dict__, {'name' : 'SDC-987', 'time' : time.struct_time((2020, 2, 25, 8, 12, 0, 1, 56, -1))})

  def test_TasksDataFromJson(self):
    data = io.StringIO('''{ "tasks" : [ {"name" : "SDC-001", "reportedTime" : 0.0, "active" : true},
      {"name" : "SDC-002", "reportedTime" : 780.0, "active" : false} ],
      "times" : [ { "name" : "SDC-001", "time" : [2020, 2, 26, 7, 43, 0, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 11, 21, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 26, 11, 50, 45, 2, 57, -1] } ] }''')
    taskData = TasksData(data)
    self.assertEqual(len(taskData.tasks), 2)
    self.assertEqual(taskData.tasks[0].name, 'SDC-001')
    self.assertEqual(taskData.tasks[0].reportedTime, 0.0)
    self.assertTrue(taskData.tasks[0].active)
    self.assertEqual(taskData.tasks[1].name, 'SDC-002')
    self.assertEqual(taskData.tasks[1].reportedTime, 780.0)
    self.assertFalse(taskData.tasks[1].active)
    self.assertEqual(len(taskData.times), 3)
    self.assertEqual(taskData.times[0].name, 'SDC-001')
    self.assertEqual(taskData.times[0].time, time.struct_time((2020, 2, 26, 7, 43, 0, 2, 57, -1)))
    self.assertEqual(taskData.times[1].name, None)
    self.assertEqual(taskData.times[1].time, time.struct_time((2020, 2, 26, 11, 21, 30, 2, 57, -1)))
    self.assertEqual(taskData.times[2].name, 'SDC-002')
    self.assertEqual(taskData.times[2].time, time.struct_time((2020, 2, 26, 11, 50, 45, 2, 57, -1)))
    self.assertEqual(taskData.times[1].getTime() - taskData.times[0].getTime(), 4 * 3600 - 22 * 60 + 30)
    self.assertEqual(taskData.times[2].getTime() - taskData.times[1].getTime(), 29 * 60 + 15)

  def test_TasksDataToJson(self):
    taskData = TasksData()
    self.assertEqual(taskData.tasks, [])
    self.assertEqual(taskData.times, [])
    taskData.tasks = [TaskState({'name' : 'SDC-007', 'reportedTime' : 100.0, 'active' : True}),
                      TaskState({'name' : 'SDC-008', 'reportedTime' : 47.0, 'active' : False})]
    taskData.times = [TaskTime({'name' : None, 'time' : [2020, 2, 25, 11, 2, 0, 1, 56, -1]}),
                      TaskTime({'name' : 'SDC-007', 'time' : [2020, 2, 25, 12, 26, 0, 1, 56, -1]})]
    jsonData = io.StringIO('')
    taskData.save(jsonData)
    testData = json.loads(jsonData.getvalue())
    self.assertEqual(testData, {'tasks' : [{'name' : 'SDC-007', 'reportedTime' : 100.0, 'active' : True},
                                           {'name' : 'SDC-008', 'reportedTime' : 47.0, 'active' : False}],
                               'times' : [{'name' : None, 'time' : [2020, 2, 25, 11, 2, 0, 1, 56, -1]},
                                          {'name' : 'SDC-007', 'time' : [2020, 2, 25, 12, 26, 0, 1, 56, -1]}]})

  def test_TasksDataAddCurrentTask(self):
    taskData = TasksData()
    taskData.add('SDC-011')
    time.sleep(2)
    taskData.add(None)
    time.sleep(1)
    taskData.add('SDC-011')
    self.assertEqual(len(taskData.tasks), 1)
    self.assertEqual(taskData.tasks[0].name, 'SDC-011')
    self.assertEqual(taskData.tasks[0].reportedTime, 0.0)
    self.assertTrue(taskData.tasks[0].active)
    self.assertEqual(len(taskData.times), 3)
    self.assertEqual(taskData.times[0].name, 'SDC-011')
    self.assertEqual(taskData.times[1].name, None)
    self.assertGreater(taskData.times[1].getTime(), taskData.times[0].getTime())
    self.assertEqual(taskData.times[2].name, 'SDC-011')
    self.assertGreater(taskData.times[2].getTime(), taskData.times[1].getTime())

  def test_TasksDataRemoveTask(self):
    data = io.StringIO('''{ "tasks" : [ { "name" : "SDC-001", "reportedTime" : 150.0, "active" : true },
      { "name" : "SDC-002", "reportedTime" : 78.0, "active" : false } ],
      "times" : [ { "name" : "SDC-001", "time" : [2020, 2, 26, 7, 43, 0, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 11, 21, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 26, 11, 50, 45, 2, 57, -1] } ] }''')
    taskData = TasksData(data)
    taskData.remove('SDC-003')
    self.assertEqual(len(taskData.tasks), 2)
    self.assertEqual(taskData.tasks[0].name, 'SDC-001')
    self.assertTrue(taskData.tasks[0].active)
    self.assertEqual(taskData.tasks[1].name, 'SDC-002')
    self.assertFalse(taskData.tasks[1].active)
    self.assertEqual(len(taskData.times), 3)
    taskData.remove('SDC-001')
    self.assertEqual(len(taskData.tasks), 2)
    self.assertEqual(taskData.tasks[0].name, 'SDC-001')
    self.assertFalse(taskData.tasks[0].active)
    self.assertEqual(taskData.tasks[1].name, 'SDC-002')
    self.assertFalse(taskData.tasks[1].active)
    self.assertEqual(len(taskData.times), 3)

  def test_TasksDataGetTaskTime(self):
    data = io.StringIO('''{ "tasks" : [ { "name" : "SDC-001", "reportedTime" : 15000.0, "active" : true },
      { "name" : "SDC-002", "reportedTime" : 0.0, "active" : false } ],
      "times" : [ { "name" : "SDC-001", "time" : [2020, 2, 26, 7, 43, 0, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 11, 21, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 26, 11, 50, 45, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 16, 42, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 27, 7, 10, 0, 3, 58, -1] },
      { "name" : "SDC-001", "time" : [2020, 2, 27, 9, 55, 0, 3, 58, -1] } ] }''')
    taskData = TasksData(data)
    self.assertEqual(taskData.getTaskTime('SDC-001'), 4 * 3600 - 22 * 60 + 30 - 15000.0)
    self.assertEqual(taskData.getTaskTime('SDC-002'), 5 * 3600 - 8 * 60 -15 + 2 * 3600 + 45 * 60)
    self.assertEqual(taskData.getTaskTime('SDC-003'), 0.0)


if __name__ == '__main__':
  unittest.main()
