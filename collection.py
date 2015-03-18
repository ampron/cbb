'''College Basketball Data Collection Module
	Author: Alex Pronschinske
	Module Version: 1 (developmental)
	
	List of classes: -none-
	List of functions:
		download_gm_links
		download_hashcodes
		download_pbp
		get_tm_schd
		get_gm_pbp
		parse_pbp_html
	Module dependencies: 
		ampLib
		ampMath
		core
		multiprocessing
		os
		re
		urllib2
'''

import time

import core

import multiprocessing as mp
import re
from urllib2 import urlopen, URLError
import os
import ampLib
import ampMath

#===============================================================================
def download_gm_links(sn, silence=False, writeURLs=False):
	'''This method will download webpages from NCAA.com and record web
	links for all the games in the current season.
	
	Args:
		sn (core.SeasonName): "s"eason "n"ame, contains year and gender
		silence = False: switch for turning off print statements
		writeURLs = False: If true a text file containing the links will
			be saved.
	Returns:
		(Lg, played_gms, future_gms)
		Lg (League): League object used
		played_gms (list): [(gmhc, vsTm, vsSc, hmTm, hmSc, gm_link), ..]
		future_gms (list): [(gmhc, vsTm, hmTm), ...]
	'''
	
	if sn.gender == 'M':
		sportyear_codes = {
			2009: '10260', 2010: '10440', 2011: '10740', 2012: '11220'
		}
	else:
		sportyear_codes = {
			2009: '10261', 2010: '10420', 2011: '10760', 2012: '11240'
		}
	
	# assemble team index page url
	# TODO: use this instead...
	# "http://stats.ncaa.org/team/schedule_list?academic_year=2011"
	# + "&conf_id=-1&division=1&sport_code=MBB&schedule_date=01/13/2011"
	# and this...
	# "http://stats.ncaa.org/team/inst_team_list?academic_year=2011"
	# + "&conf_id=-1&division=1&sport_code=MBB
	
	# Make a list of team pages
	Lg = core.League(
		'team_hashcodes_{0}.csv'.format(sn)
	)
	team_urls = []
	for tm in Lg:
		if tm.phv == 0: continue
		team_urls.append(
			(
				tm,
				'http://stats.ncaa.org/team/index/'
				+ sportyear_codes[sn.year] + '?' + 'org_id=' + tm.ncaa_hc
			)
		)
	
	if not silence:
		print 'begin collecting game links from team pages...'
	
	# Collect game links from individual team pages
	# This section of code is uses multiple processes asynchronously
	#crawl_results = urltools.open_urls(team_urls, 3, silence=False)
	
	#played_gms = []
	#for (tm, url) in team_urls:
	#	try:
	#		played_gms.append( parse_tmpg(tm, crawl_results[url])
	#	except Exception as err:
	#		print '{0} on {1} page: {2}'.format(
	#			type(err).__name__, tm, str(err)
	#		)
	#		raise err
	#	# END try
	# END for
	
	manager1 = mp.Manager()
	pastgm_results = manager1.Queue()
	manager2 = mp.Manager()
	futuregm_results = manager2.Queue()
	results = {'past': pastgm_results, 'future': futuregm_results}
	
	manager3 = mp.Manager()
	count = manager3.Value('i', 0)
	count_lock = manager3.Lock()
	
	worker_pool = mp.Pool(processes=10*mp.cpu_count())
	for (tm, url) in team_urls:
		if tm.phv == 2: continue
		
		# Give team schedule url to worker pool
		worker_pool.apply_async(
			get_tm_schd, args=(tm.name, tm.ncaa_hc, url, results, count, count_lock)
		)
	# END for
	worker_pool.close()
	
	# Start an updater process
	updater = mp.Process(
		target=ampLib.update,
		args=(len(team_urls), count, count_lock, 10)
	)
	updater.start()
	
	# Wait here for all work to complete
	worker_pool.join()
	updater.terminate()
	if not silence:
		print 'All asynchronous work completed'
	# Async. multiprocess code ended
	
	# Get results out of Queue object
	played_gms = []
	while not results['past'].empty():
		gm_data = results['past'].get()
		dateInt = gm_data[0]
		HorN = gm_data[1]
		hmhc = gm_data[2]
		hmTm = Lg(hmhc)
		hmSc = gm_data[3]
		vshc = gm_data[4]
		vsTm = Lg(vshc)
		vsSc = gm_data[5]
		gm_link = gm_data[6]
		
		gmhc = '{0:08d}{1}{2:07d}'.format(dateInt, HorN, hmTm.phv*vsTm.phv)
		played_gms.append( (gmhc, vsTm, vsSc, hmTm, hmSc, gm_link) )
	# END while
	
	future_gms = []
	while not results['future'].empty():
		gm_data = results['future'].get()
		dateInt = gm_data[0]
		HorN = gm_data[1]
		hmhc = gm_data[2]
		hmTm = Lg(hmhc)
		vshc = gm_data[3]
		vsTm = Lg(vshc)
		
		gmhc = '{0}{1}{2}'.format(dateInt, HorN, hmTm.phv*vsTm.phv)
		future_gms.append( (gmhc, vsTm, hmTm) )
	# END while
	
	# Each game will have been recorded twice, so remove duplicates and sort
	played_gms = ampLib.uniquify(played_gms, lambda tup: tup[0])
	played_gms.sort(key=lambda tup: tup[0])
	future_gms = ampLib.uniquify(future_gms, lambda tup: tup[0])
	future_gms.sort(key=lambda tup: tup[0])
	
	# (Optional) Write game URLs to csv file
	if writeURLs:
		# Future games
		file_name = 'future_games_{0}.csv'.format(sn)
		f = open(file_name, 'w')
		f.write('gmhc,vsTm,hmTm\n')
		
		future_gms.sort(key=lambda tup: tup[0])
		for (gmhc, vsTm, hmTm) in future_gms:
			f.write( '{0},"{1}","{2}"\n'.format(gmhc, vsTm, hmTm) )
		f.close()
		
		if not silence:
			print 'Saved file: "{0}"'.format(file_name)
		
		# Played games
		file_name = 'played_games_{0}.csv'.format(sn)
		f = open(file_name, 'w')
		f.write('gmhc,vsTm,vsSc,hmTm,hmSc,url\n')
		for tup in played_gms:
			f.write(
				'{0},"{1.name}",{2},"{3.name}",{4},{5}\n'.format(*tup)
			)
		f.close()
		
		if not silence:
			print 'Saved file: "{0}"'.format(file_name)
		# END if
	# END if
	
	return (Lg, played_gms, future_gms)
