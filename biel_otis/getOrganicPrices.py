from urllib.request import urlopen
import json
import dml
import prov.model
import datetime
import uuid
import time
import ssl


class getOrganicPrices(dml.Algorithm):
    contributor = 'biel_otis'
    reads = []
    writes = ['biel_otis.OrganicPrices']
    ssl._create_default_https_context = ssl._create_unverified_context

    @staticmethod
    def execute(trial = False):
        '''Retrieve some data sets (not using the API here for the sake of simplicity).'''
        startTime = datetime.datetime.now()

        # Set up the database connection.
        client = dml.pymongo.MongoClient()
        repo = client['biel_otis']
        repo.authenticate('biel_otis', 'biel_otis')
        url = 'http://datamechanics.io/data/biel_otis/food_prices.json'
        response = urlopen(url).read().decode("utf-8")
        r = json.loads(response)
        
        repo.dropCollection("OrganicPrices")
        repo.createCollection("OrganicPrices")
        repo['biel_otis.OrganicPrices'].insert_many(r)
        repo['biel_otis.OrganicPrices'].metadata({'complete':True})
        print(repo['biel_otis.OrganicPrices'].metadata())
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
        doc.add_namespace('op', 'http://datamechanics.io/biel_otis/') # Organic Food Prices dataset in the United States

        this_script = doc.agent('alg:biel_otis#getOrganicPrices', {prov.model.PROV_TYPE:prov.model.PROV['SoftwareAgent'], 'ont:Extension':'py'})
        resource = doc.entity('op:food_prices', {'prov:label':'Organic Food Prices dataset in the United States', prov.model.PROV_TYPE:'ont:DataResource', 'ont:Extension':'json'})
        output_resource = doc.entity('dat:biel_otis#OrganicPrices', {prov.model.PROV_LABEL: 'Organic Food Prices dataset in the United States', prov.model.PROV_TYPE:'ont:DataSet'})


        this_run = doc.activity('log:uuid' + str(uuid.uuid4()), startTime, endTime)
    
        
        #Associations
        doc.wasAssociatedWith(this_run, this_script)
     
        #Usages
        doc.usage(this_run, resource, startTime, None,
                  {prov.model.PROV_TYPE:'ont:Retrieval'})

        #Generated
        doc.wasGeneratedBy(output_resource, this_run, endTime)


        #Attributions
        doc.wasAttributedTo(output_resource, this_script)

        #Derivations
        doc.wasDerivedFrom(output_resource, resource, this_run, this_run, this_run)
        repo.logout()
        
        return doc

print("finished getOrganicPrices")
## eof
