'''AMP Custom Math Module
	Author: Alex Pronschinske
	Version: 1
	
	List of Classes: -none-
	List of Functions:
		fermat_factors
		get_primes
		round
		meanstd
		logit
		invlogit
		binoCoef
		fDist
		hist
		linfit
		rowElim
'''

import math
import urllib2
import os
import re

def fermat_factors(N):
	a = math.ceil(math.sqrt(N))
	b = math.sqrt( a*a - N )
	n_steps = 1
	while b != int(b):
		a += 1
		b = math.sqrt( a*a - N )
		n_steps += 1
	# END while
	
	print '{} steps to completion'.format(n_steps)
	return (a-b, a+b)
# END fermat_factors

def get_primes():
	'''Get a List of the First 1,000 Prime Numbers
	
	Args: -none-
	Returns:
		list.
	'''
	
	f = open('./first1000primes.txt')
	ftxt = f.read()
	f.close()
	
	return re.findall(r'\d+', ftxt, re.DOTALL)
# END get_primes

def round(x, d=0):
	if d != 0:
		x = x*10**d
	
	if (x - math.floor(x)) >= 0.5:
		x = math.floor(x) + 1
	else:
		x = math.floor(x)
	
	if d != 0:
		return x/10**d
	else:
		return x

def meanstd(X):
	xsum = 0.0
	xsumsq = 0.0
	n = len(X)
	for x in X:
		xsum += x
		xsumsq += x*x
	mean = xsum / n
	std = math.sqrt((xsumsq/n) - (mean*mean))
	
	return [mean, std]

def logit(x):
	return math.log(x / (1 - x))

def invlogit(x):
	return 1 / (1 + math.exp(-1*x))

def binoCoef(n, k):
	out = 1
	if 0 < k < n:
		if (n-k) <= k:
			l = (n-k)
		else:
			l = k
		
		for i in range(0, l): out = out * (n-i)/(1+i)
	elif k == n: out = 1
	else: out = 0
	
	return out

def fDist(X, nbins):
	Y = [[0]*nbins, [0]*nbins]
	xmin = X[0]
	xmax = X[0]
	for x in X:
		if x < xmin:
			xmin = x
		elif x > xmax:
			xmax = x
	
	xsize = (xmax-xmin) / float(nbins)
	
	for i in range(0,nbins):
		Y[0][i] = xmin + (i + 0.5)*xsize
	
	for x in X:
		q = int((x - xmin) / xsize)
		if q >= len(Y[1]): q = len(Y[1]) - 1
		Y[1][q] += 1
	
	return Y

def hist(Xin, nbins, fileName):
	X = fDist(Xin, nbins)
	
	urlstr = 'http://chart.apis.google.com/chart?'
	urlstr += 'cht=bvs&'
	urlstr += 'chs=600x500&'
	urlstr += 'chxt=x,y&'
	#urlstr += 'chxl=0:'
	#for x in X[0]:
	#    urlstr += '|{0:.3f}'.format(x)
	#urlstr += '&'
	
	urlstr += 'chd=t:'
	ymax = 0
	for y in X[1]:
		urlstr += str(y) + ','
		if y > ymax: ymax = y
	urlstr = urlstr[:-1] + '&'
	urlstr += 'chds=0,' + str(ymax) + '&'
	urlstr += 'chxr=0,{0:.3f},{1:.3f}|1,0,{2}'.format(X[0][0], X[0][-1], ymax)
	
	#print urlstr
	img = urllib2.urlopen(urlstr)
	f = open(fileName + '.png', 'w')
	f.write(img.read())
	f.close()
	img.close()
	os.system('eog ' + fileName + '.png')

def linfit(X, Y, eY=None, full_output=False):
	'''Weighted Linear Best-Fit
	
	Args:
		X (list):
		Y (list):
		eY (list|float|int):
		full_output (bool):
	Returns:
		
	'''
	
	if type(X) != list and type(X).__name__ != 'ndarray':
		raise TypeError('X data must be a list or ndarray')
	if type(Y) != list and type(Y).__name__ != 'ndarray':
		raise TypeError('Y data must be a list or ndarray')
	
	n = len(X)
	
	if len(Y) != n:
		raise ValueError('X and Y lists must be the same length')
	
	if eY is None:
		pass
	elif type(eY) == int or type(eY) == float:
		eY = [eY for i in range(0,n)]
	elif type(eY) != list and type(eY).__name__ != 'ndarray':
		raise TypeError('Data error must be an int, float, list, or a ndarray')
	# END if
	
	sx = 0.0
	sx2 = 0.0
	sy = 0.0
	sy2 = 0.0
	sxy = 0.0
	
	if eY is None:
		sw = n
		for i in range(n):
			sx += X[i]
			sx2 += X[i]*X[i]
			sy += Y[i]
			sy2 += Y[i]*Y[i]
			sxy += Y[i]*X[i]
	else:
		for i in range(n):
			sw += 1.0/(eY[i]**2)
			sx += X[i]/(eY[i]**2)
			sx2 += X[i]*X[i]/(eY[i]**2)
			sy += Y[i]/(eY[i]**2)
			sy2 += Y[i]*Y[i]
			sxy += Y[i]*X[i]/(eY[i]**2)
		# END for
	# END if
	
	delta = sw*sx2 - sx*sx
	a = (sw*sxy - sx*sy) / delta
	b = (sx2*sy - sx*sxy) / delta
	
	if not full_output:
		return (a, b)
	
	if eY is None:
		ssxy = sxy - sx*sy/n
		ssxx = sx2 - sx*sx/n
		ssyy = sy2 - sy*sy/n
		Rsqr = ssxy*ssxy / (ssxx*ssyy)
		return (a, b, Rsqr)
	else:
		chisqr = 0.0
		for i in range(n):
			chisqr += ( (Y[i] - a*X[i] - b)/eY[i] )**2
		# END for
		reduc_chisqr = chisqr/(n-2)
		
		a_err = sw/delta
		b_err = sx2/delta
		return (a, b, a_err, b_err, reduc_chisqr)
	# END if
# END linfit

def rowElim(X):
	L = len(X)
	Y = [[X[i][j] for j in range(0,L)] for i in range(0,L)]
	tol = 1E-12
	
	for i in range(0,L):
		a = Y[i][i]
		if abs(a) <= tol:
			Y[i][i] = 0.0
			continue
		
		for j in range(0,L):
			Y[i][j] = Y[i][j] / a
		
		# DEBUG CODE
		#print 'Y ='
		#for row in Y:
		#    print row
		
		for k in range(i+1,L):
			b = Y[k][i]
			for j in range(0,L):
				Y[k][j] -= b*Y[i][j]
		
		# DEBUG CODE
		#print 'Y ='
		#for row in Y:
		#    print row
	
	return Y
# END rowElim






