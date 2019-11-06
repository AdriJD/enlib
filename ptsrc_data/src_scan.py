"""This module deals with a Scan variant for point source analysis.
It is not a subclass of Scan as it makes incompatible assumptions,
and things are stored more explicitly."""
from __future__ import division, print_function
import numpy as np, h5py

# This compressed format is quite complicated, but is basically a
# source-centric representation of the flattened tod. This flattened
# tod is divided into ranges[nrange,2] of contiguous samples.
# Each source shows up in a set of ranges rangesets[offsets[source,0]:offsets[source[1]]].
# rangesets would not be needed if all ranges of a course were
# consecutive. But because several sources may share the same range,
# this is impossible.
#
# This data structure is quite cumbersome and error prone to
# work with. For example, removing a source or removing samples
# is difficult.
#
# point is the celestial pointing of each sample. This presents
# a problem if we switch to focalplane coordinates, as we then
# would need separate pointing for each source.

class SrcScan:
	def __init__(self, tod, point, phase, ranges, rangesets, offsets, ivars, dets, rbox=None, nbox=None, ys=None, point_offset=None):
		self.tod     = tod
		self.point   = point
		self.phase   = phase
		self.ranges  = ranges
		self.rangesets=rangesets
		self.offsets = offsets
		self.ivars   = ivars
		self.dets    = dets
		self.rbox    = rbox
		self.nbox    = nbox
		self.ys      = ys
		self.point_offset = point_offset
	@property
	def shape(self): return (self.offsets.shape[:2])
	def __str__(self): return "SrcScan(nsrc=%d,ndet=%d,nsamp=%d)" % (self.offsets.shape[0],self.offsets.shape[1],self.tod.size)
	def __getitem__(self, sel):
		if type(sel) != tuple:
			sel = (sel,)
		sel = sel + (slice(None),)*(2-len(sel))
		nsrc, ndet = self.offsets.shape[:2]
		srcs = np.arange(nsrc)[sel[0]]
		dets = np.arange(ndet)[sel[1]]
		return self.select(srcs, dets)
	def select(self, srcs, dets):
		"""Extract a new SrcScan for the specified srcs and dets,
		eliminating ranges that are no longer needed."""
		if np.all(dets==np.arange(len(self.dets))) and np.all(srcs==np.arange(self.offsets.shape[0])):
			return self
		# 1. First slice offsets and rangesets
		rangesets = []
		nset = 0
		offsets = np.zeros([len(srcs),len(dets),2],dtype=np.int32)
		for si, src in enumerate(srcs):
			for di, det in enumerate(dets):
				o1,o2 = self.offsets[src,det]
				offsets[si,di,0] = nset
				rangesets.append(self.rangesets[o1:o2])
				nset += o2-o1
				offsets[si,di,1] = nset
		rangesets = np.concatenate(rangesets).astype(np.int32)
		# 2. Then determine which ranges are no longer used, and
		# a mappings between old and new ranges
		used = np.zeros(len(self.ranges),dtype=bool)
		used[rangesets] = True
		rmap  = np.nonzero(used)[0]
		irmap = np.zeros(len(self.ranges),dtype=np.int32)
		irmap[rmap] = np.arange(len(rmap))
		# 3. Extract valid ranges and update rangesets
		ranges = self.ranges[rmap]
		rangesets = irmap[rangesets]
		# 4. Extract our actual samples while updating ranges
		n = np.sum(ranges[:,1]-ranges[:,0])
		tod   = self.tod[:n].copy()
		point = self.point[:n].copy()
		phase = self.phase[:n].copy()
		m = 0
		for ri in range(len(ranges)):
			i1,i2 = ranges[ri]
			o1,o2 = m,m+i2-i1
			tod  [o1:o2] = self.tod [i1:i2]
			point[o1:o2] = self.point[i1:i2]
			phase[o1:o2] = self.phase[i1:i2]
			ranges[ri] = [o1,o2]
			m = o2
		point_offset = self.point_offset
		if point_offset is not None:
			point_offset = point_offset[dets]
		return SrcScan(tod, point, phase, ranges, rangesets, offsets, self.ivars[dets], self.dets[dets], self.rbox, self.nbox, self.ys, point_offset)

def write_srcscan(fname, scan):
	with h5py.File(fname, "w") as hfile:
		for key in ["tod","point","phase","ranges","rangesets","offsets","ivars","dets","rbox","nbox","ys","point_offset"]:
			hfile[key] = getattr(scan, key)

def read_srcscan(fname):
	args = {}
	with h5py.File(fname, "r") as hfile:
		for key in ["tod","point","phase","ranges","rangesets","offsets","ivars","dets","rbox","nbox","ys","point_offset"]:
			if key in hfile:
				args[key] = hfile[key].value
	return SrcScan(**args)
