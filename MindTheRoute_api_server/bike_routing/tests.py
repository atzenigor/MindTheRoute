from django.test import TestCase
import bike_routing.graphmaker as gm
import bike_routing.models as model
from django.db import connection

class Graphmaker(TestCase):
    
    def test_makegraph(self):
        gm.Graphmap('data/Pigneto-highways.osm',
                    'data/pigneto_elevations.tsv').make_graph()


        