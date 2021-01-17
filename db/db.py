from os.path import isfile
from sqlite3 import connect

from apscheduler.triggers.cron import CronTrigger

DB_PATH = "./data/db/database.db"
BUILD_PATH = "./data/db/build.sql"

cxn = connect(DB_PATH, check_same_thread=False)
cur = cxn.cursor()


def with_commit(func):
	def inner(*args, **kwargs):
		func(*args, **kwargs)
		commit()

	return inner


@with_commit
def build():
	if isfile(BUILD_PATH):
		scriptexec(BUILD_PATH)


def commit():
	cxn.commit()

def scriptexec(path):
	with open(path, "r", encoding="utf-8") as script:
		cur.executescript(script.read())