# END download_gm_links

#===============================================================================
def download_hashcodes(sn=None, test=False):
	'''This method will record all the NCAA team hashcodes and also assign
	the internal prime hash values
	
	Args:
		sn (core.SeasonName): "s"eason "n"ame, contains year and gender, if this
			is left as None then the function is recusively called for all
			available seasons
		test = False: if True the function will run debugging code
	Returns: -none-
	'''
	
	# Recursively call function for all seasons if one is not specified
	if sn is None:
		# Get team index page
		tm_index_pg = urlopen(
			'http://stats.ncaa.org/team/inst_team_list?'
			+ 'sport_code=MBB'
			+ '&division=1',
			timeout=2*60
		)
		tm_index_text = tm_index_pg.read()
		tm_index_pg.close()
		
		# Get all availible years
		all_yrs = re.findall(
			r'''
			<a \s+ href="javascript:changeYears\( (\d{4}) \);"> [^<>]* </a>
			''', tm_index_text, re.DOTALL | re.VERBOSE
		)
		
		for y in all_yrs:
			download_hashcodes(core.SeasonName('M', int(y)-1), test)
			download_hashcodes(core.SeasonName('W', int(y)-1), test)
		# END for
		
		return None
	elif test:
		print str(sn)
	# END if
	
	primes = ampMath.get_primes()
	
	# Get team index page
	tm_index_pg = urlopen(
		'http://stats.ncaa.org/team/inst_team_list?'
		+ 'sport_code='+sn.gender+'BB'
		+ '&division=1'
		+ '&academic_year=' + str(sn.year+1),
		timeout=2*60
	)
	tm_index_text = tm_index_pg.read()
	tm_index_pg.close()
	
	hash_pairs = re.findall(
		r'''
		<tr>\s*
		<td>\s*
		<a\s+
			href="/team/index/\d+\?org_id=(\d+)" [^>]*  # hashvalue
		>
			([^<>]+)                                    # team name
		</a>\s*
		</td>\s*
		</tr>
		''', tm_index_text, re.DOTALL | re.VERBOSE
	)
	
	hash_pairs.sort(key=lambda (v, nm): nm)
	hash_pairs.insert(0, (0, 'non-Div I Schools'))
	
	# Write data to file
	fname = 'team_hashcodes_{0}.csv'.format(sn)
	if test: fname = fname[:-4] + '-test.csv'
	with open(fname, 'w') as f:
		f.write('Team,NCAA ID,Prime ID\n')
		for i in range(len(hash_pairs)):
			f.write(
				'{0[1]},{0[0]},{1}\n'.format(hash_pairs[i], primes[i])
			)
		# END for
	# END with
