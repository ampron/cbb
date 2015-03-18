'''AMP College Basketball Core Module
	Author: Alex Pronschinske
	Version: 1 (developmental)
	
	List of classes:
		League
		SeasonName
		Team
	List of functions:
		pbp_data_census
	Module dependencies: 
		ampLib
		os
		re
'''

import os
import re
import ampLib

#===============================================================================
class League(object):
	'''College Basketball League Class
	
	This class a custom hash table for matching team names to NCAA hashcodes
	to internal prime hashvalues.  Entries will be Team objects and each will
	be keyed 3 times, once by name, once by NCAA hashcode, and once by prime
	hash value.  This allows for 3-way look-up.
	
	Instantiation Args:
		fileName (str): Name of hashcode CSV file
						e.g. "team_hashcodes_M_09-10.csv"
	Instance Attributes:
		sn (SeasonName)
		registry (dict)
		tm_nms (list)
		ncaa_hcs (list)
		prime_hvs (list)
		non_D1_name (str)
		Ntms (int)
	Class Methods:
		__call__
		__iter__
	'''
	
	def __init__(self, *args):
		if len(args) == 1 and type(args[0]) is str:
			file_name = args[0]
			try:
				self.sn = SeasonName(
					re.search(r'(?<=_)M|W(?=_)', file_name).group(0),
					'20'+re.search(r'(\d\d)-\d\d', file_name).group(1)
				)
			except Exception as err:
				raise type(err)('file name, "{0}", not vaild'.format(file_name))
			# END try
		elif len(args) == 1 and type(args[0]) is SeasonName:
			self.sn = args[0]
			file_name = 'team_hashcodes_{0}.csv'.format(self.sn)
		elif len(args) == 2:
			self.sn = SeasonName(*args)
			file_name = 'team_hashcodes_{0}.csv'.format(self.sn)
		else:
			raise TypeError(
				'League initalization argument must be ' +
				'a file name (str), a gender & year (str,str|int), ' +
				'or a core.SeasonName'
			)
		# END else
		# END if
		
		self.registry = {}
		self.tm_nms = []
		self.ncaa_hcs = []
		self.prime_hvs = []
		
		f = open(file_name)
		l = f.readline()
		for l in f:
			lntup = ampLib.csvline_to_list(l) # (team_name, ncaa_hc, phv)
			tm = Team(*lntup)
			
			self.registry[tm.name] = tm
			self.registry['n'+tm.ncaa_hc] = tm
			self.registry['p'+str(tm.phv)] = tm
			
			if lntup[2] == '2':
				self.non_D1_name = tm.name
			else:
				self.tm_nms.append(tm.name)
				self.ncaa_hcs.append(tm.ncaa_hc)
			# END if
			self.prime_hvs.append(tm.phv)
		# END for
		f.close()
		
		self.Ntms = len(self.tm_nms)
	
	def __call__(self, query):
		'''Look-up Call Method
		
		A function-like call of the League class will perform a smart look-
		up for a given team name string, NCAA hash value (str only), or a prime
		hashvalue (int only).
		
		Args:
			query (str|int): will become key for a tuple entry in the registry
		Retruns:
			Team.
		'''
		
		if type(query) is int:
			query = 'p' + str(query)
		elif re.search(r'^\d+$', query):
			query = 'n' + query
		# END if
		
		try:
			return self.registry[query]
		except KeyError:
			return Team(query, '0', 2, False)
		# END try
	# END __call__
	
	def __format__(self, format_spec):
		format_str = self.gender + '_' + self.year_txt
		return format_str.__format__(format_spec)
	# END __format__
	
	def __iter__(self):
		for name in self.tm_nms:
			yield self.registry[name]
	# END __iter__
# END League

#===============================================================================
class SeasonName(tuple):
	'''Gender and year specific season name class
	
	Instantiation Args:
		gender (str): gender represented as "M" or "W", case-insensitive
		year (int): year the the season started
	Instance Attributes:
		gender (str)
		year (int)
	Class Methods:
		__str__
	'''
	
	def __new__(cls, gender, year):
		# Validate the gender
		if type(gender) is not str:
			raise TypeError('gender must be a str')
		if gender != 'M' and gender != 'W':
			raise ValueError('gender argument must be "M"|"W"')
		elif gender == 'm':
			gender = 'M'
		elif gender == 'w':
			gender = 'W'
		# END if
		
		# Validate the year
		if type(year) is str:
			try:
				year = int(year)
			except ValueError:
				raise ValueError(
					'year string, "{0}", not a vaild integer'.format(year)
				)
			# END try
		# END if
		if type(year) is not int:
			raise TypeError('year must be a str or int')
		if year < 2009:
			raise ValueError('year value less than 2009')
		
		label = gender + '_' + str(year)[-2:] + '-' + str(year+1)[-2:]
		
		return super(SeasonName, cls).__new__(cls, (gender, year, label))
	# END __new__
	
	def __format__(self, format_spec):
		return str(self)
	# END __format__
	
	def __str__(self):
		return self[2]
	# END __str__
	
	@property
	def year(self): return self[1]
	
	@property
	def gender(self): return self[0]
# END SeasonName

#===============================================================================
class Team(tuple):
	'''NCAA Team Class
	
	Instantiation Args:
		name (str): team name
		ncaa_hc (str): NCAA hashcode
		phv (str|int): prime hash value
	Instance Attributes:
		name (str)
		ncaa_hc (str)
		phv (int)
	Class Methods:
		__str__
	'''
	
	def __new__(cls, name, ncaa_hc, phv, D1=True):
		# Validate and condition the arguments
		if type(name) is not str: raise TypeError('name must be a str')
		if type(ncaa_hc) is not str: raise TypeError('ncaa_hc must be a str')
		if type(phv) is str: phv = int(phv)
		if type(phv) is not int: raise TypeError('phv must be a str or int')
		if type(D1) is not bool: raise TypeError('D1 must be a bool')
		
		return super(Team, cls).__new__(cls, (name, ncaa_hc, phv, D1))
	# END __new__
	
	@property
	def name(self): return self[0]
	@property
	def ncaa_hc(self): return self[1]
	@property
	def phv(self): return self[2]
	@property
	def D1(self): return self[3]
	
	def __str__(self):
		return self.name
	# END __str__
# END Team

#===============================================================================
def pbp_data_census(file_name):
	'''Play-by-Play Quick Data Census
	
	This function will count up which games are recorded in a pbp-xml database
	without loading the whole database into memory
	
	Args:
		file_name (str): name of pbp-xml database file
	Returns:
		list. List of indiviual game hashcodes (str)
	'''
	gm_hashcodes = []
	
	if file_name not in os.listdir('.'): return gm_hashcodes
	
	lnptn = re.compile(r'^<game\ id="([\dHN]{16})">$')
	with open(file_name) as f:
		for ln in f:
			lnMat = lnptn.match(ln)
			if lnMat:
				gm_hashcodes.append( lnMat.group(1) )
			# END if
		# END for
	# END with
	
	return gm_hashcodes
# END pbp_data_census
























