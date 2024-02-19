import unittest
from TaskTimer import *
import time
import io
import os.path
import tempfile
import datetime


class Test_TaskTimeDb(unittest.TestCase):
  def setUp(self):
    self.memDb = ':memory:'
    self.dbDir = pathlib.Path('data')
    self.dbName = 'testDb.db'
    self.fullDb = self.dbDir / self.dbName
    self.fullDb.unlink(True)

  def tearDown(self):
    self.fullDb.unlink(True)

  def test_initDb(self):
    db = TaskTimeDb(False, self.dbName)
    self.assertEqual(1, db.dataConn.cursor().execute('SELECT COUNT(*) FROM Event').fetchone()[0])
    db.close()
    self.assertEqual(2, db.dataConn.cursor().execute('SELECT COUNT(*) FROM Event').fetchone()[0])

  def test_initDb_background(self):
    db = TaskTimeDb(True, self.dbName)
    self.assertEqual(0, db.dataConn.cursor().execute('SELECT COUNT(*) FROM Event').fetchone()[0])
    db.close()
    self.assertEqual(0, db.dataConn.cursor().execute('SELECT COUNT(*) FROM Event').fetchone()[0])

  def test_initDb_existing(self):
    db = TaskTimeDb(False, self.dbName)
    db.addEvent('testEvent')
    data = db.dataConn.cursor().execute('SELECT id FROM Event').fetchall()
    self.assertEqual([('open',),('testEvent',)], data)
    db.close()
    del db
    db = TaskTimeDb(True, self.dbName)
    data = db.dataConn.cursor().execute('SELECT id FROM Event').fetchall()
    self.assertEqual([('open',),('testEvent',),('close',)], data)

  def fillTestData(self, db, data):
    today = datetime.date.today().isoformat()
    for item in data:
      time = item[1] if item[1][4] == '-' else today + ' ' + item[1]
      db.dataConn.cursor().execute('INSERT INTO Event (id, time) VALUES (?, ?)', (item[0], time))
    db.dataConn.commit()

  def test_getTodayWorkTime(self):
    db = TaskTimeDb(True, self.memDb)
    self.fillTestData(db, (('open', '07:32:45'), ('close', '10:32:04'),
                           ('open', '10:25:21'), ('close', '11:02:47')))
    self.assertEqual(db.getTodayWorkTime(), datetime.timedelta(hours=3, minutes=30, seconds=2))

  def test_getDayWorkTime(self):
    db = TaskTimeDb(True, self.memDb)
    self.fillTestData(db, (('open', '2023-10-17 07:10:25'), ('close', '2023-10-17 11:05:14'),
                           ('open', '2023-10-17 11:45:21'), ('close', '2023-10-17 16:02:30'),
                           ('open', '2023-10-18 07:51:00'), ('close', '2023-10-18 15:47:00'),
                           ('open', '2023-10-19 09:00:35'), ('close', '2023-10-19 17:34:57')))
    self.assertEqual(db.getDayWorkTime(datetime.date(2023, 10, 17)), datetime.timedelta(hours=8, minutes=52, seconds=5))
    self.assertEqual(db.getDayWorkTime(datetime.date(2023, 10, 18)), datetime.timedelta(hours=7, minutes=56, seconds=0))
    self.assertEqual(db.getDayWorkTime(datetime.date(2023, 10, 19)), datetime.timedelta(hours=8, minutes=34, seconds=22))
    self.assertEqual(db.getDayWorkTime(datetime.date(2023, 10, 20)), datetime.timedelta(0))

  def test_setLunchTime(self):
    db = TaskTimeDb(True, self.memDb)
    self.fillTestData(db, (('open', '07:12:36'), ('close', '11:02:10'), ('open', '11:36:12'), ('close', '15:31:47')))
    db.setLunchTime()
    self.assertEqual(db.getLunchTime(), datetime.timedelta(minutes=34, seconds=2))

  def test_setLunchTime_before11(self):
    db = TaskTimeDb(True, self.memDb)
    self.fillTestData(db, (('open', '07:27:00'), ('close', '10:50:00'), ('open', '11:24:15'), ('close', '12:10:00'), ('open', '12:45:00'), ('close', '14:40:00')))
    db.setLunchTime()
    self.assertEqual(db.getLunchTime(), datetime.timedelta(minutes=34, seconds=15))


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
    TaskTime.timeProvider = lambda : time.struct_time((2020, 2, 25, 8, 12, 0, 1, 56, -1))
    task1 = TaskTime('SDC-099')
    TaskTime.timeProvider = lambda : time.struct_time((2020, 2, 25, 12, 20, 0, 1, 56, -1))
    task2 = TaskTime('SDC-001')
    TaskTime.timeProvider = lambda : time.struct_time((2020, 2, 25, 14, 52, 30, 1, 56, -1))
    idle = TaskTime(None)
    self.assertEqual(task1.name, 'SDC-099')
    self.assertEqual(task2.name, 'SDC-001')
    self.assertEqual(idle.name, None)
    self.assertEqual(task1.time, time.struct_time((2020, 2, 25, 8, 12, 0, 1, 56, -1)))
    self.assertEqual(task2.time, time.struct_time((2020, 2, 25, 12, 20, 0, 1, 56, -1)))
    self.assertEqual(idle.time, time.struct_time((2020, 2, 25, 14, 52, 30, 1, 56, -1)))

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
    self.assertFalse(taskData.keepTimingWhenOff)
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
    TaskTime.timeProvider = lambda : time.struct_time((2020, 2, 26, 15, 32, 0, 1, 56, -1))
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
    self.assertFalse(taskData.keepTimingWhenOff)
    self.assertEqual(len(taskData.times), 4)
    self.assertEqual(taskData.times[0].name, 'SDC-001')
    self.assertEqual(taskData.times[0].time, time.struct_time((2020, 2, 26, 7, 43, 0, 2, 57, -1)))
    self.assertEqual(taskData.times[1].name, 'SDC-002')
    self.assertEqual(taskData.times[1].time, time.struct_time((2020, 2, 26, 11, 21, 30, 2, 57, -1)))
    self.assertEqual(taskData.times[2].name, None)
    self.assertEqual(taskData.times[2].time, time.struct_time((2020, 2, 26, 11, 50, 45, 2, 57, -1)))
    self.assertEqual(taskData.times[3].name, 'SDC-002')
    self.assertEqual(taskData.times[3].time, time.struct_time((2020, 2, 26, 15, 32, 0, 1, 56, -1)))

  def test_TasksDataToJson(self):
    taskData = TasksData()
    self.assertEqual(taskData.tasks, [])
    self.assertEqual(taskData.times, [])
    taskData.tasks = [TaskState({'name' : 'SDC-007', 'reportedTime' : 100.0, 'active' : True}),
                      TaskState({'name' : 'SDC-008', 'reportedTime' : 47.0, 'active' : False})]
    taskData.times = [TaskTime({'name' : None, 'time' : [2020, 2, 25, 11, 2, 0, 1, 56, -1]}),
                      TaskTime({'name' : 'SDC-007', 'time' : [2020, 2, 25, 12, 26, 0, 1, 56, -1]})]
    taskData.keepTimingWhenOff = True
    jsonData = DataIO()
    taskData.save(jsonData)
    self.assertFalse(taskData.keepTimingWhenOff)
    self.assertRaises(ValueError, jsonData.getvalue)
    testData = json.loads(jsonData.result)
    self.assertEqual(testData, {'tasks' : [{'name' : 'SDC-007', 'reportedTime' : 100.0, 'active' : True},
                                           {'name' : 'SDC-008', 'reportedTime' : 47.0, 'active' : False}],
                               'times' : [{'name' : None, 'time' : [2020, 2, 25, 11, 2, 0, 1, 56, -1]},
                                          {'name' : 'SDC-007', 'time' : [2020, 2, 25, 12, 26, 0, 1, 56, -1]}] })

  def test_TasksDataToJson_NotKeepingTimingAfterSave(self):
    TaskTime.timeProvider = lambda : time.struct_time((2020, 2, 25, 18, 43, 0, 2, 56, -1))
    taskData = TasksData()
    self.assertEqual(taskData.tasks, [])
    self.assertEqual(taskData.times, [])
    taskData.tasks = [TaskState({'name' : 'SDC-007', 'reportedTime' : 100.0, 'active' : True}),
                      TaskState({'name' : 'SDC-008', 'reportedTime' : 47.0, 'active' : False})]
    taskData.times = [TaskTime({'name' : None, 'time' : [2020, 2, 25, 11, 2, 0, 1, 56, -1]}),
                      TaskTime({'name' : 'SDC-007', 'time' : [2020, 2, 25, 12, 26, 0, 1, 56, -1]})]
    jsonData = DataIO()
    taskData.save(jsonData)
    self.assertFalse(taskData.keepTimingWhenOff)
    self.assertRaises(ValueError, jsonData.getvalue)
    testData = json.loads(jsonData.result)
    self.assertEqual(testData, {'tasks' : [{'name' : 'SDC-007', 'reportedTime' : 100.0, 'active' : True},
                                           {'name' : 'SDC-008', 'reportedTime' : 47.0, 'active' : False}],
                               'times' : [{'name' : None, 'time' : [2020, 2, 25, 11, 2, 0, 1, 56, -1]},
                                          {'name' : 'SDC-007', 'time' : [2020, 2, 25, 12, 26, 0, 1, 56, -1]},
                                          {'name' : None, 'time' : [2020, 2, 25, 18, 43, 0, 2, 56, -1]}] })

  def test_TasksDataAddCurrentTask(self):
    taskData = TasksData()
    TaskTime.timeProvider = lambda : time.struct_time((2020, 2, 26, 7, 43, 0, 2, 57, -1))
    taskData.add('SDC-011')
    TaskTime.timeProvider = lambda : time.struct_time((2020, 2, 26, 9, 11, 0, 2, 57, -1))
    taskData.add(None)
    TaskTime.timeProvider = lambda : time.struct_time((2020, 2, 26, 9, 16, 0, 2, 57, -1))
    taskData.add('SDC-011')
    self.assertEqual(len(taskData.tasks), 1)
    self.assertEqual(taskData.tasks[0].name, 'SDC-011')
    self.assertEqual(taskData.tasks[0].reportedTime, 0.0)
    self.assertTrue(taskData.tasks[0].active)
    self.assertEqual(len(taskData.times), 3)
    self.assertEqual(taskData.times[0].name, 'SDC-011')
    self.assertEqual(taskData.times[0].time, time.struct_time((2020, 2, 26, 7, 43, 0, 2, 57, -1)))
    self.assertEqual(taskData.times[1].name, None)
    self.assertEqual(taskData.times[0].time, time.struct_time((2020, 2, 26, 7, 43, 0, 2, 57, -1)))
    self.assertEqual(taskData.times[2].name, 'SDC-011')
    self.assertEqual(taskData.times[0].time, time.struct_time((2020, 2, 26, 7, 43, 0, 2, 57, -1)))

  def test_TasksDataRemoveTask(self):
    data = io.StringIO('''{ "tasks" : [ { "name" : "SDC-001", "reportedTime" : 150.0, "active" : true },
      { "name" : "SDC-002", "reportedTime" : 78.0, "active" : false } ],
      "times" : [ { "name" : "SDC-001", "time" : [2020, 2, 26, 7, 43, 0, 2, 57, -1] },
      { "name" : null, "time" : [2020, 2, 26, 11, 21, 30, 2, 57, -1] },
      { "name" : "SDC-002", "time" : [2020, 2, 26, 11, 50, 45, 2, 57, -1] } ],
      "keepTimingWhenOff" : false }''')
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
    self.assertEqual(format.trim([(0, 'd'), (10, 'h'), (0, 'm'), (42, 's')]), ([(0, 'd'), (10, 'h'), (0, 'm'), (42, 's')], 0))

  def test_TimeFormatterDaysHours(self):
    format = TimeFormatter('dh', True)
    self.assertEqual(format.get(5 * 3600), '5h')
    self.assertEqual(format.get(6.2 * 3600), '7h')
    self.assertEqual(format.get(12.7 * 3600), '1d 5h')
    self.assertEqual(format.get(15.9 * 3600), '2d')
    self.assertEqual(format.get(16.1 * 3600), '2d 1h')

  def test_TimeFormatterDaysHoursMinutesSeconds(self):
    format = TimeFormatter('dhms', False)
    self.assertEqual(format.get(4 * 3600 + 44 * 60 + 24.6), '0d 4h 44m 25s')
    self.assertEqual(format.get(26 * 3600 + 10 * 60 + 51), '3d 2h 10m 51s')
    self.assertEqual(format.get(8 * 3600 + 5 * 60 + 59.1), '1d 0h 6m 0s')

  def test_TimeFormatterUnorderedDaysHours(self):
    format = TimeFormatter('hd', False)
    self.assertEqual(format.get(4.1 * 3600), '5h 0d')
    self.assertEqual(format.get(27 * 3600 + 10 * 60), '4h 3d')
    self.assertEqual(format.get(8 * 3600), '0h 1d')


if __name__ == '__main__':
  unittest.main()