# END download_hashcodes

#===============================================================================
def download_pbp(
	sn, Lg=None, played_gms=None, silence=False, write_skips=False
):
	'''This method will download webpages from NCAA.com, record play-by-by
	data from the pages, and save it as an AMP-style xml file.
	
	Args:
		sn (core.SeasonName): "s"eason "n"ame, contains year and gender
		Lg (League): League that was used to get the played_gms
		played_gms (list|str): Should be a list of urls (str's) pointing
			to individual game PbP records, or the name of a file (str)
			containing game urls
		silence = False: Bool controling print output
		write_skips = False: If true a text file containing the skipped
			links will be saved.
	Returns:
		list.  Contains str's of game links that were skipped
	'''
	
	# *Arg Validation* determine if played_gms is a list or a file name
	# string
	if type(played_gms).__name__ == 'str':
		print 'Reading in played games from "{0}"'.format(played_gms)
		f = open(played_gms)
		f.readline()
		played_gms = []
		for l in f:
			lnVals = ampLib.csvline_to_list(l)
			played_gms.append( tuple(lnVals) )
		# END for
		f.close()
	elif type(played_gms).__name__ == 'list':
		pass
	else:
		msg = 'played_gms is {} type, must be str or list'.format(
			type(played_gms).__name__
		)
		raise TypeError(msg)
	# END if
	
	# Make a list of team pages
	if Lg is None:
		Lg = core.League(
			'team_hashcodes_{0}.csv'.format(sn)
		)
	# END if
	
	# Load current season's data
	pbp_file_name = 'pbp_data_{0}.xml'.format(sn)
	downloaded_gmhcs = core.pbp_data_census(pbp_file_name)
	
	# Load current season's previous download errors
	pbp_errors_fname = 'pbp_errors_{0}.csv'.format(sn)
	if pbp_errors_fname in os.listdir('.'):
		pbp_errors = ampLib.csv2LD(pbp_errors_fname)
		pbp_errors_hashes = [d['gmID'] for d in pbp_errors]
	else:
		pbp_errors = []
		pbp_errors_hashes = []
	# END if
	
	# Remove from URL list all games already recorded
	if sn.gender == 'M':
		known_errors = {}
	else:
		known_errors = {}
	# END if
	date_bounds = [sn.year*10000 + 1101, (sn.year+1)*10000 + 601]
	gms_skipped = []
	played_gms_reduc = []
	for tup in played_gms:
		# tup = (gmhc, vsTm, vsSc, hmTm, hmSc, gm_link)
		gmhc = tup[0]
		if gmhc not in downloaded_gmhcs and gmhc not in pbp_errors_hashes:
			date = int(gmhc[:8])
			if date_bounds[0] < date and date < date_bounds[1]:
				played_gms_reduc.append(tup)
			elif gmhc in known_errors:
				gmhc = known_errors[gmhc]
				date = int(gmhc[:8])
				played_gms_reduc.append(tup)
			else:
				if not silence:
					print '\nDate Error, {0} not in [{1[0]}, {1[1]}]'.format(
						date, date_bounds
						)
					print 'URL: "{0}"'.format(tup[5])
					print 'game hashcode: {0}\n'.format(gmhc)
				# END if
				gms_skipped.append(tup)
			# END if
		# END if
	# END for
	
	# post-loop clean-up
	del played_gms
	played_gms = played_gms_reduc
	del played_gms_reduc
	
	# Prepare for webpage fetching loop
	n = len(played_gms)
	if not silence:
		print '{0} recorded games exist'.format(len(downloaded_gmhcs))
		print '{0} new games to fetch'.format(n)
	
	# This section of code uses multiple processes asynchronously
	# Setup parallel variables
	manager1 = mp.Manager()
	pbp_data_proxy = manager1.list()
	pbp_data_lock = manager1.Lock()

	manager2 = mp.Manager()
	count = manager2.Value('i', 0)
	count_lock = manager2.Lock()

	worker_pool = mp.Pool(processes=10*mp.cpu_count())
	
	# Start up all processes
	for gm_data in played_gms:
		gmhc = gm_data[0]
		gm_url = gm_data[5]
		worker_pool.apply_async(
			get_gm_pbp,
			args=(
				gm_url, gmhc, pbp_data_proxy, pbp_data_lock, count, count_lock
			)
		)
	# END for
	worker_pool.close()
	
	# Start an updater process
	updater = mp.Process(
		target=ampLib.update,
		args=(len(played_gms), count, count_lock, 10)
	)
	updater.start()
	
	# Wait here for all work to complete
	worker_pool.join()
	updater.terminate()
	if not silence:
		print 'All asynchronous work completed'
	# Async. multiprocess code ended
	
	pbp_data = []
	with pbp_data_lock:
		for tup in pbp_data_proxy:
			pbp_data.append(tup)
		# END for
	# END with
	
	# TODO: function should end here, move writing code to another func
	# Write the pbp and box score data to files
	file_name = 'pbp_data_{0}.xml'.format(sn)
	file_txt = ''
	for gmhc, entry in pbp_data: file_txt += '{0}\n'.format(entry)
	
	if file_name in os.listdir('.'):
		f = open(file_name, 'a')
	else:
		f = open(file_name, 'w')
	# END if
	f.write(file_txt)
	f.close()
	if not silence:
		print '{0} games added to Play-by-Play database'.format(
			len(pbp_data)
		)
	# END if
	
	if len(gms_skipped) > 0:
		if not silence:
			print '{0} link(s) skipped'.format( len(gms_skipped) )
		if write_skips:
			f_name = 'links_Skipped_{0}.txt'.format(sn)
			f = open(f_name, 'w')
			for tup in gms_skipped:
				# tup = (gmhc, vsTm, vsSc, hmTm, hmSc, gm_link)
				f.write( '{0}, {1} at {3}, {5}\n'.format(*tup) )
			f.close()
			if not silence:
				print 'saved in "' + f_name + '"'
			return f_name
		else:
			return gms_skipped
		# END if
	# END if
