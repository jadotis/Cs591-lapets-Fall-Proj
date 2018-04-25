from urllib.request import urlopen
import json
import dml
import prov.model
import datetime
import uuid
import time
import ssl
import random

def union(R, S):
    return R + S

def difference(R, S):
    return [t for t in R if t not in S]

def intersect(R, S):
    return [t for t in R if t in S]

def project(R, p):
    return [p(t) for t in R]

def select(R, s):
    return [t for t in R if s(t)]
 
def product(R, S):
    return [(t,u) for t in R for u in S]

def aggregate(R, f):
    keys = {r[0] for r in R}
    return [(key, f([v for (k,v) in R if k == key])) for key in keys]


def calculateDist(d1, d2):
    R = 6373.0
    d1 = d1.replace("(", "").replace(")", "")
    d1 = d1.split(",")
    d1 = (float(d1[0]), float(d1[1]))

    d2 = d2.replace("(", "").replace(")", "")
    d2 = d2.split(",")
    d2 = (float(d2[0]), float(d2[1]))

    lat1 = radians(d1[0])
    lon1 = radians(d1[1])
    lat2 = radians(d2[0])
    lon2 = radians(d2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance <= 1


def dist(p, q):
    (x1,y1) = p
    (x2,y2) = q
    return (x1-x2)**2 + (y1-y2)**2

def plus(args):
    p = [0,0]
    for (x,y) in args:
        p[0] += x
        p[1] += y
    return tuple(p)

def scale(p, c):
    (x,y) = p
    return (x/c, y/c)

def compTuples(t1, t2):
    if(t1 == []):
        return 100000000000000
    comp = [abs(x[0] - y[0]) + abs(x[1] - y[1]) for x in t1 for y in t2]
    return sum(comp)



class setObesityMarkets(dml.Algorithm):
    print('setObesityMarkets')
    contributor = 'biel_otis'
    reads = ['biel_otis.ObesityData']
    writes = ['biel_otis.OptimalMarketLoc_OLD']

    @staticmethod
    def execute(trial = False):
        startTime = datetime.datetime.now()
        if (trial == True):
            #IF IN TRIAL MODE, SKIP THIS SCRIPT -- SEE EXTENDED SCRIPT (setOptimalHealthMarkets.py) FOR ADDED CONSTRAINT
            #SATISFACTION AND OPTIMIZATION

            return {"start":startTime, "end":startTime}

        # Set up the database connection.
        client = dml.pymongo.MongoClient()
        repo = client['biel_otis']
        repo.authenticate('biel_otis', 'biel_otis')

        obesityValues = list(repo['biel_otis.ObesityData'].find())

        #selection of the geolocation of overweight individuals in Boston
        obeseLocations = [x['geolocation'] for x in obesityValues if x['measureid'] == 'OBESITY' and x['cityname'] == 'Boston']
        latAndLong = [(float(x['latitude']),float(x['longitude'])) for x in obeseLocations]
        lats = [x[0] for x in latAndLong]
        longs = [x[1] for x in latAndLong]
        means = [(random.uniform(min(lats), max(lats)), random.uniform(min(longs), max(longs))) for x in range(10)]
        old = []
        old_compVal = 0
        new_compVal = 1
        while (old_compVal != new_compVal):
            old_compVal = compTuples(old, means)
            old = means
            mpd = [(m, p, dist(m, p)) for (m,p) in product(means, latAndLong)]
            pds = [(p, dist(m,p)) for (m, p, d) in mpd]
            pd = aggregate(pds, min)
            mp = [(m, p) for ((m,p,d), (p2,d2)) in product(mpd, pd) if p==p2 and d==d2]
            mt = aggregate(mp, plus)
            m1 = [(m, 1) for ((m,p,d), (p2, d2)) in product(mpd, pd) if p==p2 and d==d2]
            mc = aggregate(m1, sum)

            means = [scale(t, c) for ((m,t), (m2,c)) in product(mt, mc) if m == m2]
            new_compVal = compTuples(old, means)
        
        inputs = [{'optimal_market': str(x)} for x in means]

        repo.dropCollection("OptimalMarketLoc_OLD")
        repo.createCollection("OptimalMarketLoc_OLD")
        repo['biel_otis.OptimalMarketLoc_OLD'].insert_many(inputs)
        repo['biel_otis.OptimalMarketLoc_OLD'].metadata({'complete':True})
        print(repo['biel_otis.OptimalMarketLoc_OLD'].metadata())
        repo.logout()

        endTime = datetime.datetime.now()

        return {"start":startTime, "end":endTime}
    
    @staticmethod
    def provenance(doc = prov.model.ProvDocument(), startTime = None, endTime = None):
        '''
            Create the provenance document describing everything happening
            in this script. Each run of the script will generate a new
            document describing that invocation event.
            '''
        
        # Set up the database connection.
        client = dml.pymongo.MongoClient()
        repo = client['biel_otis']
        repo.authenticate('biel_otis', 'biel_otis')
        doc.add_namespace('alg', 'http://datamechanics.io/algorithm/') # The scripts are in <folder>#<filename> format.
        doc.add_namespace('dat', 'http://datamechanics.io/data/') # The data sets are in <user>#<collection> format.
        doc.add_namespace('ont', 'http://datamechanics.io/ontology#') # 'Extension', 'DataResource', 'DataSet', 'Retrieval', 'Query', or 'Computation'.
        doc.add_namespace('log', 'http://datamechanics.io/log/') # The event log.

        this_script = doc.agent('alg:biel_otis#setObesityMarkets', {prov.model.PROV_TYPE:prov.model.PROV['SoftwareAgent'], 'ont:Extension':'py'})
        obesity_resource = doc.entity('dat:biel_otis#ObesityData', {prov.model.PROV_LABEL:'Obesity Data from City of Boston', prov.model.PROV_TYPE:'ont:DataSet'})
        output_resource = doc.entity('dat:biel_otis#OptimalHealthMarkets', {prov.model.PROV_LABEL: 'Dataset containing the optimal placements of health food markets based on locations of obese persons.', prov.model.PROV_TYPE:'ont:DataSet'})

        this_run = doc.activity('log:uuid' + str(uuid.uuid4()), startTime, endTime)
    
        
        #Associations
        doc.wasAssociatedWith(this_run, this_script)
     
        #Usages
        doc.usage(this_run, obesity_resource, startTime, None,
                  {prov.model.PROV_TYPE:'ont:Retrieval'})

        #Generated
        doc.wasGeneratedBy(output_resource, this_run, endTime)


        #Attributions
        doc.wasAttributedTo(output_resource, this_script)

        #Derivations
        doc.wasDerivedFrom(output_resource, obesity_resource, this_run, this_run, this_run)
        repo.logout()
        
        return doc

## eof
