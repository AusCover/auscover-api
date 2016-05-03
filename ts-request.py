#!/bin/env python
#
# ts-request.py: Part of AusCover-API suite
#   request a timeseries for a point from a data layer
#

### Modules ###
import os, sys, re
import yaml
from pprint import pprint
from collections import OrderedDict as OD
from subprocess import call as spc
from datetime import datetime
### Globals ###
tmpncfile = ''

### Functions ###

def readYaml():
  """Read a file into a yaml list/dict object """
  yf = 'auscover-products.yaml'
  yd = [ OD() ]
  with open(yf, 'r') as fin:
    yd = yaml.safe_load(fin)
    #yd = yaml.safe_load(fin, Loader=yamlordereddictloader.Loader)
  return yd
#---

def listAllDatasets(yd):
  # field length - for printing
  flen = 30

  #print 'Contains %d items of %s' % (len(yd), type(yd))
  print ''
  #print 'ID  Layer/Product         Location'
  print '%3s' % 'ID', 'Layer/Product'.ljust(flen)[:flen], 'Type'.ljust(flen-20), 'Location'.ljust(flen+20)[:flen+20]
  print '%3s' % '--', '-------------'.ljust(flen)[:flen], '----'.ljust(flen-20), '--------'.ljust(flen+20)[:flen+20]
  for i in range(len(yd)):
    print "%3s" % str(i+1), yd[i]['name'].ljust(flen)[:flen], yd[i]['type'].ljust(flen-20), yd[i]['location'].ljust(flen+20)[:flen+20]
#--- 

def listDatasetID(ds):
  #pprint(ds, indent=2, width=80)
  print ''
  print 'Description    : %s' % ds['description']
  print 'Type           : %s' % ds['type']
  print 'Location       : %s' % ds['location']
  print 'Variables      : %s' % ds['variables']
  print 'Temporal Extent: %s ... %s' % (ds['temporal_extent']['start'], ds['temporal_extent']['end'])
  print 'CRS            : %s' % ds['crs']
  print 'Spatial Extent : %s (upper-left) ... %s (lower-right)' % (ds['spatial_extent']['ul'], ds['spatial_extent']['lr'])
  print ''
#--- 

def errorParams(p):
  print 'This argument <%s> requires a value!' % p
  usage()
#--- 

def parseArgs(args):
  #print args, type(args), len(args)
  #allArgs = ' '.join(args)
  #print allArgs, type(allArgs), len(allArgs)    
  # now resplit on ' ' ( '-' causes a problem for -ve latlons)
  #splitArgs = allArgs.split(' ')
  splitArgs = args
  #print splitArgs
  pargs = []
  for s in splitArgs:
    #ss = s.split(' ')
    #print ss
    # remove last item if blank
    #if s[-1] == '': s.pop(-1)
    #if len(s) == 0:
      #ignore
    #  pass
    
    #strip leading '-'
    if s[0] == '-': s = s.lstrip('-')

    #now insert args into list
    if len(s) == 1:
      pargs.append((s))
      #print 'arg: %s' % (ss[0])
    elif len(s) >= 2:
      pargs.append((s[0],s[1:]))
      #print 'arg: %s,  value: %s' % (ss[0], ss[1])
    else:
      print 'Unknown arguments', s
      usage()

  #print 'pargs: ', pargs
  # read in dict of available datasets
  yd = readYaml()

  dsid = 0
  var = bbox = trange = ''

  # now process the args
  freq = True
  for p in pargs:
    if p[0] == 'l':
      freq = False
      if len(p) == 1: 
        print 'List available datasets:'
        listAllDatasets(yd)
        break
      else:
        dsid = int(p[1])
        print 'Details for dataset <%d>: %s' % (dsid, yd[dsid - 1]['name'])
        listDatasetID(yd[dsid - 1]) 
        break
    if p[0] == 'd':
      if len(p) != 2: errorParams(p[0])
      print 'Dataset chosen <%s>: %s' % ( p[1], yd[int(p[1]) -1]['name'] )
      dsid = int(p[1]) 
    if p[0] == 'v':
      if len(p) != 2: errorParams(p[0])
      print 'Variable chosen: ', p[1]
      var = p[1]
    if p[0] == 'b':
      if len(p) != 2: errorParams(p[0])
      print 'Bounding box: ', p[1]
      bbox = p[1]
    if p[0] == 't':
      if len(p) != 2: errorParams(p[0])
      print 'Time range: ', p[1]
      trange = p[1]
    if p[0] == 's':
      freq = False
      print 'Time-series csv ...'
      if len(p) > 1:
        fname = p[1]
        timeSeries(fname)
      else:
        timeSeries()
      break

  # now formulate request
  if freq: formRequest(yd[int(dsid -1)], var, bbox, trange)
#--- 

