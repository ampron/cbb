'''College Basketball Analysis Module
	Author: Alex Pronschinske
	Version: 1 (developmental)
	
	List of classes:
		SeasonData
		Game
		Bout
		EmptyGameError
	List of functions:
		predictGm
		valueGm
		rwRank
	Module dependencies: 
		ampLib
		ampMath
		core
		math
		numpy.linalg
		re
		scipy
		scipy.special
'''

import core
import re
import ampLib
import ampMath
from math import sqrt
import scipy as sp
from scipy.special import erf, erfinv
from numpy.linalg import norm


#===============================================================================
class SeasonData(object):
	'''College Basketball Season Data Class
	
	This class will open a season database file and parse it into a dict
	of indivdual game descriptions keyed by data-team hash codes
	
	Instantiation Args:
		arg (str|core.League|core.SeasonName): Object indicating the season or
			file name (str) of XML database
	Instance Attributes:
		leag (core.League)
		gms (dict): Dict of non-empty Game objects keyed by hashcode (str)
		gm_hcs (list): List of keys for gms
		empty_gms (list): List of hashcodes (str) of games without pbp data
	Class Methods:
		get_tm_schd
	'''
	
	def __init__(self, arg):
		if type(arg) is str:
			try:
				gy = re.search(
					r'^pbp_data_(M|W)_(\d\d)-\d\d\.xml$', arg
				).groups()
			except Exception as err:
				raise type(err)('file name, "{0}", not vaild'.format(arg))
			# END try
			self.sn = core.SeasonName(gy[0], '20'+gy[1])
			
			self.leag = core.League(self.sn)
		elif type(arg) is core.League:
			self.leag = arg
			self.sn = self.leag.sn
		elif type(arg) is core.SeasonName:
			self.sn = arg
			self.leag = core.League(self.sn)
		else:
			raise TypeError(
				'SeasonData initalization argument must be ' +
				'a file name (str), a core.League, or a core.SeasonName'
			)
		# END if
		
		self.gms = {}
		self.gm_hcs = []
		self.empty_gms = []
		with open('pbp_data_{0}.xml'.format(self.sn)) as f:
			pbp_csv = ''
			for ln in f:
				if ln[0] != '<':
					pbp_csv += ln
				elif ln[1] == 'g':
					gmhc = re.search(r'^<game id="([^"]+)">', ln).group(1)
				elif ln[1] == 'h':
					hm_nm = re.search(r'^<home>([^<>]+)', ln).group(1)
				elif ln[1] == 'v':
					vs_nm = re.search(r'^<visitor>([^<>]+)', ln).group(1)
				elif ln == '</game>\n':
					try:
						hm = self.leag(hm_nm)
						vs = self.leag(vs_nm)
						self.gms[gmhc] = Game(gmhc, hm, vs, pbp_csv)
						self.gm_hcs.append(gmhc)
					except EmptyGameError as err:
						self.empty_gms.append(gmhc)
						print str(err)
					# END try
					pbp_csv = ''
				# END if
			# END for
		# END with
		
		self.gm_hcs.sort()
	# END __init__
	
	def __iter__(self):
		for gmhc in self.gm_hcs:
			yield self.gms[gmhc]
	# END __iter__
	
	def get_tm_schd(self, tm):
		'''Get Team Schedule
		
		Given a Team object or a team's name as a string this function returns
		a sorted list of that team's games
		
		Args:
			tm (Team|str): Team identifier
		Returns:
			list. [Game, Game, ...]
		'''
		if type(tm) is str:
			if tm not in self.leag.registry:
				raise ValueError(
					'Team "{0}" is not in the {1} League'.format(
						tm, self.leag.sn
					)
				)
			# END if
			tm = self.leag(tm)
		# END if
		
		tm_schd = []
		for gm in self:
			if gm.hm == tm or gm.vs == tm:
				tm_schd.append(gm)
		# END for
		
		return tm_schd
	# END get_tm_schd
# END SeasonData

