import sys
import inspect
import math
import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import scipy.signal as signal

from scikits.audiolab import Format, Sndfile


def analyze(filename):
	f = Sndfile(filename, 'r')
	fs = f.samplerate
	nc = f.channels
	enc = f.encoding
	nf = f.nframes

	print "Hz: %d ch: %d enc: %s frames: %d" % (fs, nc, enc, nf)
	#print inspect.getmembers(f)

	#data = f.read_frames(n, np.dtype('i2')).swapaxes(0,1)
	data = f.read_frames(nf).swapaxes(0,1)
	print np.abs(data).max()
	#print "max: %d %d val: %d %d" % (np.argmax(data[:,0]), np.argmax(data[:,1]), data[np.argmax(data[:,0]), 0], data[np.argmax(data[:,1]), 1])
	#print data[fs*2]
	#print data[fs*2,1]

	data_rms = rms(data) # [np.sqrt(np.mean(data[0]**2)), np.sqrt(np.mean(data[1]**2))]
	data_peak = np.abs(data).max(1)
	#plt.plot(data)
	#plt.show()
	#print data[0,100000:100010]
	#print data[0,100000:100010]**2
	#print np.mean(data[0,100000:100010]**2)
	#print np.sqrt(np.mean(data[0,100000:100010]**2))

	# Peak dBFS
	peak_dbfs = db(data_peak, 1.0) #[ 20*np.log10(np.abs(data[0]).max()), 20*np.log10(np.abs(data[1]).max()) ]

	# RMS dBFS
	rms_dbfs = db(data_rms, 1.0) # [ 20*np.log10(rms[0]), 20*np.log10(rms[1]) ]

	# Crest dB
	crest_db = db(data_peak, data_rms) # [ 20*np.log10(np.abs(data[0]).max() / rms[0]), 20*np.log10(np.abs(data[1]).max() / rms[1]) ]

	print "RMS", data_rms, "Peak", data_peak, "Peak dBFS", peak_dbfs, "RMS dBFS", rms_dbfs, "Crest dB", crest_db

	# Loudest
	window = int(fs / 50)
	peak = data_peak.max()
	sn_max = 0
	pos_max = 0
	c_max = 0
	sn_cur = 0
	"""for c in range(nc):
		for i, e in zip(range(n), np.abs(data[c])):
			if e > 0.95*peak:
				sn_cur = 0
				for j in range(window):
					if i+j < n and np.abs(data[c,i+j]) > peak*0.95:
						sn_cur += 1
				if sn_cur > sn_max:
					sn_max = sn_cur
					c_max = c
					pos_max = i
					print "intermediate max", sn_max, c_max, pos_max, pos_max/float(fs)
	print "final max", sn_max, c_max, pos_max, pos_max/float(fs)"""
	c_max, f_max, nf_cur, nf_max = 0, 0, 0, 0
	for c in range(nc):
		peaks = np.flatnonzero(np.abs(data[c]) > 0.95*peak)
		print(len(peaks))

		nf_cur = 0
		#for i, e in zip(range(len(peaks)), peaks):
		it = np.nditer(peaks, flags=['buffered','c_index'], op_flags=['readonly'])
		for e in it:
			i = it.iterindex
			#nf_cur = np.count_nonzero(peaks[i:] < e + window)
			nf_cur = (peaks[i:i+window] < e + window).sum()
			if nf_cur > nf_max:
				c_max = c
				nf_max = nf_cur
				f_max = e
	print c_max, nf_max, f_max, f_max/float(fs)

	#peaks = (np.abs(data) > 0.05*peak)
	#print np.sum(rolling_window(peaks, window), -1).max()

	# Spectrum
	print nf/float(fs)
	frames = nf/fs
	wfunc = np.blackman(fs)
	norm_spec = np.zeros(fs)
	tmp = np.zeros(fs)
	for i in np.arange(0, frames*fs, fs):
		#norm_spec += np.abs(np.fft.fft(np.multiply(data[0,i:i+fs], wfunc), fs))
		tmp = np.abs(np.fft.fft(np.multiply(data[0,i:i+fs], wfunc), fs))
		norm_spec += 20*np.log10(tmp/tmp.max())
	norm_spec /= frames
	#plt.plot(20*np.log10(norm_spec[np.arange(fs/2)]/norm_spec.max()))
	#plt.show()
	#plt.semilogx(np.arange(fs/2), norm_spec[0:fs/2], basex=10)
	#plt.show()

	# Allpass
	ap_freqs = [20, 60, 200, 600, 2000, 20000]
	ap_crest = np.zeros((len(ap_freqs),nc))
	ap_rms = np.zeros((len(ap_freqs),nc))
	ap_peak = np.zeros((len(ap_freqs),nc))
	"""x = np.zeros(16).reshape(4,2)#data.view().swapaxes(0,1)
	x[0,0] =
	y = np.zeros(x.shape)
	print 'x', x.flags
	print 'y', y.flags
	for freq in ap_freqs:
		b, a = allpass(freq, fs)
		y[0] = b[0]*x[0]
		print x[0]
		print y[0]
		it = np.nditer([x, y], flags=['buffered', 'c_index'], op_flags=[['readonly'],['readwrite']], order='C')
		print it.itersize
		it.iternext()
		for x_i, y_i in it:
			#y[i] = b[0]*x[i] + b[1]*x[i-1] - a[1]*y[i-1]
			i = it.iterindex
			y_i = b[0]*x_i + b[1]*x[i-1] - a[1]*y[i-1]
			if i <= 1 or i >= nf-2:
				print y[0:1], x[0:1], i"""
	for i in range(len(ap_freqs)):
		fc = ap_freqs[i]
		b, a = allpass(fc, fs)
		y = signal.lfilter(b, a, data, 1)
		ap_peak[i] = y.max(1)
		ap_rms[i] = rms(y)
		ap_crest[i] = db(ap_peak[i], ap_rms[i])
	print ap_crest

	# Histogram
	hist = np.zeros(nc*2**16).reshape(nc, 2**16)
	for c in range(nc):
		hist[c], tmp = np.histogram(data[c], bins=2**16, range=(-1.0, 1.0))
	print hist.shape
	hist_bits = np.log2((hist > 0).sum(1))
	print hist_bits


	# Peak vs RMS
	n_1s = int(np.ceil(nf/float(fs)))
	data_1s_peak = np.zeros((nc, n_1s))
	data_1s_rms = np.zeros((nc, n_1s))
	data_1s_crest = np.zeros((nc, n_1s))
	print n_1s

def rms(data):
	return np.sqrt((data**2).mean(1))

def db(a, b):
	return 20*np.log10(np.divide(a, b))

def allpass(fc, fs):
	T = 1.0/fs
	w_b = 2*np.pi*fc
	p_d = (1 - np.tan(w_b*T/2)) / (1 + np.tan(w_b*T/2))
	return ([p_d, -1], [1, -p_d])

def rolling_window(a, window):
	shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
	strides = a.strides + (a.strides[-1],)
	return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)


if __name__ == "__main__":
	if len(sys.argv) == 2:
		filename = sys.argv[1]
	else:
		print "Usage: %s filename" % sys.argv[0]
		exit()

	analyze(filename)