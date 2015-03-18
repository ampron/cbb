'''Library of General-Purpose Custom Tools
	Author: Alex Pronschinske
	Version: 1
	
	List of Classes: -none-
	List of Functions:
		uniquify
		csvline_to_list
		csv2LD
		csv2html
		matchScore
		numConvert
		update
	Module dependencies: 
		math
		re
		time
'''

import re
import time
import math

#===============================================================================
def uniquify(A, evalFunc=None):
	'''This function will remove duplicate entries from a list
	'''
	
	if evalFunc == None:
		def evalFunc(x): return x
	# END if
	
	results = []
	seen = set()
	for item in A:
		if len(seen) == 0 or evalFunc(item) not in seen:
			seen.add(evalFunc(item))
			results.append(item)
			# END if
	# END for
	return results
# END uniquify

#===============================================================================
def csvline_to_list(lineStr):
	'''Convert a single CSV formatted line to a list
	'''
	
	vals = re.findall(r'(?:^|,)("[^"]*"|[^,"\n\r]*)', lineStr)
	out = []
	for v in vals:
		out.append( v.strip('" \t') )
	return out
# END csvline_to_list

#===============================================================================
def csv2LD(fileName):
	'''Convert CSV file to line-wise list of dictionaries
	
	This function will open a csv file and create a line-wise list of
	dictionaries based on each line keyed with the values of the first line
	(assumed to be column headers)
	
	Arg:
		fileName (str): The file of interest's name
	Returns:
		list.  Line-wise list of header-keyed dictionaries
	'''
	f = open(fileName)
	
	keys = csvline_to_list(f.readline())
	iCols = range(0, len(keys))
	
	out = []
	for l in f:
		vals = csvline_to_list(l)
		lnDict = {}
		for i in iCols:
			lnDict[keys[i]] = vals[i]
		
		out.append(lnDict)
	
	return out
# END csv2LD

#===============================================================================
def csv2html(csvFileName, addStyle=''):
	'''Convert CSV file to a table in an html page
	
	Args:
		csvFileName (str): The file of interest's name
		addStyle = '': string containing custom CSS for the page
	Returns: -none-
	'''
	htmlTxt = '''
<html>

<head>
<script
	type="text/javascript"
	src="ampjs/ampjs_v1-0.js"
></script>
<script
	type="text/javascript"
	src="ampjs/amp_sorts_tables_v1-0.js"
></script>
<link
	rel="stylesheet"
	type="text/css"
	href="simpleSortTables.css"
></link>

<style>
{0}
</style>
</head>

<body>
<table class="sortable">
	<tr>'''.format(addStyle)
	
	f = open(csvFileName)
	headers = csvline_to_list(f.readline())
	for v in headers:
		htmlTxt += '''
		<th>{0}</th>'''.format(v)
	
	htmlTxt += '''
	</tr>'''
	
	for l in f:
		htmlTxt += '''
	<tr>'''
		lnVals = csvline_to_list(l)
		for v in lnVals:
			htmlTxt += '''
		<td>{0}</td>'''.format(v)
		
		htmlTxt += '''
	</tr>'''
	
	htmlTxt += '''
</table>
</body>

</html>'''
	
	f.close()
	
	htmlFileName = re.sub(r'(?<=\.)csv(?=$)', 'html', csvFileName)
	f = open(htmlFileName, 'w')
	f.write(htmlTxt)
	f.close()
# END csv2LD

#===============================================================================
def matchScore(A, B):
	'''College Name "Match-y-ness" Valuer Functions
	(devel)
	
	Args:
		A (str):
		B (str):
	Returns:
		?
	'''
	results = {}
	
	synonyms = [
		('Illinois', 'Ill', 'IL')
	]
	
	for aStr in A:
		scores = {}
		Aexploded = re.split(r'[\s\-]', aStr)
		
		Aexmulti = []
		for partialStr in Aexploded:
			for tupSet in synonyms:
				for word in tupSet:
					if partialStr.lower() == word.lower():
						pass
					n = len(partialStr)
					if n == 2:
						continue
				for i in range(0,n):
					Aexmulti.append(partialStr)
		
		N = 0
		for bStr in B:
			for partialStr in Aexmulti:
				if re.search(partialStr, bStr, re.I):
					if bStr in scores.keys():
						scores[bStr] += 1
					else:
						scores[bStr] = 1
					N += 1
				for k in scores.keys():
					scores[k] = scores[k]/float(N)
		scores = sorted(scores.items(), key=lambda (k,v): v, reverse=True)
		results[aStr] = scores
	
	return results
# END matchScore

#===============================================================================
def numConvert(x, fromBase, toBase):
	'''Convert a Number's Base in or out of Base 10
	
	Either fromBase or toBase must be 10.  Valid bases are between 2 and 62,
	input error with respect to this restriction will be silently ignored
	
	Args:
		x (float|int): value to be converted
		fromBase (int): value's original base
		toBase (int): value's desired base
	Returns:
		float.  The value in the desired base
	'''
	allDigStr = '0123456789abcdefghijklmnpqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ'
	dozenal_digits = u'0123456789\u03c7\u025b'
	if fromBase == 10:
		z = ''
		K = int(math.log(x, toBase))
		for i in range(1,K+1)[::-1]:
			y = int(x/(toBase**i))
			z = z + allDigStr[y]
			x = x - y*toBase**i
		z = z + allDigStr[int(x)]
	elif toBase == 10:
		rlkup = {}
		for i, s in enumerate(allDigStr):
			rlkup[s] = i
		z = 0
		for i, s in enumerate(x[::-1]):
			z = z + rlkup[s]*fromBase**i
	# END if
	return z
# END numConvert

#===============================================================================
def update(total, count, count_lock, interval=2):
	t_0 = time.time()
	T = [0, 0, 0]
	N = [0, 0, 0]
	while True:
		with count_lock: n = count.value
		N.append(n)
		N.pop(0)
		
		secs = time.time() - t_0
		T.append(secs)
		T.pop(0)
		
		hrs = int(secs/60/60)
		secs -= 60*60*hrs
		mins = int(secs/60)
		secs -= 60*mins
		
		x = 100.0*float(n)/total
		out_str = (
			'({0:02d}:{1:02d}:{2:06.3f}) '.format(hrs, mins, secs) +
			'{0:02.0f}% complete ({1}/{2})'.format(x, n, total)
		)
		
		dn = N[2] - N[0]
		dt = T[2] - T[0]
		if dt > 0 and n > 0:
			out_str += ', '
			if dn == 0:
				dn = 0.5
				out_str += '> '
			# END if
			dndt = float(dn)/float(dt)
			etr_secs = (total-n) / dndt
			etr_hrs = int(etr_secs/60/60)
			etr_secs -= 60*60*etr_hrs
			etr_mins = int(etr_secs/60)
			etr_secs -= 60*etr_mins
			out_str += (
				'{0:02d}:{1:02d}:{2:02d} remaining'.format(
					etr_hrs, etr_mins, int(etr_secs)
					)
				)
		# END if
		
		print out_str
		time.sleep(interval)
	# END while
# END update




