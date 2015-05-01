#! /usr/bin/env python

## Script to split LHE files with multiple-weights into multiple single-weight files
#
#  Author: James Robinson <james.robinson@cern.ch>

import argparse
import copy
import logging
from xml.etree import ElementTree

def replace_last(source, str_from, str_to):
    return str_to.join(source.rsplit(str_from, 1))

parser = argparse.ArgumentParser(description='Split an LHE file with multiple weights into multiple files.')
parser.add_argument('input_file', metavar='file_name', type=str, help='an input LHE file with multiple weights')
args = parser.parse_args()

logging.basicConfig( format='%(name)-15s %(levelname)-8s %(message)s', level=logging.INFO)
logger = logging.getLogger('LHE_splitter')
logger.info( 'Preparing to read {0}'.format( args.input_file ) )

# Open the LHE file as xml
tree = ElementTree.parse( args.input_file )
root_element = tree.getroot()

# Get the reweighting information header
generator_header = root_element.find('header')
reweight_header = generator_header.find('initrwgt')

# Generate dictionary to map IDs to weight metadata
weights = {}
logger.info( 'Loading weight metadata' )
for weight_group in reweight_header.findall('weightgroup') :
  output_weight_group = copy.deepcopy( weight_group )
  [ output_weight_group.remove( weight ) for weight in output_weight_group.findall('weight') ]
  for weight in weight_group.findall('weight') :
    weights[weight.get('id')] = ( copy.deepcopy( output_weight_group ), weight )

# Iterate over weights
for idx, (ID, weight_metadata) in enumerate( sorted( weights.items() ), start=1 ) :
  logger.info( 'Now expanding weight {0}/{1} : ID {2}'.format( idx, len(weights), ID ) )
  output_tree = copy.deepcopy( tree )
  root_element = output_tree.getroot()

  # Replace reweighting header
  reweight_header = root_element.find('header').find('initrwgt')
  [ reweight_header.remove( weight_group ) for weight_group in reweight_header.findall('weightgroup') ]
  reweight_header.append( weight_metadata[0] )
  reweight_header.find('weightgroup').append( weight_metadata[1] )

  # Iterate over events
  logger.info( '  iterating over events' ); event_number = 0
  for event in root_element.findall('event') :
    if event_number % 1e6 == 0 : logger.info( '  ... now reading event {0}'.format( event_number+1 ) )
    event_weights = event.find('rwgt')
    output_event_weights = copy.deepcopy( event_weights )
    [ output_event_weights.remove( weight ) for weight in output_event_weights.findall('wgt') ]
    for weight in event_weights :
      if weight.get('id') == ID :
        output_event_weights.append( weight )
    event.remove( event_weights )
    event.append( output_event_weights )
    event_number += 1

  # Write output tree
  output_file = replace_last( args.input_file, '.', '.{0}.'.format(ID) )
  logger.info( 'Writing new LHE file to {0}'.format( output_file ) )
  output_tree.write( output_file )