# END download_pbp

#===============================================================================
def parse_tmpg(tm, pgtxt):
	'''
	'''
	
	rows = re.findall(r'<tr[^<>]*?>(.+?)</tr>', pg_txt, re.DOTALL)
	for rowStr in rows:
		cells = re.findall(r'<td[^<>]*?>(.+?)</td>', rowStr, re.DOTALL)
		if len(cells) != 3: continue
		
		# Should find a date in the 1st column of the row
		dateMat = re.search(
			r'(?P<m> \d{2}) / (?P<d> \d{2}) / (?P<y> \d{4})',
			cells[0], re.VERBOSE
		)
		if not dateMat: continue
		
		# Find the NCAA hashcode of other team in 2nd column
		# of the row
		oppMat = re.search(r'team/index.*?id=(\d+)', cells[1])
		if oppMat:
			opphc = oppMat.group(1)
		else:
			# Opponent is a non-Div I School
			opphc = '0'
		# END if
		
		# Create the game's date integer
		dateInt = '{0[y]}{0[m]}{0[d]}'
		dateInt = dateInt.format(dateMat.groupdict())
		dateInt = int(dateInt)
		
		# Determine if the game is "H"osted or at a "N"eutral
		# location
		if re.search(r'<br/>@', cells[1]):
			HorN = 'N'
			hmhc = tmhc
			vshc = opphc
		elif re.search(r'@', cells[1]):
			HorN = 'H'
			hmhc = opphc
			vshc = tmhc
		else:
			HorN = 'H'
			hmhc = tmhc
			vshc = opphc
		
		# Should find a link to the game's page in the 3rd
		# column of the row
		gm_mat = re.search(
			r'''
			<a\ href=["\']/game/index/(\d+)[^"\']*["\']>
				[^\d<>]+ (\d+)\ *-\ *(\d+) [^<>]+
			</a>
			''', cells[2], re.VERBOSE
		)
		
		# Save links to completed games
		if gm_mat:
			# Make full URL for the game
			gm_link = (
				'http://stats.ncaa.org/game/play_by_play/' +
				gm_mat.groups()[0]
			)
			if tmhc == hmhc:
				hmSc = int(gm_mat.groups()[1])
				vsSc = int(gm_mat.groups()[2])
			else:
				vsSc = int(gm_mat.groups()[1])
				hmSc = int(gm_mat.groups()[2])
			
			results['past'].put(
				(dateInt, HorN, hmhc, hmSc, vshc, vsSc, gm_link)
			)
		# Save data for upcoming games
		else:
			if re.search(r'@', cells[1]):
				hmhc = opphc
				vshc = tmhc
			else:
				hmhc = tmhc
				vshc = opphc
			# END if
			
			results['future'].put( (dateInt, HorN, hmhc, vshc) )
		# END if
	# END for
	
	return past_gms, future_gms

