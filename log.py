"""This module provids a simple logging/output interface."""
import time
from logging import *
from enlib import memory, colors
from mpi4py import MPI

class EnFilter(Filter):
	def __init__(self, rank=0):
		self.rank = rank
		try:
			# Try to get actual time since task start if possible
			import os, psutil
			p = psutil.Process(os.getpid())
			self.t0 = p.create_time()
		except ImportError:
			# Otherwise measure from creation of this filter
			self.t0 = time.time()
	def filter(self, record):
		record.rank  = self.rank
		record.wtime = time.time()-self.t0
		record.wmins = record.wtime/60.
		record.whours= record.wmins/60.
		record.mem   = memory.current()/1024.**3
		record.memmax= memory.max()/1024.**3
		return record

class QuietOthers(Filter):
	def __init__(self, rank=0, which=(INFO,)):
		self.rank  = rank
		self.which = which
	def filter(self, record):
		if self.rank == 0 or record.levelno not in self.which:
			return record

class ColoredFormatter(Formatter):
	def __init__(self, msg, colors={'DEBUG':colors.reset,'INFO':colors.lgreen,'WARNING':colors.lbrown,'ERROR':colors.lred, 'CRITICAL':colors.lpurple}):
		Formatter.__init__(self, msg)
		self.colors = colors
	def format(self, record):
		try:
			col = self.colors[record.levelname]
		except KeyError:
			col = colors.reset
		return col + Formatter.format(self, record) + colors.reset

default_format = "%(rank)3d %(wmins)7.2f %(mem)5.2f %(memmax)5.2f %(message)s"

def init(level=INFO, rank=MPI.COMM_WORLD.rank, file=None, fmt=default_format, color=True):
	"""Set up the root logger for output to console and file. Extra output records
	for mpi rank, time since process start and memory usage are added by default.
	Console output is colored by default, and info-level messages are muted from
	others than root for console output. File output is done independently for each
	task. If file-name can be a format string, which is then used as file%rank
	to produce the output file. Otherwise, a different output file must be passed
	for each mpi task. If file is None (the default), no file output is produced.
	The console level threshold is set by the level argument, which must be a
	python logging module level. The threshold does not apply to file output, where
	everything is output."""
	logger  = getLogger("")
	logger.setLevel(DEBUG)
	if file:
		try:
			oname = file % rank
		except:
			oname = file
		fh = FileHandler(oname)
		fh.setLevel(DEBUG)
		fh.addFilter(EnFilter(rank))
		formatter = Formatter(fmt)
		fh.setFormatter(formatter)
		logger.addHandler(fh)
	fclass = ColoredFormatter if color else Formatter
	ch = StreamHandler()
	ch.setLevel(level)
	ch.setFormatter(fclass(fmt))
	ch.addFilter(EnFilter(rank))
	ch.addFilter(QuietOthers(rank))
	logger.addHandler(ch)
	return logger

def verbosity2level(verbosity):
	if verbosity <= 0: return ERROR
	if verbosity <= 1: return INFO
	return DEBUG