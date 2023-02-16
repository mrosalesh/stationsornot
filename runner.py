#!/usr/bin/env python
# Eclipse SUMO, Simulation of Urban MObility; see https://eclipse.org/sumo
# Copyright (C) 2009-2022 German Aerospace Center (DLR) and others.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# https://www.eclipse.org/legal/epl-2.0/
# This Source Code may also be made available under the following Secondary
# Licenses when the conditions for such availability set forth in the Eclipse
# Public License 2.0 are satisfied: GNU General Public License, version 2
# or later which is available at
# https://www.gnu.org/licenses/old-licenses/gpl-2.0-standalone.html
# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

# @file    runner.py
# @author  Manuel Hernandez Rosales
# @author  Carmen Angelina García Cerrud
# @date    2022-10-04

from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import optparse
import re
import numpy as np


# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary 
import traci
import math
import random

#longitud entre estaciones por manzana
lengthbetweenstations=50
#longitud de las estaciones
lengthstations=15
#numero de habitantes que se van a transportar
habitantestrans = 1000
#parametro de la distribucion de Poisson
lamb = 1
#capacidad de las estaciones de buses
personcapacitystation=100
#duracion de las paradas
duration=20


def factorial(n):
    fac=1
    for y in range(1,n+1):
        fac=fac*y
    return fac

def distpoisson(lamb, st):
    if st>12:
        dp=0
    else:
        dp=((lamb**st)*math.exp(-lamb))/(factorial(st))
    return dp



def createstations(lengthbetweenstations, lengthstation):
    i=0
    h = open ('./data/busstops.add.xml','w')
    h.write("""<?xml version="1.0" encoding="UTF-8"?>\n<additional xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/additional_file.xsd">\n""")
    f = open ('./data/paradas.rou.xml','r')
    for line in f:
        if ('id=\"r_bus' in line)==True:
            for item in re.finditer("(?P<begin>route id=\"r_bus)(?P<norbus>[\d]*)(\" edges=\")(?P<edges>[\w -.]*)(?P<end>\")", line):
                edges=re.split(" ", item.groupdict()['edges'])
                norbus=item.groupdict()['norbus']
                bsf = open ('./data/busstops'+norbus+'.txt','w')
                for edge in edges:
                    g = open ('./data/paradas.net.xml','r') 
                    for line2 in g:
                        aux='lane id="'+edge+'_1'
                        if (aux in line2)==True:
                            for item2 in re.finditer("(?P<begin>lane id=[\w \f-.\_\":=]*length=\")(?P<length>[\d]*.[\d]*)", line2):
                                length=float(item2.groupdict()['length'])
                                a=math.trunc(length/lengthbetweenstations)
                                b=(length/lengthbetweenstations - a)
                                if (b<.66):
                                    a=a-1
                                j=0
                                startpos=0
                                endpos=lengthstation
                                while (j<=a):
                                    h.write("<busStop id=\""+ 'bs'+str(i)+"\" lane=\""+ edge + '_1' +"\" startPos=\""+str(startpos)+"\" endPos=\""+str(endpos)+"\" lines=\""+norbus+'b'+"\" friendlyPos=\"true\" personCapacity=\""+ str(personcapacitystation) +"\" />\n")
                                    bsf.write('bs'+str(i)+'\n')
                                    startpos=startpos+lengthbetweenstations
                                    endpos=endpos+lengthbetweenstations
                                    i=i+1
                                    j=j+1
                    g.close()
                bsf.close
    f.close
    h.write("""</additional>""")
    h.close();

def createroutesbusstops():
    f = open ('./data/paradas.rou.xml','r')
    h = open ('./data/paradasbusstops.rou.xml','w')
    for line in f:
        if ('id=\"r_bus' in line)==True:
            line=line.rstrip('\n>/')+'>\n'
            h.write(line)
            for item in re.finditer("(?P<begin>route id=\"r_bus)(?P<norbus>[\d]*)(\" edges=\")(?P<edges>[\w -.]*)(?P<end>\")", line):
                norbus=item.groupdict()['norbus']
                z=open("./data/busstops"+norbus+".txt", 'r')
                for x in z:
                    h.write('<stop busStop="' + x.rstrip('\n') + '" duration="' + str(duration) +'"/> ');
                h.write('\n</route>\n')
                z.close
        else:
            h.write(line)
    h.close
    f.close

    
