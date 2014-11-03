from django.db import models

class Node(models.Model):
    id = models.IntegerField(primary_key = True)
    graphid = models.IntegerField(unique = True, null = True, blank=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    elevation =  models.FloatField(default=0.0)
    
class Way(models.Model):
    id = models.IntegerField(primary_key = True)
    name = models.CharField(max_length = 64)

class NodeWayRelation(models.Model):
    node = models.ForeignKey('Node')
    way = models.ForeignKey('Way')
    position = models.IntegerField()
    class Meta:
        ordering = ('position',)
#         unique_together = ('Node','way','position')