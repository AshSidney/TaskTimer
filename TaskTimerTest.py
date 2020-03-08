import unittest
from TaskTimer import *
import time
import io
import os.path
import tempfile


class DataIO(io.StringIO):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.result = ''

  def close(self):
    self.result = self.getvalue()
    super().close()


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
    data = DataIO('''{ "tasks" : [ {"name" : "SDC-001", "reportedTime" : 0.0, "active" : true},
      {"name" : "SDC-002", "reportedTime" : 780.0, "active" : false} ],
      "times" : [ { "name" : "SDC-001", "time" : [2020, 2, 26, 7, 43, 0, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 11, 21, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 26, 11, 50, 45, 2, 57, -1] } ] }''')
    taskData = TasksData(data)
    self.assertRaises(ValueError, data.getvalue)
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

  def test_TasksDataFromJsonReactivateTask(self):
    beforeTime = int(time.time())
    data = DataIO('''{ "tasks" : [ {"name" : "SDC-001", "reportedTime" : 0.0, "active" : true},
      {"name" : "SDC-002", "reportedTime" : 780.0, "active" : true} ],
      "times" : [ { "name" : "SDC-001", "time" : [2020, 2, 26, 7, 43, 0, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 26, 11, 21, 30, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 11, 50, 45, 2, 57, -1] } ] }''')
    taskData = TasksData(data)
    self.assertRaises(ValueError, data.getvalue)
    self.assertEqual(len(taskData.tasks), 2)
    self.assertEqual(taskData.tasks[0].name, 'SDC-001')
    self.assertEqual(taskData.tasks[0].reportedTime, 0.0)
    self.assertTrue(taskData.tasks[0].active)
    self.assertEqual(taskData.tasks[1].name, 'SDC-002')
    self.assertEqual(taskData.tasks[1].reportedTime, 780.0)
    self.assertTrue(taskData.tasks[1].active)
    self.assertEqual(len(taskData.times), 4)
    self.assertEqual(taskData.times[0].name, 'SDC-001')
    self.assertEqual(taskData.times[0].time, time.struct_time((2020, 2, 26, 7, 43, 0, 2, 57, -1)))
    self.assertEqual(taskData.times[1].name, 'SDC-002')
    self.assertEqual(taskData.times[1].time, time.struct_time((2020, 2, 26, 11, 21, 30, 2, 57, -1)))
    self.assertEqual(taskData.times[2].name, None)
    self.assertEqual(taskData.times[2].time, time.struct_time((2020, 2, 26, 11, 50, 45, 2, 57, -1)))
    self.assertEqual(taskData.times[3].name, 'SDC-002')
    self.assertGreaterEqual(taskData.times[3].getTime(), beforeTime)
    self.assertLessEqual(taskData.times[3].getTime(), time.time())

  def test_TasksDataToJson(self):
    taskData = TasksData()
    self.assertEqual(taskData.tasks, [])
    self.assertEqual(taskData.times, [])
    taskData.tasks = [TaskState({'name' : 'SDC-007', 'reportedTime' : 100.0, 'active' : True}),
                      TaskState({'name' : 'SDC-008', 'reportedTime' : 47.0, 'active' : False})]
    taskData.times = [TaskTime({'name' : None, 'time' : [2020, 2, 25, 11, 2, 0, 1, 56, -1]}),
                      TaskTime({'name' : 'SDC-007', 'time' : [2020, 2, 25, 12, 26, 0, 1, 56, -1]})]
    jsonData = DataIO()
    taskData.save(jsonData)
    self.assertRaises(ValueError, jsonData.getvalue)
    testData = json.loads(jsonData.result)
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

  def test_TasksDataGetLastTask(self):
    data = io.StringIO('''{ "tasks" : [ { "name" : "SDC-001", "reportedTime" : 15000.0, "active" : true },
      { "name" : "SDC-002", "reportedTime" : 0.0, "active" : false } ],
      "times" : [ { "name" : "SDC-001", "time" : [2020, 2, 26, 7, 43, 0, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 11, 21, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 26, 11, 50, 45, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 16, 42, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 27, 7, 10, 0, 3, 58, -1] },
      { "name" : "SDC-001", "time" : [2020, 2, 27, 9, 55, 0, 3, 58, -1] } ] }''')
    taskData = TasksData(data)
    self.assertEqual(taskData.getLastTask(), 'SDC-001')
    data = io.StringIO('''{ "tasks" : [ { "name" : "SDC-001", "reportedTime" : 15000.0, "active" : true },
      { "name" : "SDC-002", "reportedTime" : 0.0, "active" : true } ],
      "times" : [ { "name" : "SDC-001", "time" : [2020, 2, 26, 7, 43, 0, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 11, 21, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 26, 11, 50, 45, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 16, 42, 30, 2, 57, -1] } ] }''')
    taskData = TasksData(data)
    self.assertEqual(taskData.getLastTask(), 'SDC-002')
    data = io.StringIO('''{ "tasks" : [ { "name" : "SDC-001", "reportedTime" : 15000.0, "active" : true },
      { "name" : "SDC-002", "reportedTime" : 0.0, "active" : false } ],
      "times" : [ { "name" : "SDC-001", "time" : [2020, 2, 26, 7, 43, 0, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 11, 21, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 26, 11, 50, 45, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 16, 42, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 27, 7, 10, 0, 3, 58, -1] } ] }''')
    taskData = TasksData(data)
    self.assertEqual(taskData.getLastTask(), '')

  def test_TasksDataGetActiveTasks(self):
    data = io.StringIO('''{ "tasks" : [ { "name" : "SDC-001", "reportedTime" : 150.0, "active" : true },
      { "name" : "SDC-002", "reportedTime" : 78.0, "active" : false },
      { "name" : "SDC-005", "reportedTime" : 0.0, "active" : true } ],
      "times" : [] }''')
    taskData = TasksData(data)
    self.assertEqual(taskData.getActiveTasks(), ['SDC-001', 'SDC-005'])

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

  def test_TasksDataGetTaskTimeTillNow(self):
    currTime = int(time.time())
    task1Time = time.localtime(currTime - 10 * 3600)
    task2Time = time.localtime(currTime - 4 * 3600)
    data = io.StringIO('''{ "tasks" : [ { "name" : "SDC-001", "reportedTime" : 0.0, "active" : true },
      { "name" : "SDC-002", "reportedTime" : 0.0, "active" : true } ],
      "times" : [ { "name" : "SDC-001", "time" : ['''
      + str(task1Time.tm_year) + ', ' + str(task1Time.tm_mon) + ', ' + str(task1Time.tm_mday) + ', '
      + str(task1Time.tm_hour) + ', ' + str(task1Time.tm_min) + ', ' + str(task1Time.tm_sec) + ', '
      + str(task1Time.tm_wday) + ', ' + str(task1Time.tm_yday) + ', ' + str(task1Time.tm_isdst) + '''] },
      { "name" : "SDC-002", "time" : ['''
      + str(task2Time.tm_year) + ', ' + str(task2Time.tm_mon) + ', ' + str(task2Time.tm_mday) + ', '
      + str(task2Time.tm_hour) + ', ' + str(task2Time.tm_min) + ', ' + str(task2Time.tm_sec) + ', '
      + str(task2Time.tm_wday) + ', ' + str(task2Time.tm_yday) + ', ' + str(task2Time.tm_isdst) + '] } ] }')
    taskData = TasksData(data)
    fullTime1 = taskData.getTaskTimeTillNow('SDC-001')
    fullTime2 = taskData.getTaskTimeTillNow('SDC-002')
    timeOffset = time.time() - currTime
    self.assertEqual(fullTime1, 6 * 3600)
    self.assertGreaterEqual(fullTime2, 4 * 3600)
    self.assertLessEqual(fullTime2, 4 * 3600 + timeOffset)

  def test_TasksDataUpdateTaskTime(self):
    data = io.StringIO('''{ "tasks" : [ { "name" : "SDC-001", "reportedTime" : 15000.0, "active" : true },
      { "name" : "SDC-002", "reportedTime" : 0.0, "active" : false } ],
      "times" : [] }''')
    taskData = TasksData(data)
    taskData.updateTaskTime('SDC-001', 600.0)
    self.assertEqual(taskData.find('SDC-001').reportedTime, 15600.0)
    taskData.updateTaskTime('SDC-002', 2400.0)
    self.assertEqual(taskData.find('SDC-002').reportedTime, 2400.0)
    taskData.updateTaskTime('SDC-XXX', 5000.0)
    self.assertEqual(len(taskData.tasks), 2)
    self.assertEqual(taskData.find('SDC-001').reportedTime, 15600.0)
    self.assertEqual(taskData.find('SDC-002').reportedTime, 2400.0)

  def test_DataFileForLoadAndSave(self):
    with tempfile.TemporaryDirectory() as tempDir:
      nonExistingFile = DataFile(os.path.join(tempDir, 'nonExisting.json'))
      self.assertEqual(nonExistingFile.forLoad(), None)
      testFileName = os.path.join(tempDir, 'testData.json')
      dataFile = DataFile(testFileName)
      with dataFile.forSave() as fileToSave:
        self.assertNotEqual(fileToSave, None)
        json.dump({'first' : 123, 'second' : 'just string'}, fileToSave)
      self.assertTrue(os.path.exists(testFileName))
      with dataFile.forLoad() as fileToLoad:
        self.assertNotEqual(fileToLoad, None)
        data = json.load(fileToLoad)
        self.assertEqual(len(data), 2)
        self.assertEqual(data['first'], 123)
        self.assertEqual(data['second'], 'just string')

  def test_TimeFormatterInit(self):
    format = TimeFormatter('dh', True)
    self.assertEqual(format.units, [('d', 8 * 3600), ('h', 3600)])
    self.assertEqual(format.order, [0, 1])
    format = TimeFormatter('hms', True)
    self.assertEqual(format.units, [('h', 3600), ('m', 60), ('s', 1)])
    self.assertEqual(format.order, [0, 1, 2])
    format = TimeFormatter('hmd', True)
    self.assertEqual(format.units, [('d', 8 * 3600), ('h', 3600), ('m', 60)])
    self.assertEqual(format.order, [2, 0, 1])

  def test_TimeFormatterRound(self):
    format = TimeFormatter('dh', True)
    self.assertEqual(format.round(4.1 * 3600), 5 * 3600)
    self.assertEqual(format.round(2.7 * 3600), 3 * 3600)
    self.assertEqual(format.round(7 * 3600), 7 * 3600)
    format = TimeFormatter('ms', True)
    self.assertEqual(format.round(15 * 60 + 51.2), 15 * 60 + 52)
    self.assertEqual(format.round(4 * 60 + 59.5), 5 * 60)

  def test_TimeFormatterSplit(self):
    format = TimeFormatter('dh', True)
    self.assertEqual(format.split(21 * 3600), [(2, 'd'), (5, 'h')])
    format = TimeFormatter('dhms', True)
    self.assertEqual(format.split(26 * 3600 + 34 * 60 + 12), [(3, 'd'), (2, 'h'), (34, 'm'), (12, 's')])
    self.assertEqual(format.split(5 * 3600 + 4 * 60), [(0, 'd'), (5, 'h'), (4, 'm'), (0, 's')])
    self.assertEqual(format.split(10 * 3600 + 26), [(1, 'd'), (2, 'h'), (0, 'm'), (26, 's')])

  def test_TimeFormatterTrim(self):
    format = TimeFormatter('d', True)
    self.assertEqual(format.trim([(2, 'd'), (10, 'h'), (0, 'm'), (0, 's')]), ([(2, 'd'), (10, 'h')], 0))
    self.assertEqual(format.trim([(0, 'd'), (10, 'h'), (0, 'm'), (42, 's')]), ([(10, 'h'), (0, 'm'), (42, 's')], 1))
    format = TimeFormatter('d', False)
    self.assertEqual(format.trim([(2, 'd'), (10, 'h'), (0, 'm'), (0, 's')]), ([(2, 'd'), (10, 'h'), (0, 'm'), (0, 's')], 0))
    self.assertEqual(format.trim([(0, 'd'), (10, 'h'), (0, 'm'), (42, 's')]), ([(10, 'h'), (0, 'm'), (42, 's')], 1))

  def test_TimeFormatterDaysHours(self):
    format = TimeFormatter('dh', True)
    self.assertEqual(format.get(5 * 3600), '5h')
    self.assertEqual(format.get(6.2 * 3600), '7h')
    self.assertEqual(format.get(12.7 * 3600), '1d 5h')
    self.assertEqual(format.get(15.9 * 3600), '2d')
    self.assertEqual(format.get(16.1 * 3600), '2d 1h')

  def test_TimeFormatterDaysHoursMinutesSeconds(self):
    format = TimeFormatter('dhms', False)
    self.assertEqual(format.get(4 * 3600 + 44 * 60 + 24.6), '4h 44m 25s')
    self.assertEqual(format.get(26 * 3600 + 10 * 60 + 51), '3d 2h 10m 51s')
    self.assertEqual(format.get(8 * 3600 + 5 * 60 + 59.1), '1d 0h 6m 0s')

  def test_TimeFormatterUnorderedDaysHours(self):
    format = TimeFormatter('hd', False)
    self.assertEqual(format.get(4.1 * 3600), '5h')
    self.assertEqual(format.get(27 * 3600 + 10 * 60), '4h 3d')
    self.assertEqual(format.get(8 * 3600), '0h 1d')


if __name__ == '__main__':
  unittest.main()