#===============================================================================
class Game(object):
	'''Basketball Game Class
	
	This class's methods are the primary play-by-play analysis functions
	
	Instantiation Args:
		hashcode (str): Game hashcode
		hm (Team): home team.
		vs (Team): visiting team.
		pbp_csv (str): String containing csv formated play-by-play data.
	Class Attributes: none
	Instance Attributes:
		hc (str): Game hashcode
		date (str)
		hosted (bool): False for a game at a neutral site
		teams (dict)
		hm (Team)
		vs (Team)
		plays (list)
		pbp_keys (list)
	Class Methods:
		__iter__
	'''
	
	def __init__(self, hashcode, hm, vs, pbp_csv):
		self.hc = hashcode
		self.date = hashcode[:8]
		self.hosted = True
		if hashcode[8] == 'N': self.hosted = False
		self.teams = {'hm': hm, hm.name: hm, 'vs': vs, vs.name: vs}
		self.plays = []
		
		csv_lns = re.findall(r'[^\n]+?\n', pbp_csv)
		if len(csv_lns) < 2:
			raise EmptyGameError(hashcode, hm.name, vs.name)
		# END if
		
		self.plays_keys = ampLib.csvline_to_list(csv_lns.pop(0))
		# pbpKeys = [period, time, vs_sc, hm_sc, team, play]
		for ln in csv_lns:
			ln = ampLib.csvline_to_list(ln)
			self.plays.append(
				(
					int(ln[0]), ln[1], int(ln[2]), int(ln[3]),
					self.teams[ln[4]], ln[5]
				)
			)
		# END for
	# END __init__
	
	@property
	def hm(self): return self.teams['hm']
	
	@property
	def vs(self): return self.teams['vs']
	
	def __iter__(self):
		'''Iterate the game into bouts
		'''
		time = '20:00'
		curr_bout = Bout()
		# plays[i] = [
		#     0:period (int), 1:time (str), 2:vs_sc (int), 3:hm_sc (int),
		#     4:team (Team), 5:play (str)
		# ]
		for ply in self.plays:
			prevTime = time
			
			time = ply[1]
			curr_play_desc = ply[5].lower()
			
			skipMat = re.search(
				'enters|leaves|timeout|deadball', curr_play_desc
			)
			if skipMat:
				continue
			elif re.search('turnover', curr_play_desc):
				if len(curr_bout) > 0: yield curr_bout
				
				curr_bout = Bout(ply)
			elif ( re.search(r'made|missed', curr_play_desc)
			and not re.search(r'free throw', curr_play_desc) ):
				if len(curr_bout) > 0: yield curr_bout
				
				curr_bout = Bout(ply, fga=True)
			elif re.search(r'foul', curr_play_desc):
				if curr_bout.first_act_fga and time == prevTime:
					curr_bout.append(ply)
					continue
				# END if
				
				if len(curr_bout) > 0: yield curr_bout
				
				curr_bout = Bout(ply)
			elif re.search(r'end of', curr_play_desc):
				if len(curr_bout) > 0: yield curr_bout
				
				curr_bout = Bout()
			else:
				curr_bout.append(ply)
			# END if
		# END for
	# END __iter__
	
	def __str__(self):
		return '{0}: {1} @ {2}'.format(self.hc, self.vs, self.hm)
	# END __str__
# END Game

#===============================================================================
class Bout(object):
	'''Basketball Possession Bout Class
	
	The Bout class will describe a single run through the possession tree
	
	Instantiation Args:
		plays (list)
	Instance Attributes:
		compiled_string (str)
		first_act_fga (bool)
		plays (list)
		includes_commonfoul (bool)
	Class Methods:
		__len__
		__str__
		append
	'''
	
	def __init__(self, ply=None, fga=False):
		self.first_act_fga = None
		self.compiled_string = ''
		self.plays = []
		if ply is not None: self.append(ply, fga)
		# END if
	# END __init__
	
	def __len__(self):
		return len(self.plays)
	# END __len__
	
	def __str__(self):
		return self.compiled_string
	# END __str__
	
	def append(self, ply, fga=False):
		self.plays.append(ply)
		if len(self) == 1: self.first_act_fga = fga
		self.compiled_string += '{0},{1},{2:02d},{3:02d},{4},{5};'.format(*ply)
	# END append
	
	@property
	def includes_commonfoul(self):
		if ( re.search(r'foul', str(self))
		and not re.search(r'free throw', str(self)) ):
			return True
		else:
			return False
		# END if
	# END includes_commonfoul
