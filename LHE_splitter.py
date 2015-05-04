#! /usr/bin/env python
## Script to split LHE files with multiple-weights into multiple single-weight files
#
#  Author: James Robinson <james.robinson@cern.ch>
#  
#  Modified by Michaela Queitsch-Maitland <michaela.queitsch-maitland@cern.ch> to handle very large input LHE files
#  Makes use of iterparse to iterate through elements in tree (instead of reading the whole tree into memory)

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

# Generate dictionary to map IDs to weight metadata
weights = {}
LHE_version = 3.0
for event, elem in ElementTree.iterparse( args.input_file, events=('start','end') ):
  # Find LHE version
  if elem.tag=="LesHouchesEvents":
    LHE_version = elem.get('version')
        
  if elem.tag=="weightgroup":
    weight_group = elem
    output_weight_group = copy.deepcopy( weight_group )
    [ output_weight_group.remove( weight ) for weight in output_weight_group.findall('weight') ]
    for weight in weight_group.findall('weight') :
      weights[weight.get('id')] = ( copy.deepcopy( output_weight_group ), weight )

  if elem.tag=="event" or elem.tag=="wgt":
      break

# Iterate over weights
for idx, (ID, weight_metadata) in enumerate( sorted( weights.items() ), start=1 ) :
  logger.info( 'Now expanding weight {0}/{1} : ID {2}'.format( idx, len(weights), ID ) )

  # Open output file
  output_file = replace_last( args.input_file, '.', '.{0}.'.format(ID) )
  logger.info( 'Writing new LHE file to {0}'.format( output_file ) )
  f = open( output_file, 'w' )

  # Write preamble to file
  f.write('<LesHouchesEvents version="'+LHE_version+'">')
  # Find the header and init elements
  for event, elem in ElementTree.iterparse( args.input_file, events=('start','end') ):
      if event=="end" and elem.tag=="header":  
          # Replace reweighting header
          reweight_header = elem.find('initrwgt')
          [ reweight_header.remove( weight_group ) for weight_group in reweight_header.findall('weightgroup') ]
          reweight_header.append( weight_metadata[0] )
          reweight_header.find('weightgroup').append( weight_metadata[1] )
          f.write(ElementTree.tostring(elem))

      # Don't read past init (don't want to iterate over events yet!)
      if event=="end" and elem.tag=="init": 
          f.write(ElementTree.tostring(elem))
          break

  # Now iterate over events
  logger.info( '  iterating over events' ); event_number = 0
  for event, elem in ElementTree.iterparse( args.input_file, events=('start','end') ):
      if event=="end" and elem.tag=="event":
          if event_number % 1e5 == 0 :
              logger.info( '  ... processed {0} M events'.format( event_number/1e6 ) )
          event_weights = elem.find('rwgt')
          output_event_weights = copy.deepcopy( event_weights )
          [ output_event_weights.remove( weight ) for weight in output_event_weights.findall('wgt') ]
          for weight in event_weights :
              if weight.get('id') == ID :
                  output_event_weights.append( weight )
          elem.remove( event_weights )
          elem.append( output_event_weights )
          event_number += 1

          # Write event with modified weight element to output
          f.write(ElementTree.tostring(elem))

  # Closing brace for LesHouchesEvents
  f.write('</LesHouchesEvents>')
  # Close file
  f.close()


