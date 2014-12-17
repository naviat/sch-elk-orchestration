#!/usr/bin/python

import time
import boto.opsworks
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-r', '--region', default='us-east-1',
                    type=str, help='AWS region')
parser.add_argument('-e', '--redis_opsworks_layer_id',
                    default='5175c391-cb2a-49bb-be19-4d588d35d430',
                    type=str, help='Opsworks ID of the Redis Layer')
parser.add_argument('-i', '--indexer_opsworks_layer_id',
                    default='9cafbed2-a248-40a4-8b9d-0a68a8629771',
                    type=str, help='Opsworks ID of the Indexer Layer')
parser.add_argument('-cd', '--cooldown_period', default=3,
                    type=int, help='Cooldown period in minutes between ' +
                    'scale down of redis and indexers')
args = parser.parse_args()
region = args.region
redis_opsworks_layer_id = args.redis_opsworks_layer_id
indexer_opsworks_layer_id = args.indexer_opsworks_layer_id
cooldown_period_minutes = args.cooldown_period

print 'Start time: ' + time.ctime()

# Get Status of the Opswork instance in Redis layer
opswork = boto.opsworks.connect_to_region(region)
instances_to_stop = []
print 'Checking status of Opsworks instance in Redis Layer'
instances = opswork.describe_instances(layer_id=redis_opsworks_layer_id)
for key, value in instances.items():
    for i in range(0, len(value)):
        redis_status = value[i].get('Status')
        redis_opswork_id = value[i].get('InstanceId')

        if redis_status != 'online':
            raise Exception('Redis instance with opsworks id ' +
                            redis_opswork_id +
                            ' expected status is online. It is currently ' +
                            redis_status +
                            ' . Another process could already be working.')

    instances_to_stop.append(redis_opswork_id)

# Stop Redis instance
for instance in instances_to_stop:
    print 'Stopping Redis instance with opsworks id ' + instance
    opswork.stop_instance(instance)
    instances_to_stop.remove(instance)

# Wait for cooldown period for drain their buffer
for i in range(0, cooldown_period_minutes):
    print time.ctime() + ':Waiting for cooldown period before scaling down indexers. ' + \
        str(cooldown_period_minutes-i) + ' minutes left '
    time.sleep(60)

# Get Status of the Opswork instances in Indexer layer
print 'Checking status of Opsworks instances in Indexer Layer'
instances = opswork.describe_instances(layer_id=indexer_opsworks_layer_id)
for key, value in instances.items():
    for i in range(0, len(value)):
        indexer_status = value[i].get('Status')
        indexer_opswork_id = value[i].get('InstanceId')

        if indexer_status != 'online':
            raise Exception('Indexer instance with opsworks id ' +
                            indexer_opswork_id +
                            ' expected status is online. It is currently ' +
                            indexer_status +
                            '. Another process could already be working.')

        instances_to_stop.append(indexer_opswork_id)

# Stop Indexer instances
for instance in instances_to_stop:
    print 'Stopping Indexer instance with opsworks id ' + instance
    opswork.stop_instance(instance)