# END Bout

#===============================================================================
class EmptyGameError(Exception):
	'''Empty Game Error Exception Class
	
	Exception raised for attempt to create a Game object without PbP data
	
	Instantiation Args:
		gmHashcode (str): Hashcode of game
		hmtm (str): Name of home team.
		vstm (str): Name of visiting team.
	Instance Attributes:
		gmHashcode (str)
		hmtm (str)
		vstm (str)
		msg (str)
	'''
	def __init__(self, gmHashcode, hmtm='', vstm=''):
		self.gmHashcode = gmHashcode
		self.hmtm = hmtm
		self.vstm = vstm
	# END __init__
	
	def __str__(self):
		self.msg = 'No PbP data in ' + self.gmHashcode
		if self.hmtm != '' and self.vstm != '':
			self.msg += ', {} vs. {}'.format(self.vstm, self.hmtm)
		return repr(self.msg)
	# END __str__
# END EmptyGameError

# TODO: make a method of Game class
#===============================================================================
#  (P[hm win], finalScore) = predictGm(Vhm, Vvs, ('H'|'N'), ('M'|'W'))
#-------------------------------------------------------------------------------

# TODO: make a method of Game class
#===============================================================================
#  {'V2H':, 'H2V':} = valueGm(scDiff, ('H'|'N'), ('M'|'W'))
#-------------------------------------------------------------------------------
def valueGm(scDiff, HorN, MorW):
	'''Game valuing function
	
	Here's the idea.  If, for example, a team wins by 16 at home then this
	performance is better than 68.5% (or 1 stdev) of all other game outcomes.
	Therefore, the random walker voter will judge this team as
	the better team 68.5% of the time.  Or, 68.5% of RW voters will pick that
	team as better.
	'''
	if MorW.lower() == 'm':
		# Home edge
		mu = 4.45703
		# Standard deviation in score
		sig = 12.75732
	else:
		mu = 3.94315
		sig = 16.36411
	
	if HorN.lower() == 'h':
		adjScDiff = scDiff - mu
	else:
		adjScDiff = scDiff
	
	p = {'V2H': 0.0, 'H2V': 0.0}
	p['V2H'] = 0.5*(1.0 + erf( adjScDiff / (sqrt(2.0)*sig) ))
	p['H2V'] = 1.0 - p['V2H']
	
	return p
# END valueGm