#===============================================================================
def get_tm_schd(tm, tmhc, url, results, count, count_lock, retry=False):
	'''doc string'''
	
	try:
		# download team page text
		f = urlopen(url, timeout=2*60)
		pg_txt = f.read()
		f.close()
	except URLError:
		if not retry:
			print 'Retrying download of {0} schedule...'.format(tm)
			return get_tm_schd(tm, url, results, count, count_lock, retry=True)
		else:
			print '{0} team page skipped: "{1}"'.format(tm, url)
			with count_lock: count.value += 1
			return
		# END if
	# END try
	
	try:
		rows = re.findall(r'<tr[^<>]*?>(.+?)</tr>', pg_txt, re.DOTALL)
		for rowStr in rows:
			cells = re.findall(r'<td[^<>]*?>(.+?)</td>', rowStr, re.DOTALL)
			if len(cells) != 3: continue
			
			# Should find a date in the 1st column of the row
			dateMat = re.search(
				r'(?P<m> \d{2}) / (?P<d> \d{2}) / (?P<y> \d{4})',
				cells[0], re.VERBOSE
			)
			if not dateMat: continue
			
			# Find the NCAA hashcode of other team in 2nd column
			# of the row
			oppMat = re.search(r'team/index.*?id=(\d+)', cells[1])
			if oppMat:
				opphc = oppMat.group(1)
			else:
				# Opponent is a non-Div I School
				opphc = '0'
			# END if
			
			# Create the game's date integer
			dateInt = '{0[y]}{0[m]}{0[d]}'
			dateInt = dateInt.format(dateMat.groupdict())
			dateInt = int(dateInt)
			
			# Determine if the game is "H"osted or at a "N"eutral
			# location
			if re.search(r'<br/>@', cells[1]):
				HorN = 'N'
				hmhc = tmhc
				vshc = opphc
			elif re.search(r'@', cells[1]):
				HorN = 'H'
				hmhc = opphc
				vshc = tmhc
			else:
				HorN = 'H'
				hmhc = tmhc
				vshc = opphc
			
			# Should find a link to the game's page in the 3rd
			# column of the row
			gm_mat = re.search(
				r'''
				<a\ href=["\']/game/index/(\d+)[^"\']*["\']>
					[^\d<>]+ (\d+)\ *-\ *(\d+) [^<>]+
				</a>
				''', cells[2], re.VERBOSE
			)
			
			# Save links to completed games
			if gm_mat:
				# Make full URL for the game
				gm_link = (
					'http://stats.ncaa.org/game/play_by_play/' +
					gm_mat.groups()[0]
				)
				if tmhc == hmhc:
					hmSc = int(gm_mat.groups()[1])
					vsSc = int(gm_mat.groups()[2])
				else:
					vsSc = int(gm_mat.groups()[1])
					hmSc = int(gm_mat.groups()[2])
				
				results['past'].put(
					(dateInt, HorN, hmhc, hmSc, vshc, vsSc, gm_link)
				)
			# Save data for upcoming games
			else:
				if re.search(r'@', cells[1]):
					hmhc = opphc
					vshc = tmhc
				else:
					hmhc = tmhc
					vshc = opphc
				# END if
				
				results['future'].put( (dateInt, HorN, hmhc, vshc) )
			# END if
		# END for
	except Exception as err:
		print '{0} on {1} page: {2}'.format(
			type(err).__name__, tm, str(err)
		)
		raise err
	# END try
	
	with count_lock: count.value += 1
# END get_tm_schd

