'''AMP College Basketball Package Testing Module
	Author: Alex Pronschinske
	Version: 1 (developmental)
	
	List of Classes: -none-
	List of Functions:
		main
		link_collection
	Module dependencies: 
		collection
		sys
'''

import core
import collection as coll
import analysis as anl

import re

test_sn = core.SeasonName('M', 2011)

#===============================================================================
def main(*args):
	test_lut = {
		'link_collection': link_collection,
		'download_pbp': download_pbp,
		'iter_gm': iter_gm
	}
	test_lut[args[0]]()
# END main

#===============================================================================
def link_collection():
	Lg, played_gms, future_gms = coll.download_gm_links(
		test_sn, writeURLs=True
	)
	print 'len(played_gms) = {0}'.format(len(played_gms))
	print 'len(future_gms) = {0}'.format(len(future_gms))
	print 'Number of teams in league: {0}'.format(Lg.Ntms)
# END link_collection

#===============================================================================
def download_pbp():
	coll.download_pbp(
		test_sn, played_gms='played_games_'+str(test_sn)+'.csv',
		write_skips=True
	)
# END download_pbp	

#===============================================================================
def iter_gm():
	with open('sampleGame-annotated.txt') as f:
		pbp_csv = f.read()
	pbp_csv = re.sub(r'\n\n', '\n', pbp_csv)
	pbp_csv = re.sub(r'<[^\n]+\n', '', pbp_csv)
	leag = core.League('team_hashcodes_M_11-12.csv')
	hm = leag('North Carolina St.')
	vs = leag('Elon')
	smpl_gm = anl.Game('20120128H2585753', hm, vs, pbp_csv)
	
	with open('iter_test_result.txt', 'w') as f:
		f.write(str(smpl_gm) + '\n')
		for bout in smpl_gm:
			f.write(str(bout) + '\n')
	# END with
# END load_sample_game

#===============================================================================
if __name__ == '__main__':
	import sys
	main(sys.argv[1:])
# END if