# TODO: make a method of SeasonData class
#===============================================================================
def rwRank(dataInput, MorW='M'):
	'''Random-Walker Ranking Function
	'''
	if type(dataInput).__name__ == 'str':
		# Read in game data
		boxData = ampLib.csv2LD(dataInput)
		#  expect file name to be "box_data_(M|W)_10-11.csv"
		MorW = re.search(r'(?<=_)M|W(?=_)', dataInput).group(0)
	else:
		boxData = dataInput
	
	for gmEntry in boxData:
		gmEntry['hmSc'] = int(gmEntry['hmSc'])
		gmEntry['vsSc'] = int(gmEntry['vsSc'])
	
	# Set-up team legend
	tmIds = core.League('team_ids_' + MorW + '1011.csv')
	allTms = tmIds.names
	nonD1tm = tmIds.non_D1_name
	
	#DEBUG: Example League
	#allTms = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
	#boxData = [
	#    {'gmID':'12345678H', 'home':'A', 'hmSc':80, 'visitor':'B', 'vsSc': 70},
	#    {'gmID':'12345678H', 'home':'E', 'hmSc':83, 'visitor':'A', 'vsSc': 85},
	#    {'gmID':'12345678H', 'home':'B', 'hmSc':80, 'visitor':'E', 'vsSc': 73},
	#    {'gmID':'12345678H', 'home':'C', 'hmSc':60, 'visitor':'D', 'vsSc': 68},
	#    {'gmID':'12345678H', 'home':'F', 'hmSc':60, 'visitor':'G', 'vsSc': 68},
	#]
	
	# Digest game data
	gmTups = []
	winCnts = []
	tmLeg = {}
	tmLegR = {}
	iTm = 0
	for gmD in boxData:
		hmtm = gmD['home']
		if hmtm not in allTms:
			hmtm = nonD1tm
		vstm = gmD['visitor']
		if vstm not in allTms:
			vstm = nonD1tm
		
		scDiff = gmD['hmSc'] - gmD['vsSc']
		p = valueGm(scDiff, gmD['gmID'][8], MorW)
		
		if hmtm not in tmLeg.keys():
			hmIDnum = iTm
			iTm += 1
			tmLeg[hmtm] = hmIDnum
			tmLegR[hmIDnum] = hmtm
			winCnts.append({'N': 0, 'W': 0, 'EW': 0.0})
		else:
			hmIDnum = tmLeg[hmtm]
		
		if vstm not in tmLeg.keys():
			vsIDnum = iTm
			iTm += 1
			tmLeg[vstm] = vsIDnum
			tmLegR[vsIDnum] = vstm
			winCnts.append({'N': 0, 'W': 0, 'EW': 0.0})
		else:
			vsIDnum = tmLeg[vstm]
		
		gmTups.append( (hmIDnum, vsIDnum, p['V2H']) )
		winCnts[hmIDnum]['N'] += 1
		winCnts[vsIDnum]['N'] += 1
		if scDiff > 0:
			winCnts[hmIDnum]['W'] += 1
		else:
			winCnts[vsIDnum]['W'] += 1
	# End for gmD in boxData
	
	# Record graph size
	numTms = iTm
	print 'Number of Vertices on Graph = {0}'.format(numTms)
	iSet = range(0, numTms)
	
	# Set up graph matrix
	D = [[0.0 for j in iSet] for i in iSet]
	for (hmIDnum, vsIDnum, pV2H) in gmTups:
		pH2V = 1.0 - pV2H
		
		D[hmIDnum][hmIDnum] -= pH2V
		D[hmIDnum][vsIDnum] += pV2H
		
		D[vsIDnum][vsIDnum] -= pV2H
		D[vsIDnum][hmIDnum] += pH2V
	
	# Solve for equilibrium by row elimination
	Dreduc = ampMath.rowElim(D)
	
	V = [0.0 for i in iSet]
	A = 1.0
	nGroups = 0
	iBackwards = sorted(iSet, reverse=True)
	for i in iBackwards:
		for j in range(i+1,numTms):
			V[i] -= Dreduc[i][j]*V[j]
		if V[i] == 0.0:
			V[i] = 1.0
			nGroups += 1
		A += V[i]
	
	# Normalize team values
	A /= numTms
	Veq = sp.array(V)
	for i in iSet:
		V[i] = (i, V[i]/A)
		Veq[i] = Veq[i]/A
	
	# Display graph connected-ness
	if nGroups == 1:
		print 'Graph Connected'
	else:
		print 'Graph Unconnected, with {0} subgroups'.format(nGroups)
	
	# Check equilibrium values
	Dmatrix = sp.array(D)
	dV = sp.dot(Dmatrix,Veq)
	dVnorm = norm(dV)
	print '|dV| = {0:0.8e}'.format(dVnorm)
	
	# Rank teams and translate values to "points"
	V = sorted(V, key=lambda (i,v): v, reverse=True)
	medianValue = V[len(V)/2][1]
	results = []
	rnk = 1
	for (iTm, v) in V:
		tm = tmLegR[iTm]
		tmPID = tmIds(tm)
		# points over a median team at a neutral site
		# TODO: predictGm undefined, fix this
		(pHm, pnts) = predictGm(v, medianValue, 'N', 'M')
		N = winCnts[iTm]['N']
		W = winCnts[iTm]['W']
		results.append( (tm, tmPID, rnk, v, pnts, N, W) )
		rnk += 1
	
	# save results in a csv file
	f = open('rankings_'+MorW+'.csv', 'w')
	f.write(
		'Rank,Team Prime ID,Team Name,Record,Win Pct,Vetrex Value,'
		+ 'Score Over Median Team\n'
	)
	for (tm, tmPID, rnk, v, pnts, N, W) in results:
		lnStr = '{0},{1},{2},"{3:2d} - {4:2d}",{5:0.3f},{6:0.5f},{7:+0.2f}\n'
		f.write(
			lnStr.format(rnk, tmPID, tm, W, N-W, float(W)/N, v, pnts)
		)
	f.close()
	
	return results
# END rwRank

