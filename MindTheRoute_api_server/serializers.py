from rest_framework import serializers
from bike_routing.models import Node, Way

class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        exclude = ['graphid']
        
class WaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Way