#===============================================================================
def get_gm_pbp(gm_url, gmhc, pbp_data, pbp_data_lock, count, count_lock):
	# Download pbp web page
	try:
		f = urlopen(gm_url, timeout=2*60)
		pg_txt = f.read()
	except URLError:
		#if not silence:
		print 'URLError on {0}'.format(gmhc)
		print '    {0}'.format(gm_url)
		print '    reason: {0}'.format(URLError.reason)
		pg_txt = None
	except Exception as err:
		print '{0}: {1} on {2}'.format(type(err).__name__, err, gmhc)
	finally:
		f.close()
	#END try
	
	# Parse the pbp page and add it to the list of pbp data
	if pg_txt is not None:
		gm_pbp = parse_pbp_html(pg_txt, gmhc, gm_url)
		with pbp_data_lock: pbp_data.append( (gmhc, gm_pbp) )
	# END if
	
	with count_lock: count.value += 1
# END get_gm_pbp

#===============================================================================
def parse_pbp_html(pg_txt, gmhc='', gm_url=''):
	'''Parse HTML tables containing final score and play-by-play data
	
	Args:
		pg_txt (str): string containing game play-by-play html page
		gmhc (str): hashcode of the game of interest
	Returns:
		str.  pbp data as a XML node
	'''
	
	pg_tbls = re.findall(
		r'<table[^<>]*?mytable[^<>]*?>.*?</table>', pg_txt, re.DOTALL
	)
	period_tbls = []
	for table in pg_tbls:
		pbp_struc = re.search('''
		<tr  [^<>]*> \s*
			<td [^<>]*> \s* Time \s* </td> \s*
			<td [^<>]*> \s* [^<>]+ \s* </td> \s*
			<td [^<>]*> \s* Score \s* </td> \s*
			<td [^<>]*> \s* [^<>]+ \s* </td> \s*
		</tr>
		''', table, re.IGNORECASE | re.VERBOSE
		)
		if pbp_struc:
			period_tbls.append(table)
		if re.search('Total', table):
			summary_tbl = table
	# END for
	
	if len(period_tbls) < 2:
		print 'Warning: {} PbP tables for game {}\n\tURL: {}'.format(
			len(period_tbls), gmhc, gm_url
		)
		f = open('bad_gm_pgs/{0}-{1}_tbls.html', 'w')
		f.write(pg_txt)
		f.close()
	# END if

	# Get team names
	tm_names = re.findall(r'''
		<tr> .+?
			>( [A-Z] [^\n<>]+  )</ .+?
		</tr>
		''', summary_tbl, re.VERBOSE | re.DOTALL)
	tms = {'vs': tm_names[0], 'hm': tm_names[1]}
	
	# Construct play-by-play csv-formated data
	pbp_csv = ''
	period = 1
	for table in period_tbls:
		rows = re.findall('<tr>.*?</tr>', table, re.DOTALL)
		for entry in rows:
			cells = re.findall('<td[^<>]*?>(.*?)</td>', entry)
			time = cells[0]
			vsdetail = re.sub(r'</?b>', '', cells[1])
			sc = re.search('(\d+)-(\d+)', cells[2])
			vssc = sc.group(1)
			hmsc = sc.group(2)
			hmdetail = re.sub(r'</?b>', '', cells[3])
			if len(hmdetail) > len(vsdetail):
				tm = tms['hm']
				play = hmdetail
			else:
				tm = tms['vs']
				play = vsdetail
		
			pbp_csv += '{0},{1},{2},{3},"{4}","{5}"\n'.format(
				period, time, vssc, hmsc, tm, play
				)
		# END for
		pbp_csv += '{0},{1},{2},{3},"{4}","{5}"\n'.format(
			period, '00:00', vssc, hmsc, '', 'End of period'
		)
		period += 1
	# END for
	
	# Construct game entry for the play-by-play database
	pbpEntry = ''
	pbpEntry += '<game id="{0}">\n'.format(gmhc)
	pbpEntry += '<URL>{0}</URL>\n'.format(gm_url)
	pbpEntry += '<home>{0}</home>\n'.format(tms['hm'])
	pbpEntry += '<visitor>{0}</visitor>\n'.format(tms['vs'])
	pbpEntry += '<pbp format="csv">\n'
	pbpEntry += 'period,time,vs_score,hm_score,team,play\n'
	pbpEntry += pbp_csv
	pbpEntry += '</pbp>\n'
	pbpEntry += '</game>'
	
	return pbpEntry
# END parse_pbp_html