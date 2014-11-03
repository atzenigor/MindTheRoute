from django.db import models
from django.db.models import fields

class Node(models.Model):
    id = fields.BigIntegerField(primary_key = True )
    graphid = models.IntegerField(unique = True, null = True, blank=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    elevation =  models.FloatField(default=0.0)
#     class Meta:
#         unique_together = ('latitude','longitude') 
   
class Way(models.Model):
    id = models.BigIntegerField(primary_key = True)
    name = models.CharField(max_length = 64)

class NodeWayRelation(models.Model):
    node = models.ForeignKey('Node')
    way = models.ForeignKey('Way')
    position = models.IntegerField()
    class Meta:
        ordering = ('position',)
#         unique_together = ('Node','way','position')