def formRequest(ds, var, bbox, trange):
  """Formualate request based on layer type."""
  global tmpncfile
  #print ds

  cmd = []

  #tmpncfile = 'tmp-xxx.nc' 
  tmpncfile = 'tmp-' + datetime.now().strftime('%Y%m%dT%H%I%S') + '.nc'

  #split bbox into lat/lon components
  lat = float(bbox.split(',')[0])
  lon = float(bbox.split(',')[1])
  delta = 0.10
  # and time range into start and end
  if trange != '':
    tstart = trange.split(',')[0]
    tend = trange.split(',')[1]
  else:
    tstart = ds['temporal_extent']['start']
    tend = ds['temporal_extent']['end']

  wcsTsubset = '&subset=time(\"%s\",\"%s\")' % (tstart, tend)
  ncssTsubset = '&time_start=%s' % tstart + '&time_end=%s' % tend + '&timeStride=1&accept=netcdf'

  if ds['type'].lower() == 'netcdf':
    #print 'use ncks or gdallocationinfo'
    cmd = ['ncks', '-v' + var, '-d' + bbox, ds['location']] 
  elif ds['type'].lower() == 'geotiff':
    #print 'use gdallocationinfo (not sure about time series)'
    cmd = ['gdallocationinfo', '-geoloc', bbox, ds['location']] 
  elif ds['type'].lower() == 'wcs':
    #print 'use curl'
    #url = ds['location'] + '&time=%s' % trange + '&bbox=%s' % bbox
    #url = ds['location'] + '&format=application/x-netcdf' + '&subset=Lat(-34.5,-34.4)' + '&subset=Long(140.5,140.6)' + '&subset=time(\"2015-01-01T00:00:00.000Z\",\"2015-12-31T00:00:00.000Z\")'
    url = ds['location'] + '&format=application/x-netcdf' + \
          '&subset=Lat(%s,%s)' % (lat, lat + delta) + \
          '&subset=Long(%s,%s)' % (lon, lon + delta) + wcsTsubset
          #'&subset=time(\"%s\",\"%s\")' % (tstart, tend)
    print url
    cmd = ['curl', '-s', url, '-o', tmpncfile] 
  elif ds['type'].lower() == 'ncss':
    #print 'use curl'
    #url = ds['location'] + '&time=%s' % trange + '&bbox=%s' % bbox
    #url = ds['location'] + '&north=-35.005' + '&west=140.005' + '&east=140.015' + '&south=-35.015' + '&disableProjSubset=on&horizStride=1' + '&time_start=2012-08-31T00%3A00%3A00Z' + '&time_end=2016-02-29T00%3A00%3A00Z' + '&timeStride=1&accept=netcdf'
    url = ds['location'] + '&disableProjSubset=on&horizStride=1' + \
          '&north=%s' % (lat + delta) + \
          '&west=%s' % (lon - delta) + \
          '&east=%s' % (lon + delta) + \
          '&south=%s' % (lat - delta) + ncssTsubset
          #'&time_start=%s' % tstart + '&time_end=%s' % tend + '&timeStride=1&accept=netcdf'
    #cmd = ['curl', '"%s"' % url, '-o %s' % tmpncfile] 
    cmd = ['curl', '-s', url, '-o', tmpncfile] 
  else:
    print ds['type'], ': don\'t know what to do with this type'
    sys.exit(1)

  # now run the command
  print ''
  print 'Running subset request ...'
  if spc(cmd):
    print 'Error in command: %s' % cmd
    sys.exit(1)

  # and generate the time series
  #cmd = ['python', 'ts-out.py', tmpncfile, var]
  print 'Generate csv ...'
  print ''
  timeSeries(var=var)
  #if spc(cmd):
  #  print 'Error in command: %s' % cmd
  #  sys.exit(1)
 
   
#--- 

def timeSeries(infile='tmp-xxx.nc', var='default'):
  """Produce a time series csv output from an NC file.
     Defaults to tmp-xxx input file and first variable found.
  """
  #####
  from netCDF4 import Dataset
  from netcdftime import utime
  from datetime import datetime
  #####

  filin = infile
  #print filin
  if not os.path.exists(filin):
    print ''
    print 'Cannot find file: %s !!!' % filin
    print ''
    sys.exit(1)

  ncf = Dataset(filin, 'r')
  cdftime = utime(ncf['time'].units)

  if var == 'default':
    #pick first variable in dataset
    var = ncf.variables.keys()[0]

  print 'Datetime,Value'
  for i in range(len(ncf['time'])):
    #print '%s,%s' % (cdftime.num2date(ncf['time'][i]).strftime('%Y-%m-%d'), ncf['total_cover'][i,0,0])
    print '%s,%s' % (cdftime.num2date(ncf['time'][i]).strftime('%Y-%m-%d'), ncf[var][i,0,0])

  ncf.close()

#--- 

def usage():
  print ''
  print main.__doc__
  sys.exit(1)
#--- 

### MAIN ###
def main(*args):
  """
  USAGE: ts-request.py [ -l[dataset] -d<dataset> -v<variable> -b<bbox> -t<time_range> -f<output_format> -s[file-name] ]

  WHERE:
         -l[dataset] = list all available datasets (or specified dataset)
         -d<dataset> = dataset number
         -v<variable> = variable identifier
         -b<bbox> = bounding box (lower-left, upper-right)
         -t(time_range) = (start-time, end-time)
         -f<output_format> = nc, tif, asc ...
         -s[file-name] = produce time-series from NC file
  """

  print ''
  print '----------------------------'
  print ' AusCover API - Dev Ver 0.1'
  print '----------------------------'
  print ''

  if len(args[0]) == 1:
      print ''
      print 'Program name: ', args[0][0]
      usage()
      #print main.__doc__
  else:
      parseArgs(args[0][1:])

  print ''
  print '--- DONE ---'
  print ''

  # clean up
  if os.path.exists(tmpncfile): os.remove(tmpncfile)

#---

# flush print buffer immediately
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

if __name__ == "__main__":
  #main(sys.argv[1:])
  main(sys.argv)

### END ###
