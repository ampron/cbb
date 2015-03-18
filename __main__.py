'''AMP College Basketball Package Executable Commands Module
	Author: Alex Pronschinske
	Version: 1 (developmental)
	
	List of Classes: -none-
	List of Functions: 
		main
	Module dependencies: 
		analysis
		collection
		sys
		test
'''

import sys
import core
import collection
import analysis
import test

#===============================================================================
def main(*args):
	if len(args) == 0:
		#print 'Downloading hashcodes for Women\'s CBB'
		#collection.download_hashcodes('W')
		#print 'Downloading hashcodes for Men\'s CBB'
		#collection.download_hashcodes('M')
		
		seasons = []
		for y in [2012]:
			seasons.append( core.SeasonName('M', y) )
			seasons.append( core.SeasonName('W', y) )
		# END for
		
		for sn in seasons:
			print 'Getting URL\'s from {0} season'.format(sn)
			Lg, played_gms, future_gms = collection.download_gm_links(
				sn, writeURLs=True
			)
			print 'Getting PbP data from {0} season'.format(sn)
			collection.download_pbp(
				sn, Lg, played_gms=played_gms, write_skips=True
			)
	elif args[0] == '-t':
		test_name = args[1]
		if test_name in dir(test):
			print 'running ' + test_name
			test.main(test_name)
		# END if
	# END if
# END main

if __name__ == '__main__':
	main(*sys.argv[1:])