def run():
    step = 0
    #elegimos una semilla aleatoria
    random.seed()

    #iniciamos el archivo de resultados
    res = open ('./resultados.csv','w')
    res.write('tiempo, bus, velfin, pasajeros'+'\n')
    
    #metemos a una lista lanes que tienen permitidos peatones
    arreglolanes=traci.lane.getIDList()
    
    arreglolanespeat=[]
    for x in arreglolanes:
        if ("pedestrian" in traci.lane.getAllowed(x))==True:
            arreglolanespeat.append(x)
    #print(arreglolanespeat)        
    #metemos a una lista todas las paradas de autobus
    busstops = traci.busstop.getIDList()

    #las lineas, sus edges y su terminal
    dictstatterm={}
    dictstatedg={}
    pa = open ('./data/paradas.rou.xml','r')
    for line in pa:
        if ('id=\"r_bus' in line)==True:
            for item in re.finditer("(?P<begin>route id=\"r_bus)(?P<norbus>[\d]*)(\" edges=\")(?P<edges>[\w -.]*)(?P<end>\")", line):
                edges=re.split(" ", item.groupdict()['edges'])
                norbus=item.groupdict()['norbus']
                terminal=edges[-1]
                dictstatterm[norbus]=terminal
                dictstatedg[norbus]=edges
    paso=1
    while traci.simulation.getMinExpectedNumber() > 0:
        #pasajeros que salen de su ubicacion a tomar un autobus
        st=step%300
        if st==0:
            pasajeros=int(habitantestrans*distpoisson(1, paso))
            #print(pasajeros)
            #para cada pasajero elegimos una ubicacion aleatoria y una parada aleatoria
            i=0
            while (i<pasajeros):
                lanesel=random.choice(arreglolanespeat)
                longlane=traci.lane.getLength(lanesel)
                edgesel=traci.lane.getEdgeID(lanesel)
                possel=longlane*random.random()
                #seleccionames una parada a donde ir y su posicion
                busstopsel=random.choice(busstops)
                posicionbusstop=traci.busstop.getEndPos(busstopsel)
                lanebusstopsel=traci.busstop.getLaneID(busstopsel)
                edgebusstopsel=traci.lane.getEdgeID(lanebusstopsel)
                #se crea el peaton y se hace caminar al peaton a la parada
                edgeswalk=[]
                edgeswalk.append(edgesel)
                edgeswalk.append(edgebusstopsel)
                traci.person.add('person' + str(paso)+'n'+str(i), edgesel, possel, step+150, typeID='DEFAULT_PEDTYPE')
                traci.person.appendWalkingStage('person' + str(paso)+'n'+str(i), edgeswalk, posicionbusstop, -1, 1, busstopsel)
                for x in dictstatedg.keys():
                    if edgebusstopsel in dictstatedg[x]:
                        traci.person.appendDrivingStage('person' + str(paso)+'n'+str(i), dictstatterm[x], x+'b', stopID='')
                        print(dictstatterm[x])
                        print(x+'b')
                                    
                #print('person' + str(paso)+'n'+str(i))
                #print(traci.busstop.getPersonCount(busstopsel))
                
                i+=1
            paso+=1
        traci.simulationStep()    
        step += 1
        vehiculos=traci.vehicle.getIDList()
        for v in vehiculos:
            type=traci.vehicle.getTypeID(v)
            pasajeros=traci.vehicle.getPersonNumber(v)
            velfin=traci.vehicle.getSpeed(v)
            if type=='t_0':
                res.write(str(step) +',' + v +','+ str(velfin) + ','+ str(pasajeros) +'\n')
    res.close()
    traci.close()
    sys.stdout.flush()



def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options


# this is the main entry point of this script
if __name__ == "__main__":
    options = get_options()

    createstations(lengthbetweenstations, lengthstations);
    createroutesbusstops()
    
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    traci.start([sumoBinary, "-c", "data/paradas.sumocfg",
                             "--tripinfo-output", "tripinfo.xml", "--ignore-route-errors"])
    run()
